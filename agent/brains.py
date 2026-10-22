"""The producer brain: builds the brief and asks a model for complete, render-ready episodes.

Two brains share one contract (agent/schema.py):
  * gemini — called directly from GitHub Actions with the free-tier API key
  * claude — a Claude scheduled task writes queue/pitches/<date>.json itself (see CLAUDE_TASK.md);
             this module only builds the same brief so both brains see identical context.
"""
from __future__ import annotations

import html
import json
import random
import re
import time
from collections import Counter
from datetime import timedelta

import requests
import yaml

from .common import LEARNINGS, ROOT, env, load_config, log, now, parse, same_concept, setting
from .schema import CONTRACT, MONSTERS, NAMES

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODELS_URL = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_FALLBACKS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]


def _gemini_flash_models(key: str) -> list[str]:
    """Flash models this key can call right now, newest first (Google retires old names for new keys)."""
    try:
        r = requests.get(GEMINI_MODELS_URL, headers={"x-goog-api-key": key}, params={"pageSize": 200}, timeout=30)
        models = r.json().get("models", []) if r.ok else []
    except (requests.RequestException, ValueError):
        return []
    names = [m["name"].split("/", 1)[-1] for m in models
             if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m.get("name", "")
             and not any(x in m["name"] for x in ("preview", "exp", "image", "tts", "live", "audio"))]
    num = lambda n: [float(x) for x in re.findall(r"\d+(?:\.\d+)?", n)[:1]] or [0.0]
    return sorted(names, key=lambda n: (num(n), "lite" not in n), reverse=True)


# ------------------------------------------------------------------ brief

def recent_episodes(state: dict, days: int = 30) -> list[dict]:
    cfg = load_config()
    cutoff = now(cfg) - timedelta(days=days)
    out = []
    for e in state["episodes"].values():
        created = parse(e.get("created"))
        if created and created >= cutoff and e.get("status") not in ("rejected", "superseded"):
            out.append(e)
    return sorted(out, key=lambda e: e["created"])


TAUGHT_STATUSES = ("approved", "rendered", "published", "failed")
LEVELS = ("beginner", "intermediate", "advanced")


def taught_concepts(state: dict, exclude: str | None = None) -> list[dict]:
    """Every concept the series has already taught, all time: reels that are approved or further along, plus
    concepts remembered from reels that were deleted after going live. These are never taught again."""
    out = [dict(t) for t in state.get("taught", [])]
    for k, r in state["episodes"].items():
        ep = r.get("episode") or {}
        if k != exclude and r.get("status") in TAUGHT_STATUSES and ep.get("concept"):
            out.append({"concept": ep["concept"], "title": ep.get("title", ""), "topic": ep.get("topic", "")})
    return out


def already_taught(state: dict, concept: str, exclude: str | None = None) -> str | None:
    """The taught concept this one repeats, or None if it's new."""
    for t in taught_concepts(state, exclude):
        if same_concept(concept, t["concept"]) or (t.get("topic") and same_concept(concept, t["topic"])):
            return t["concept"]
    return None


def target_level(state: dict) -> str:
    lvl = setting(state, load_config(), "level")
    return lvl if lvl in LEVELS else "intermediate"


STAGES = {
    "languages": "production bugs in plain Python, JavaScript, TypeScript, Java, Go and PHP",
    "frameworks": "production bugs in the frameworks teams ship: Node/Express, NestJS, Next.js, React, Django, FastAPI, "
                  "Flask, Spring Boot, Laravel, ORMs, Celery, GraphQL",
    "tools": "production incidents with industry tools: Kafka, Redis, PostgreSQL, MySQL, MongoDB, Elasticsearch, "
             "RabbitMQ, Docker, Kubernetes, AWS, GCP, Terraform, Nginx, CI/CD, observability",
}


