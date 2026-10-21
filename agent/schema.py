"""Episode contract shared by both brains (Gemini and Claude) and the renderer.

validate() repairs what it safely can (durations, lengths, missing outro) and raises
EpisodeError for anything that would produce a broken or misleading reel.
"""
from __future__ import annotations

import copy
import json
import re
import sys

CAST = ["junior", "null", "caller", "twins", "leak", "ollie"]
MONSTERS = CAST[1:]
NAMES = {"junior": "Junior", "null": "The Null", "caller": "The Caller", "twins": "Fork & Join", "leak": "The Leak", "ollie": "Ollie One-Off"}
BEAT_TYPES = {"pager", "title", "scene", "code", "crash", "fix", "outro"}
EXPRS = {"neutral", "happy", "scared"}
GESTURES = {"wave", "point", "shrug", "celebrate", "cower", "facepalm", "think", "nod", "shake_head", "type", "beckon",
            "dance", "laugh", "gasp", "tremble", "look_up", "look_down", "look_left", "look_right"}
ACTIONS = {"idle", "enter_left", "enter_right", "exit_left", "exit_right", "shake", "hop", "grow", "shrink", "pop_in",
           "fade_in", "fade_out", "defeated", "peek", "spin", "float", "stack"}
BGS = {"hallway", "bedroom", "server_room"}
LIGHTS = {"dark", "flashlight", "flicker", "red", "normal"}
SFX = {"pager", "ring", "crash", "ding", "whoosh", "thud", "creak", "heartbeat", "slurp", "glitch"}
LANGS = {"javascript", "typescript", "python", "java", "go"}

EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️]")


class EpisodeError(ValueError):
    pass


def _txt(v, n):
    s = EMOJI.sub("", str(v or "")).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _num(v, lo, hi, default):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, x))


def _actor(a: dict, warn: list) -> dict | None:
    if not isinstance(a, dict) or a.get("who") not in CAST:
        warn.append(f"dropped actor {a!r}")
        return None
    out = {"who": a["who"], "expr": a.get("expr") if a.get("expr") in EXPRS else "neutral",
           "x": _num(a.get("x"), -0.2, 1.2, 0.5)}
    if a.get("scale") is not None:
        out["scale"] = _num(a["scale"], 0.3, 2.0, 1)
    if a.get("action") in ACTIONS:
        out["action"] = a["action"]
    if a.get("amount") is not None:
        out["amount"] = _num(a["amount"], 0.2, 3.0, 1.5)
    if isinstance(a.get("to"), dict):
        out["to"] = {k: _num(a["to"][k], -0.3, 1.3 if k == "x" else 2.4, 1) for k in ("x", "scale") if k in a["to"]}
    if a.get("expr_to") in EXPRS:
        out["expr_to"] = a["expr_to"]
        out["expr_at"] = _num(a.get("expr_at"), 0.05, 0.95, 0.5)
    if a.get("flip"):
        out["flip"] = True
    if a.get("gesture") in GESTURES:
        out["gesture"] = a["gesture"]
        if a.get("gesture_at") is not None:
            out["gesture_at"] = _num(a["gesture_at"], 0, 0.95, 0)
    if isinstance(a.get("gestures"), list):
        gs = [{"g": g.get("g") or g.get("gesture"), "at": _num(g.get("at"), 0, 0.95, 0)} for g in a["gestures"][:4]
              if isinstance(g, dict) and (g.get("g") or g.get("gesture")) in GESTURES]
        if gs:
            out["gestures"] = gs
    if a["who"] == "caller" and a.get("copies"):
        out["copies"] = int(_num(a["copies"], 1, 6, 3))
    if a.get("opacity") is not None:
        out["opacity"] = _num(a["opacity"], 0.1, 1, 1)
    if a.get("z") is not None:
        out["z"] = int(_num(a["z"], -5, 5, 0))
    return out


