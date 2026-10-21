"""Smart posting slots: exploit the slots that win, keep exploring the rest.

Each candidate slot gets a score from real 24h results (views + weighted shares/saves),
blended with Instagram's 'when your followers are online' data once the account has 100+ followers.
"""
from __future__ import annotations

import random
from datetime import timedelta

from .common import at_local, load_config, now, parse, setting

RENDER_LEAD = timedelta(minutes=40)  # time needed between approval and first possible post


def slot_stats(state: dict) -> dict[str, dict]:
    stats: dict[str, dict] = {}
    for rec in state["episodes"].values():
        s = (rec.get("metrics") or {}).get("score")
        if s is None or not rec.get("slot_label"):
            continue
        d = stats.setdefault(rec["slot_label"], {"n": 0, "sum": 0.0})
        d["n"] += 1
        d["sum"] += s
    for d in stats.values():
        d["mean"] = d["sum"] / d["n"]
    return stats


def online_prior(state: dict, label: str) -> float:
    """0..1 share of followers online in that hour (from marketer's online_followers snapshot)."""
    hours = state.get("audience", {}).get("online_by_hour_local")
    if not hours:
        return 0.0
    h = int(label.split(":")[0])
    peak = max(hours.values()) or 1
    return hours.get(str(h), 0) / peak


def rank_slots(state: dict, cfg: dict, seed: str) -> list[tuple[str, bool]]:
    """Return slot labels best-first, each flagged True if chosen for exploration."""
    labels = list(cfg.get("slots", []))
    stats = slot_stats(state)
    means = [d["mean"] for d in stats.values()]
    overall = (sum(means) / len(means)) if means else 1.0
    rng = random.Random(seed)

    def score(lbl):
        d = stats.get(lbl)
        perf = (d["mean"] / overall) if d else 1.0           # unknown slots start at average
        confidence = min(1.0, (d["n"] if d else 0) / 4)
        prior = online_prior(state, lbl)
        evening = 0.15 if lbl >= "17:00" else 0.0            # weak prior: dev audiences scroll in the evening
        return perf * (0.6 + 0.4 * confidence) + 0.5 * prior + evening * (1 - confidence)

    ranked = sorted(labels, key=score, reverse=True)
    out = [(l, False) for l in ranked]
    if rng.random() < float(cfg.get("explore_rate", 0.25)):
        under = [l for l in labels if stats.get(l, {}).get("n", 0) < 3]
        if under:
            pick = rng.choice(under)
            out = [(pick, True)] + [(l, False) for l in ranked if l != pick]
    return out


def taken(state: dict, exclude: str | None = None) -> list:
    out = []
    for k, r in state["episodes"].items():
        if k == exclude or r.get("held"):
            continue
        if r["status"] in ("approved", "rendered", "published") and r.get("slot_at"):
            out.append(parse(r.get("published_at") or r["slot_at"]))
    return out


def assign(state: dict, ep_id: str, force: bool = False):
    """Give an approved episode the best free slot (today first, then following days)."""
    cfg = load_config()
    rec = state["episodes"][ep_id]
    if rec.get("slot_at") and not force and parse(rec["slot_at"]) > now(cfg):
        return parse(rec["slot_at"])
    per_day = int(setting(state, cfg, "reels_per_day") or 3)
    gap = timedelta(minutes=int(cfg.get("min_gap_minutes", 120)))
    busy = taken(state, exclude=ep_id)
    earliest = now(cfg) + RENDER_LEAD
    for day_off in range(0, 7):
        day = (now(cfg) + timedelta(days=day_off)).date().isoformat()
        day_busy = [t for t in busy if t.date().isoformat() == day]
        if len(day_busy) >= per_day:
            continue
        for label, explore in rank_slots(state, cfg, ep_id):
            t = at_local(cfg, day, label)
            if t < earliest:
                continue
            if any(abs(t - b) < gap for b in busy):
                continue
            rec["slot_at"] = t.isoformat()
            rec["slot_label"] = label
            rec["explore"] = explore
            return t
    return None


def due(state: dict) -> list[str]:
    """Rendered episodes whose time has come (or that you asked to post now)."""
    cfg = load_config()
    n = now(cfg)
    out = []
    for k, r in state["episodes"].items():
        if r["status"] != "rendered" or r.get("held") or setting(state, cfg, "paused"):
            continue
        if r.get("post_now") or (r.get("slot_at") and parse(r["slot_at"]) <= n + timedelta(minutes=7)):
            out.append(k)
    return sorted(out, key=lambda k: state["episodes"][k].get("slot_at") or "")