def load_topics() -> dict[str, list[dict]]:
    data = yaml.safe_load((ROOT / "bible" / "topics.yaml").read_text()) or {}
    return {st: [t for t in data.get(st) or [] if t.get("monster") in MONSTERS] for st in STAGES}


def fresh_topics(state: dict, topics: dict | None = None) -> dict[str, list[dict]]:
    """Backlog topics per stage that haven't been taught (or pitched today) yet."""
    topics = topics or load_topics()
    taught = taught_concepts(state)
    open_concepts = [e["episode"].get("concept", "") for e in recent_episodes(state, days=1)
                     if e.get("status") in ("pitched", "rewrite_queued")]

    def used(t):
        return any(same_concept(t["topic"], x.get("topic") or "") or same_concept(t["fix"], x["concept"]) or
                   same_concept(t["topic"], x["concept"]) for x in taught) or any(same_concept(t["fix"], c) for c in open_concepts)

    return {st: [t for t in ts if not used(t)] for st, ts in topics.items()}


def active_stage(state: dict, fresh: dict | None = None) -> str:
    """The pinned stage (/stage frameworks), or with auto the first stage that still has untaught topics."""
    pinned = setting(state, load_config(), "stage")
    if pinned in STAGES:
        return pinned
    fresh = fresh or fresh_topics(state)
    return next((st for st in STAGES if fresh[st]), list(STAGES)[-1])


def random_clock(rng: random.Random) -> str:
    """The time on the opening pager: any time of day or night, never the same old 3:00 AM."""
    while True:
        t = f"{rng.randint(1, 12)}:{rng.randint(0, 59):02d} {rng.choice(['AM', 'PM'])}"
        if t != "3:00 AM":
            return t


def plan_lineup(state: dict, n: int, seed: str) -> list[dict]:
    """Choose which monster + topic each pitch should cover: one monster each, topics from the active stage first
    (spilling into the next stage when it runs short), never a taught topic, leaning toward monsters the audience
    responds to (from the marketer's scores)."""
    fresh = fresh_topics(state)
    stage = active_stage(state, fresh)
    level = target_level(state)
    recent = recent_episodes(state)
    last_monsters = [e["episode"]["monster"] for e in recent[-6:] if e.get("episode")]
    perf = monster_scores(state)
    rng = random.Random(seed)
    counts = Counter(last_monsters)
    order = sorted(MONSTERS, key=lambda m: (counts[m] - 0.6 * perf.get(m, 0) + rng.random() * 0.5))
    names = list(STAGES)
    lineup = []
    pinned = setting(state, load_config(), "stage") in STAGES
    for st in [stage] if pinned else names[names.index(stage):]:
        for m in order:
            if len(lineup) < n and m not in [x["monster"] for x in lineup]:
                pool = [t for t in fresh[st] if t["monster"] == m]
                if pool:
                    lineup.append({**rng.choice(pool), "stage": st})
    while len(lineup) < n:  # backlog used up: the brain invents a new production bug from the stage's world
        m = order[len(lineup) % len(order)]
        lineup.append({"monster": m, "topic": f"a NEW production {NAMES[m]} bug from: {STAGES[stage]} "
                       "(not in the taught list, or a real-world extension of one)", "fix": "", "tech": "", "stage": stage})
    for x in lineup:
        x.update(level=level, wake_time=random_clock(rng))
    return lineup


def monster_scores(state: dict) -> dict[str, float]:
    """Relative performance per monster, centered at 0 (positive = above average)."""
    by: dict[str, list[float]] = {}
    for e in state["episodes"].values():
        s = (e.get("metrics") or {}).get("score")
        if s is not None and e.get("episode"):
            by.setdefault(e["episode"]["monster"], []).append(s)
    if not by:
        return {}
    avg = {m: sum(v) / len(v) for m, v in by.items()}
    overall = sum(avg.values()) / len(avg) or 1
    return {m: (v - overall) / overall for m, v in avg.items()}