def _beat(b: dict, ep: dict, warn: list) -> dict | None:
    t = b.get("type")
    if t not in BEAT_TYPES:
        warn.append(f"dropped beat type {t!r}")
        return None
    out = {"type": t, "dur": _num(b.get("dur"), 1.5, 6.0, 3.0)}
    if b.get("narration"):
        words = _txt(b["narration"], 200).split()
        out["narration"] = " ".join(words[:20])
    if b.get("on_screen"):
        out["on_screen"] = _txt(b["on_screen"], 40)
    if isinstance(b.get("sfx"), list):
        out["sfx"] = [s for s in b["sfx"] if s in SFX][:3]
    if b.get("shake"):
        out["shake"] = True
    if isinstance(b.get("camera"), dict):
        c = b["camera"]
        out["camera"] = {k: _num(c[k], 0.9, 1.4, 1) for k in ("zoom_from", "zoom_to") if k in c}
        if "focus_x" in c:
            out["camera"]["focus_x"] = _num(c["focus_x"], 0, 1, 0.5)
    if isinstance(b.get("actors"), list):
        acts = [x for x in (_actor(a, warn) for a in b["actors"][:4]) if x]
        if acts:
            out["actors"] = acts
    if isinstance(b.get("say"), list) and t != "scene":
        warn.append(f"dropped dialogue on a {t} beat (dialogue only plays in scene beats)")
    elif isinstance(b.get("say"), list):
        says = [{"who": s["who"], "text": _txt(s.get("text"), 70)} for s in b["say"][:2]
                if isinstance(s, dict) and s.get("who") in CAST and s.get("text")]
        if says:
            out["say"] = says
    if t == "pager":
        out.update(time=_txt(b.get("time") or "3:00 AM", 10), text=_txt(b.get("text") or "PROD IS DOWN", 24),
                   sub=_txt(b.get("sub") or "PagerDuty · Severity 1", 34))
    elif t == "title":
        out.update(text=_txt(b.get("text") or ep.get("title"), 40), sub=_txt(b.get("sub") or ep.get("hook"), 70))
        if b.get("kicker"):
            out["kicker"] = _txt(b["kicker"], 26)
        out["monster"] = b.get("monster") if b.get("monster") in MONSTERS else ep["monster"]
    elif t == "scene":
        out["bg"] = b.get("bg") if b.get("bg") in BGS else "hallway"
        out["light"] = b.get("light") if b.get("light") in LIGHTS else "dark"
    elif t in ("code", "fix"):
        lines = [str(x).rstrip()[:40] for x in (b.get("lines") or []) if str(x).strip() or True][:7]
        lines = [EMOJI.sub("", l) for l in lines]
        if not any(l.strip() for l in lines):
            raise EpisodeError(f"{t} beat has no code lines")
        out["lines"] = lines
        out["lang"] = b.get("lang") if b.get("lang") in LANGS else ep.get("language", "javascript")
        if b.get("file"):
            out["file"] = _txt(b["file"], 24)
        if t == "code":
            hl = [int(n) for n in (b.get("highlight") or []) if str(n).isdigit() and 1 <= int(n) <= len(lines)]
            out["highlight"] = hl
            if b.get("error"):
                out["error"] = _txt(b["error"], 110)
        else:
            fl = int(_num(b.get("fix_line"), 1, len(lines), len(lines)))
            after = str(b.get("after") or "").rstrip()[:40]
            out.update(fix_line=fl, after=after, note=_txt(b.get("note") or "Fixed.", 90))
    elif t == "crash":
        out.update(title=_txt(b.get("title") or "CRASH!", 16), text=_txt(b.get("text") or "Uncaught Error", 90))
    elif t == "outro":
        out.update(lesson=_txt(b.get("lesson"), 90), cta=_txt(b.get("cta") or "Follow before the next bug wakes up", 60))
        nm = b.get("next_monster")
        out["next_monster"] = nm if nm in MONSTERS and nm != ep["monster"] else next(m for m in MONSTERS if m != ep["monster"])
        if b.get("kicker"):
            out["kicker"] = _txt(b["kicker"], 20)
    return out


def _repair_fix(b: dict, code: dict | None, warn: list) -> None:
    """A fix beat shows the BUGGY lines and swaps fix_line for `after`. Brains often hand over the already
    fixed code instead; the code beat before it still has the buggy version, so recover the one changed line."""
    lines, fl, after = b["lines"], b["fix_line"], b["after"]
    if after and after != lines[fl - 1]:
        return
    if code and len(code["lines"]) == len(lines):
        diff = [i for i, (x, y) in enumerate(zip(code["lines"], lines)) if x.rstrip() != y.rstrip()]
        if len(diff) == 1:
            i = diff[0]
            b.update(lines=list(code["lines"]), fix_line=i + 1, after=lines[i])
            warn.append("fix beat had the fixed code in `lines`; rebuilt it from the code beat")
            return
    raise EpisodeError("fix beat must change its fix_line to a different `after` line "
                       "(`lines` = the buggy code from the code beat, `after` = the corrected text of line fix_line)")


