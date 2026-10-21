"""The producer brain: builds the brief and asks a model for complete, render-ready episodes.

Two brains share one contract (agent/schema.py):
  * gemini — called directly from GitHub Actions with the free-tier API key
  * claude — a Claude scheduled task writes queue/pitches/<date>.json itself (see CLAUDE_TASK.md);
             this module only builds the same brief so both brains see identical context.
"""
from __future__ import annotations

import json
import random
import re
import time
from collections import Counter
from datetime import timedelta

import requests
import yaml

from .common import LEARNINGS, ROOT, env, load_config, log, now, parse
from .schema import CONTRACT, MONSTERS, NAMES

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


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


def plan_lineup(state: dict, n: int, seed: str) -> list[dict]:
    """Choose which monster + topic each pitch should cover: rotate monsters, prefer unused topics,
    and lean toward monsters the audience responds to (from the marketer's scores)."""
    topics = yaml.safe_load((ROOT / "bible" / "topics.yaml").read_text())
    recent = recent_episodes(state)
    used = {(e["episode"]["monster"], e["episode"].get("concept", "").lower()) for e in recent if e.get("episode")}
    last_monsters = [e["episode"]["monster"] for e in recent[-6:] if e.get("episode")]
    perf = monster_scores(state)
    rng = random.Random(seed)
    counts = Counter(last_monsters)
    order = sorted(MONSTERS, key=lambda m: (counts[m] - 0.6 * perf.get(m, 0) + rng.random() * 0.5))
    lineup = []
    for i in range(n):
        m = order[i % len(order)]
        pool = topics.get(m, [])
        fresh = [t for t in pool if (m, t["topic"].lower()) not in used and t["topic"] not in [x["topic"] for x in lineup]]
        pick = rng.choice(fresh or pool) if pool else {"topic": f"a classic {NAMES[m]} bug", "fix": "", "level": "beginner", "lang": "javascript"}
        lineup.append({"monster": m, **pick})
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


def build_brief(state: dict, n: int, seed: str, extra: str = "") -> tuple[str, str]:
    """Return (system_prompt, user_prompt)."""
    bible = (ROOT / "bible" / "SERIES_BIBLE.md").read_text()
    cfg = load_config()
    lineup = plan_lineup(state, n, seed)
    recent = recent_episodes(state)
    learn = LEARNINGS.read_text() if LEARNINGS.exists() else "No performance data yet. Optimize for a strong 2-second hook and saves."
    ideas = [i["text"] for i in state.get("ideas", []) if not i.get("used")][:5]
    handle = cfg.get("instagram_handle", "")
    system = (
        "You are the head producer and growth marketer of an animated Instagram Reels series. "
        "You write complete, render-ready episodes as strict JSON. Every episode is genuinely funny and built on a real-world bug "
        "developers actually ship. Every code sample must be real, correct and runnable; "
        "every error message must be the real one the language produces. You optimize for: a scroll-stopping first 2 seconds, "
        "rewatches, shares to developer friends, and saves.\n\n" + bible
    )
    user = f"""Write {n} NEW episodes for today.

Planned lineup (follow it unless an idea below is clearly stronger):
{json.dumps(lineup, indent=1)}

Viewer/owner ideas to use if they fit: {json.dumps(ideas) if ideas else "none"}

Avoid repeating these recent episodes (title — concept):
{chr(10).join(f"- {e['episode']['title']} — {e['episode'].get('concept','')}" for e in recent[-20:] if e.get('episode')) or "- none yet"}

What the marketer learned from real performance data:
{learn}

Rules for today's batch:
- Each episode uses a DIFFERENT monster from the others in this batch.
- Vary the hook style across the batch: one relatable pain ("POV: it's 3 AM and..."), one threat ("This ghost crashes your app just by existing"), one curiosity gap, one bold claim.
- Captions end with a question that invites comments, then mention {handle or "the account"}.
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


def gemini(system: str, user: str, temperature: float = 0.9) -> dict:
    key = env("GEMINI_API_KEY", required=True)
    cfg = load_config()
    models = [env("GEMINI_MODEL") or cfg.get("gemini_model", "gemini-2.5-flash"), "gemini-2.5-flash-lite"]
    last = None
    for model in dict.fromkeys(models):
        for attempt in range(4):
            body = {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": temperature, "responseMimeType": "application/json", "maxOutputTokens": 32000},
            }
            try:
                r = requests.post(GEMINI_URL.format(model=model), headers={"x-goog-api-key": key}, json=body, timeout=180)
            except requests.RequestException as ex:
                last = str(ex)
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code in (429, 500, 503):
                last = f"{model}: HTTP {r.status_code} {r.text[:200]}"
                log("gemini busy/rate-limited, retrying:", last)
                time.sleep(min(60, 10 * 2 ** attempt))
                continue
            if r.status_code >= 400:
                last = f"{model}: HTTP {r.status_code} {r.text[:300]}"
                break  # try next model
            data = r.json()
            try:
                parts = data["candidates"][0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                return _extract_json(text)
            except (KeyError, IndexError, json.JSONDecodeError) as ex:
                last = f"{model}: unparseable response ({ex}) {str(data)[:300]}"
                user = user + "\n\nYour previous answer was not valid JSON. Return ONLY the JSON object."
                continue
    raise RuntimeError(f"Gemini failed: {last}")