LEVEL_NOTES = {
    "beginner": "the viewer is learning to code; explain the idea from scratch.",
    "intermediate": "the viewer writes code daily and knows basic syntax, loops, functions and objects. Skip the basics; "
                    "teach the bug that bites working developers in real apps (APIs, async, state, data, production), the "
                    "subtle cause behind it and the idiomatic fix.",
    "advanced": "the viewer is an experienced developer. Teach the edge case, the runtime/engine detail or the "
                "production-scale failure behind a familiar bug.",
}


def build_brief(state: dict, n: int, seed: str, extra: str = "", news: dict | None = None) -> tuple[str, str]:
    """Return (system_prompt, user_prompt). With `news` (from research()), the episode covers that news item
    instead of the planned lineup."""
    bible = (ROOT / "bible" / "SERIES_BIBLE.md").read_text()
    cfg = load_config()
    lineup = plan_lineup(state, n, seed)
    if news:
        lineup = [{"monster": "pick the cast member whose bug family fits the root cause", "topic": news["query"],
                   "level": lineup[0]["level"], "wake_time": lineup[0]["wake_time"], "stage": "news"}]
    recent = recent_episodes(state)
    learn = LEARNINGS.read_text() if LEARNINGS.exists() else "No performance data yet. Optimize for a strong 2-second hook and saves."
    ideas = [i["text"] for i in state.get("ideas", []) if not i.get("used")][:5]
    taught = taught_concepts(state)
    level = target_level(state)
    stage = active_stage(state)
    handle = cfg.get("instagram_handle", "")
    system = (
        "You are the head producer and growth marketer of an animated Instagram Reels series. "
        "You write complete, render-ready episodes as strict JSON. Every episode is genuinely funny and built on a real-world bug "
        "developers actually ship. Every code sample must be real, correct and runnable; "
        "every error message must be the real one the language or tool produces. You optimize for: a scroll-stopping first 2 seconds, "
        "rewatches, shares to developer friends, and saves.\n\n" + bible
    )
    if news:
        plan = f"""This is a BREAKING NEWS episode about a real, recent programming story. Research brief (the ONLY source
of facts; never add versions, CVE IDs, names or dates that aren't in it):
{news["brief"]}

Lineup: {json.dumps(lineup)}
News episode rules: the hook names the news ("Someone just found two bugs in ..."); the code beat shows the real bug
class from the brief's MINIMAL EXAMPLE (keep it real and runnable, it may be a simplified illustration); the fix beat
shows the correct mitigation; the narration or outro says what to update to; the caption credits who found it and
says "update now" with the patched version if the brief has one. Set `topic` to "news: <one-line headline>"."""
    else:
        plan = f"""Planned lineup (follow it unless an idea below is clearly stronger):
{json.dumps(lineup, indent=1)}"""
    user = f"""Write {n} NEW episodes for today.

{plan}

Viewer/owner ideas to use if they fit: {json.dumps(ideas) if ideas else "none"}

ALREADY TAUGHT — never teach any of these again, not even reworded or in another language:
{chr(10).join(f"- {t['concept']}" for t in taught) or "- nothing yet"}
You MAY go deeper on one of them with an extension the viewer hasn't seen: a real-world case, an edge case or the
advanced form (e.g. after "optional chaining ?." → "?. on an API response, with ?? for the fallback" or
"calling a maybe-missing callback with fn?.()"). Then the episode's `concept` names the NEW idea, `builds_on` names the
taught concept it extends, and the reel must not re-explain the basics.

Target level: {level.upper()} — {LEVEL_NOTES[level]}
Series stage: {stage.upper()} — {STAGES[stage]}. No basic coding lessons: every episode is a bug that takes down,
slows down or corrupts a real production system, with the real error/log line it produces. Name the tech in `tech`.

Avoid repeating these recent episodes (title — concept):
{chr(10).join(f"- {e['episode']['title']} — {e['episode'].get('concept','')}" for e in recent[-20:] if e.get('episode')) or "- none yet"}

What the marketer learned from real performance data:
{learn}

Rules for today's batch:
- Each episode uses a DIFFERENT monster from the others in this batch.
- Vary the hook style across the batch: one relatable pain ("POV: you just merged and..."), one threat ("This ghost crashes your app just by existing"), one curiosity gap, one bold claim.
- Captions end with a question that invites comments, then mention {handle or "the account"}.
- Every episode's `concept` is new (see ALREADY TAUGHT) and different from the others in this batch.
- Set `level` to "{level}", `topic` to the lineup topic you used and `wake_time` to its lineup wake_time. The pager
  beat shows that time; if narration or dialogue mentions the time, say that time in words (never "three A M").
- 25-40 seconds each, 6-9 beats, exactly one code beat and one fix beat about the same code.
{extra}

Return ONLY JSON shaped like this (no markdown):
{json.dumps(CONTRACT, indent=1)}"""
    return system, user