def validate(raw: dict) -> tuple[dict, list[str]]:
    """Return a cleaned episode plus warnings. Raises EpisodeError if it can't become a good reel."""
    warn: list[str] = []
    if not isinstance(raw, dict):
        raise EpisodeError("episode must be an object")
    ep = {k: raw.get(k) for k in ("id", "title", "monster", "concept", "level", "language", "hook", "logline")}
    if ep["monster"] not in MONSTERS:
        raise EpisodeError(f"monster must be one of {MONSTERS}, got {ep['monster']!r}")
    ep["title"] = _txt(ep["title"] or "Untitled Haunting", 40)
    ep["hook"] = _txt(ep["hook"] or "", 80)
    ep["concept"] = _txt(ep["concept"] or "", 80)
    ep["logline"] = _txt(ep["logline"] or "", 200)
    ep["level"] = ep["level"] if ep["level"] in ("beginner", "intermediate") else "beginner"
    ep["language"] = ep["language"] if ep["language"] in LANGS else "javascript"
    beats = [x for x in (_beat(b, ep, warn) for b in (raw.get("beats") or []) if isinstance(b, dict)) if x]
    types = [b["type"] for b in beats]
    if "code" not in types or "fix" not in types:
        raise EpisodeError("episode needs at least one code beat and one fix beat")
    for i, b in enumerate(beats):
        if b["type"] == "fix":
            _repair_fix(b, next((c for c in reversed(beats[:i]) if c["type"] == "code"), None), warn)
    if types[0] not in ("pager", "title"):
        beats.insert(0, {"type": "title", "dur": 2.4, "text": ep["title"], "sub": ep["hook"], "monster": ep["monster"]})
        warn.append("inserted title hook at start")
    if types[-1] != "outro":
        beats = [b for b in beats if b["type"] != "outro"]
        beats.append({"type": "outro", "dur": 3.2, "lesson": ep["concept"], "cta": "Follow before the next bug wakes up",
                      "next_monster": next(m for m in MONSTERS if m != ep["monster"])})
        warn.append("moved/added outro at end")
    beats = beats[:10]
    total = sum(b["dur"] for b in beats)
    if total > 42:
        k = 42 / total
        for b in beats:
            b["dur"] = round(max(1.5, b["dur"] * k), 2)
        warn.append(f"compressed runtime from {total:.1f}s")
    ep["beats"] = beats
    caption = EMOJI.sub(lambda m: m.group(0), str(raw.get("caption") or ""))[:1900].strip()
    if not caption:
        caption = f"{ep['hook']}\n\n{ep['concept']}\n\nWhat's the worst bug you've hit at 3 AM?"
    ep["caption"] = caption
    tags = []
    for t in raw.get("hashtags") or []:
        t = "#" + re.sub(r"[^A-Za-z0-9_]", "", str(t).lstrip("#"))
        if len(t) > 2 and t.lower() not in [x.lower() for x in tags]:
            tags.append(t)
    ep["hashtags"] = (tags or ["#coding", "#programming", "#codinghumor", "#softwareengineer", "#learntocode"])[:10]
    ep["cover_text"] = _txt(raw.get("cover_text") or ep["title"], 24).upper()
    if raw.get("series_tag"):
        ep["series_tag"] = _txt(raw["series_tag"], 12)
    return ep, warn


def full_caption(ep: dict, handle: str = "") -> str:
    tail = " ".join(ep.get("hashtags", []))
    cap = ep["caption"]
    if handle and handle not in cap:
        cap += f"\n\nFollow {handle} — the next bug wakes at 3 AM."
    return (cap + "\n\n" + tail).strip()[:2200]


def runtime(ep: dict) -> float:
    return round(sum(float(b.get("dur", 3)) for b in ep.get("beats", [])), 1)


# JSON skeleton given to the brains as the output contract
CONTRACT = {
    "episodes": [{
        "title": "string, 2-6 words",
        "monster": "null | caller | twins | leak | ollie",
        "concept": "the one concept taught, e.g. 'optional chaining ?.'",
        "level": "beginner | intermediate",
        "language": "javascript | typescript | python | java | go",
        "hook": "the scroll-stopping line shown in the first 2 seconds",
        "logline": "one sentence storyline for the approval card",
        "beats": ["... 6-9 beat objects following the beat schema ..."],
        "caption": "Instagram caption, 300-600 chars, ends with a question",
        "hashtags": ["#coding", "..."],
        "cover_text": "2-3 WORDS",
    }]
}


if __name__ == "__main__":  # python -m agent.schema file.json
    data = json.loads(open(sys.argv[1]).read())
    eps = data.get("episodes", [data]) if isinstance(data, dict) else data
    ok = True
    for i, e in enumerate(eps):
        try:
            clean, w = validate(copy.deepcopy(e))
            print(f"[{i}] OK  {clean['title']!r} ({clean['monster']}, {runtime(clean)}s)" + (f"  warnings: {w}" if w else ""))
        except EpisodeError as ex:
            ok = False
            print(f"[{i}] INVALID: {ex}")
    sys.exit(0 if ok else 1)
