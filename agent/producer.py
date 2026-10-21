"""Morning pitches, rewrites and 'more' requests — turns brain output into stored episodes + Telegram cards."""
from __future__ import annotations

import copy
import json
from pathlib import Path

from . import brains, telegram
from .common import QUEUE, at_local, load_config, log, next_ids, now, setting, today
from .schema import EpisodeError, validate


last_rejected: list[str] = []  # why the latest _ingest threw episodes away, for the Telegram warning


def _why_none(brain: str, raw_eps: list) -> str:
    if not raw_eps:
        return f"the {brain} brain sent back no episodes"
    return f"all {len(raw_eps)} failed the quality check:\n" + "\n".join(f"• {telegram.e(r)}" for r in last_rejected[:4])


def _ingest(state: dict, raw_eps: list[dict], brain: str, day: str, cfg: dict) -> list[str]:
    ids, rejected = [], []
    clean_eps = []
    for raw in raw_eps:
        try:
            ep, warns = validate(copy.deepcopy(raw))
            clean_eps.append((ep, warns))
        except EpisodeError as ex:
            rejected.append(f"{raw.get('title', '?')}: {ex}")
    for (ep, warns), ep_id in zip(clean_eps, next_ids(state, day, len(clean_eps))):
        ep["id"] = ep_id
        state["episodes"][ep_id] = {
            "status": "pitched", "created": now(cfg).isoformat(), "day": day, "brain": brain,
            "episode": ep, "warnings": warns,
        }
        ids.append(ep_id)
    if rejected:
        log("rejected invalid episodes:", rejected)
    last_rejected[:] = rejected
    return ids


def _mark_ideas_used(state: dict) -> None:
    for i in state.get("ideas", []):
        i["used"] = True


def pitch_today(state: dict, force: bool = False, fallback_ok: bool = False) -> str:
    """Morning run. Returns a short status string for logs."""
    cfg = load_config()
    day = today(cfg)
    if setting(state, cfg, "paused"):
        return "paused"
    info = state["days"].setdefault(day, {})
    if info.get("pitched") and not force:
        return "already pitched"
    brain = setting(state, cfg, "brain") or "gemini"
    n = int(setting(state, cfg, "pitches_per_day") or 4)
    claude_file = QUEUE / "pitches" / f"{day}.json"
    note = ""
    if claude_file.exists():
        raw = json.loads(claude_file.read_text())
        eps = raw.get("episodes", raw if isinstance(raw, list) else [])
        brain_used = raw.get("brain", "claude") if isinstance(raw, dict) else "claude"
    elif brain == "claude" and not fallback_ok and now(cfg) < at_local(cfg, day, cfg.get("claude_fallback_after", "07:40")):
        return "waiting for Claude"
    else:
        if brain == "claude":
            note = "Claude's pitches didn't arrive in time, so Gemini wrote today's batch."
        system, user = brains.build_brief(state, n, day)
        eps = brains.gemini(system, user).get("episodes", [])
        brain_used = "gemini"
    ids = _ingest(state, eps, brain_used, day, cfg)
    if not ids:
        telegram.send(f"⚠️ No valid pitches today: {_why_none(brain_used, eps)}\nSend /more to try again.")
        return "no valid episodes"
    _mark_ideas_used(state)
    info.update(pitched=True, brain=brain_used, note=note)
    telegram.send_pitch_header(day, brain_used, len(ids), int(setting(state, cfg, "reels_per_day") or 3), note)
    for i, ep_id in enumerate(ids, 1):
        telegram.send_pitch(state, ep_id, i, len(ids))
    return f"pitched {len(ids)} via {brain_used}"


def more(state: dict, n: int = 2, extra: str = "") -> list[str]:
    cfg = load_config()
    day = today(cfg)
    system, user = brains.build_brief(state, n, day + f"-more{len(state['episodes'])}", extra)
    eps = brains.gemini(system, user).get("episodes", [])
    ids = _ingest(state, eps, "gemini", day, cfg)
    if not ids:
        telegram.send(f"⚠️ No new pitches: {_why_none('gemini', eps)}\nSend /more to try again.")
    for i, ep_id in enumerate(ids, 1):
        telegram.send_pitch(state, ep_id, i, len(ids))
    return ids


def rewrite(state: dict, ep_id: str, notes: str) -> str | None:
    """Rewrite one pitch with the owner's notes. Uses Gemini (free) in both modes; if no Gemini key is
    configured, the request is queued for the next Claude run."""
    cfg = load_config()
    rec = state["episodes"][ep_id]
    from .common import env
    if not env("GEMINI_API_KEY"):
        q = QUEUE / "rewrites.json"
        items = json.loads(q.read_text()) if q.exists() else []
        items.append({"id": ep_id, "notes": notes, "episode": rec["episode"]})
        q.write_text(json.dumps(items, indent=2))
        rec["status"] = "rewrite_queued"
        telegram.send(f"📝 Queued your notes for Claude's next run: {rec['episode']['title']}")
        return None
    system, user = brains.rewrite_brief(state, rec["episode"], notes)
    eps = brains.gemini(system, user, temperature=0.7).get("episodes", [])
    new_ids = _ingest(state, eps[:1], "gemini", rec["day"], cfg)
    if not new_ids:
        telegram.send("⚠️ The rewrite came back invalid. Try different notes, or approve the original.")
        return None
    new = new_ids[0]
    state["episodes"][new]["rewrite_of"] = ep_id
    state["episodes"][new]["notes"] = notes
    rec["status"] = "superseded"
    rec["superseded_by"] = new
    telegram.send_pitch(state, new, None, None, rewritten=True)
    return new


def ingest_claude_rewrites(state: dict) -> int:
    """Pick up rewrite results Claude wrote as queue/pitches/<date>-rewrite-<id>.json."""
    cfg = load_config()
    n = 0
    for f in sorted((QUEUE / "pitches").glob("*-rewrite-*.json")):
        done = state.setdefault("ingested_files", [])
        if f.name in done:
            continue
        raw = json.loads(f.read_text())
        old = raw.get("rewrite_of")
        if old in state["episodes"]:
            day = state["episodes"][old]["day"]
            ids = _ingest(state, raw.get("episodes", [])[:1], "claude", day, cfg)
            if ids:
                state["episodes"][ids[0]]["rewrite_of"] = old
                state["episodes"][old].update(status="superseded", superseded_by=ids[0])
                telegram.send_pitch(state, ids[0], None, None, rewritten=True)
                n += 1
        done.append(f.name)
    q = QUEUE / "rewrites.json"
    if n and q.exists():
        q.write_text("[]")
    return n