def rewrite_brief(state: dict, episode: dict, notes: str) -> tuple[str, str]:
    system, _ = build_brief(state, 1, episode.get("id", "x"))
    user = f"""The owner reviewed this episode and asked for changes.

OWNER NOTES: {notes}

CURRENT EPISODE:
{json.dumps(episode, indent=1)}

Rewrite the episode applying the notes faithfully while keeping every rule of the series bible.
Return ONLY JSON: {{"episodes": [ <the one rewritten episode> ]}}"""
    return system, user


# ------------------------------------------------------------------ gemini

def _extract_json(text: str) -> dict:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=0)
    data = json.loads(text[start:])
    if isinstance(data, list):
        data = {"episodes": data}
    return data


def _generate(body: dict) -> dict:
    """POST to Gemini with retries and model fallback; returns the first successful response body."""
    key = env("GEMINI_API_KEY", required=True)
    cfg = load_config()
    models = [env("GEMINI_MODEL") or cfg.get("gemini_model", GEMINI_FALLBACKS[0]), *GEMINI_FALLBACKS]
    last, discovered = None, False
    tried = set()
    while models:
        model = models.pop(0)
        if model in tried:
            continue
        tried.add(model)
        for attempt in range(4):
            try:
                r = requests.post(GEMINI_URL.format(model=model), headers={"x-goog-api-key": key}, json=body, timeout=180)
            except requests.RequestException as ex:
                last = str(ex)
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code in (429, 500, 503):
                last = f"{model}: HTTP {r.status_code} {r.text[:200]}"
                if attempt >= 1:  # still busy: a less loaded model beats waiting
                    log("gemini busy, switching model:", model)
                    if not discovered:
                        discovered = True
                        models += _gemini_flash_models(key)[:4]
                    break
                log("gemini busy/rate-limited, retrying:", last)
                time.sleep(15)
                continue
            if r.status_code >= 400:
                last = f"{model}: HTTP {r.status_code} {r.text[:300]}"
                if r.status_code == 404 and not discovered:  # model retired: ask Google what this key can use
                    discovered = True
                    found = _gemini_flash_models(key)
                    log("gemini model unavailable, discovered:", found[:5])
                    models += found[:4]
                break  # try next model
            return r.json()
    raise RuntimeError(f"Gemini failed: {last}")


def _text(data: dict) -> str:
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


def gemini(system: str, user: str, temperature: float = 0.9) -> dict:
    last = None
    for _ in range(3):
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": temperature, "responseMimeType": "application/json", "maxOutputTokens": 32000},
        }
        data = _generate(body)
        try:
            return _extract_json(_text(data))
        except (KeyError, IndexError, json.JSONDecodeError) as ex:
            last = f"unparseable response ({ex}) {str(data)[:300]}"
            user = user + "\n\nYour previous answer was not valid JSON. Return ONLY the JSON object."
    raise RuntimeError(f"Gemini failed: {last}")


# ------------------------------------------------------------------ news research

def _page_text(url: str, limit: int = 15000) -> str:
    """Readable text of a linked article (scripts, styles and tags stripped)."""
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 (prod-manor research)"})
        r.raise_for_status()
    except requests.RequestException as ex:
        log("news page fetch failed:", url, repr(ex))
        return ""
    t = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)[^>]*>.*?</\1>", " ", r.text)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", t))
    return " ".join(t.split())[:limit]


RESEARCH_PROMPT = """You are a fact-checking research assistant for a developer education channel.
Research this programming news item using Google Search and the article text below (if any):

NEWS: {query}

{pages}
Write a factual brief (no fluff, max 400 words) with these headings:
WHAT HAPPENED: who found or reported it, when, and where it was published.
AFFECTED: product / language / framework / tool, and the exact versions or setups affected.
IDS: CVE or advisory IDs, if any.
ROOT CAUSE: the technical bug class (e.g. integer overflow in X, missing bounds check in Y) explained precisely.
IMPACT: what an attacker or the bug can do in production.
FIX: patched versions and the correct mitigation for developers.
MINIMAL EXAMPLE: a short, real code pattern (max 6 lines) in the affected language that shows the same bug class,
and the one-line fix. Say if it's an illustration of the class rather than the exact vulnerable code.
UNCERTAIN: anything sources disagree on or you could not confirm.
Only state what sources support. Never invent version numbers, CVE IDs, names or dates."""


def _why_empty(data: dict) -> str:
    """Why a response had no text (finish reason, block reason, thinking tokens), for logs and Telegram."""
    c = (data.get("candidates") or [{}])[0]
    block = (data.get("promptFeedback") or {}).get("blockReason")
    use = data.get("usageMetadata") or {}
    return (f"finish={c.get('finishReason')}" + (f" blocked={block}" if block else "")
            + f" thinking_tokens={use.get('thoughtsTokenCount')} output_tokens={use.get('candidatesTokenCount')}")


def research(query: str) -> dict:
    """Search the web for a news item and return {"brief", "sources", "note"} the episode is written from.
    Tries Google Search grounding first; if that fails or comes back empty, retries once, then falls back to the
    linked article text alone (never to the model's memory, which can't know recent news)."""
    urls = re.findall(r"https?://\S+", query)[:3]
    pages = "".join(f"ARTICLE {u}:\n{txt}\n\n" for u in urls if (txt := _page_text(u)))
    prompt = RESEARCH_PROMPT.format(query=query, pages=pages)
    # thinking tokens count against maxOutputTokens, so leave plenty of room or the answer comes back empty
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 32000}}
    search = {**body, "tools": [{"google_search": {}}]}
    attempts = [("search", search), ("search retry", search)] + ([("article only", body)] if pages else [])
    problems = []
    for name, b in attempts:
        try:
            data = _generate(b)
            brief = _text(data).strip()
        except (RuntimeError, KeyError, IndexError) as ex:
            problems.append(f"{name}: {str(ex)[:200]}")
            log("news research failed:", name, repr(ex)[:300])
            continue
        if not brief:
            problems.append(f"{name}: empty ({_why_empty(data)})")
            log("news research empty:", name, _why_empty(data), str(data)[:500])
            continue
        sources = [{"title": u, "url": u} for u in urls]
        for ch in (data["candidates"][0].get("groundingMetadata") or {}).get("groundingChunks") or []:
            web = ch.get("web") or {}
            if web.get("uri") and all(x["url"] != web["uri"] for x in sources):
                sources.append({"title": web.get("title") or web["uri"], "url": web["uri"]})
        note = "" if name.startswith("search") else "Web search failed, so this brief comes from the linked article only."
        return {"brief": brief, "sources": sources[:6], "note": note}
    hint = "" if urls else " Try again with a link to the article."
    raise RuntimeError("; ".join(problems) + hint)
