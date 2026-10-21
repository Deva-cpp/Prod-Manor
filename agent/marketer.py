"""The marketer loop: collect results, score every reel, learn what works, report nightly.

Score favors the signals Instagram's ranking rewards for Reels: reach/views, shares (sends),
saves and comments, with watch time as a quality multiplier.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from . import instagram, telegram
from .common import LEARNINGS, load_config, log, now, parse, setting, short
from .schema import NAMES
from .telegram import e

CHECKPOINTS = [("24h", timedelta(hours=24)), ("72h", timedelta(hours=72)), ("7d", timedelta(days=7))]


def score(m: dict) -> float:
    views = m.get("views") or m.get("reach") or 0
    base = views + 8 * (m.get("shares") or 0) + 6 * (m.get("saved") or 0) + 3 * (m.get("comments") or 0) + (m.get("likes") or 0)
    watch = (m.get("ig_reels_avg_watch_time") or 0) / 1000.0  # ms → s
    return round(base * (1 + min(watch, 30) / 30), 1)


def collect(state: dict) -> int:
    """Pull insights for reels that reached a checkpoint. Returns how many were updated."""
    cfg = load_config()
    n = now(cfg)
    done = 0
    for k, r in state["episodes"].items():
        if r["status"] != "published" or not r.get("ig", {}).get("media_id"):
            continue
        pub = parse(r.get("published_at"))
        mets = r.setdefault("metrics", {})
        for name, age in CHECKPOINTS:
            if name in mets or n - pub < age:
                continue
            try:
                m = instagram.reel_insights(r["ig"]["media_id"])
            except instagram.IGError as ex:
                log("insights failed", k, ex)
                break
            m["at"] = n.isoformat()
            mets[name] = m
            if name == "24h" or "score" not in mets:
                mets["score"] = score(m)  # slot learning uses the 24h score so slots compare fairly
            mets["latest_score"] = score(m)
            done += 1
    return done


def snapshot_account(state: dict) -> None:
    cfg = load_config()
    try:
        snap = instagram.account_snapshot()
    except Exception as ex:
        log("account snapshot failed:", ex)
        return
    if snap.get("followers_count") is not None:
        state["followers"].append({"at": now(cfg).isoformat(), "count": snap["followers_count"]})
        state["followers"] = state["followers"][-120:]
    online = snap.get("online_followers")
    if online:
        # API hours are in the account's reporting timezone (UTC offset of Pacific time in Meta docs);
        # store as-is keyed by hour and let the scheduler compare relative peaks.
        local = {}
        shift = int(now(cfg).utcoffset().total_seconds() // 3600) + 8  # PT(UTC-8) → local, approximate
        for h, v in online.items():
            local[str((int(h) + shift) % 24)] = v
        state.setdefault("audience", {})["online_by_hour_local"] = local


def learnings(state: dict) -> str:
    rows = [r for r in state["episodes"].values() if (r.get("metrics") or {}).get("score") is not None]
    if len(rows) < 3:
        return ("Too little data yet (" + str(len(rows)) + " measured reels). Keep testing different hook styles, "
                "monsters and slots. Strong default: a threat or relatable-pain hook in the first 2 seconds.")
    by_monster, by_slot, by_level, by_lang = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    for r in rows:
        ep, s = r["episode"], r["metrics"]["score"]
        by_monster[ep["monster"]].append(s)
        by_level[ep["level"]].append(s)
        by_lang[ep["language"]].append(s)
        if r.get("slot_label"):
            by_slot[r["slot_label"]].append(s)
    avg = lambda d: sorted(((k, sum(v) / len(v), len(v)) for k, v in d.items()), key=lambda x: -x[1])
    best = sorted(rows, key=lambda r: -r["metrics"]["score"])[:3]
    worst = sorted(rows, key=lambda r: r["metrics"]["score"])[:2]
    fmt = lambda xs, names=None: ", ".join(f"{(names or {}).get(k, k)} {v:.0f} (n={n})" for k, v, n in xs)
    out = [
        f"Measured reels: {len(rows)}. Score = views + 8×shares + 6×saves + 3×comments + likes, boosted by watch time.",
        f"Monsters by avg score: {fmt(avg(by_monster), NAMES)}.",
        f"Level: {fmt(avg(by_level))}. Language: {fmt(avg(by_lang))}.",
        f"Slots: {fmt(avg(by_slot))}.",
        "Top hooks to learn from (do NOT copy; find the pattern):",
        *[f"- \"{r['episode']['hook']}\" ({NAMES[r['episode']['monster']]}, {r['episode']['concept']}) → {r['metrics']['score']:.0f}" for r in best],
        "Weakest hooks (avoid this pattern):",
        *[f"- \"{r['episode']['hook']}\" → {r['metrics']['score']:.0f}" for r in worst],
    ]
    return "\n".join(out)


def nightly(state: dict, send: bool = True) -> str:
    cfg = load_config()
    collect(state)
    snapshot_account(state)
    text = learnings(state)
    LEARNINGS.write_text(text + "\n")
    if not send:
        return text
    n = now(cfg)
    today = n.date().isoformat()
    posted = [(k, r) for k, r in state["episodes"].items() if r["status"] == "published" and (r.get("published_at") or "")[:10] == today]
    lines = [f"🌙 <b>Marketer report · {e(today)}</b>"]
    f = state.get("followers") or []
    if f:
        lines.append(f"👥 Followers: <b>{f[-1]['count']}</b>" + (f" ({f[-1]['count'] - f[-8]['count']:+d} vs a week ago)" if len(f) >= 8 else ""))
    if posted:
        lines.append(f"Posted today: {len(posted)}")
        for k, r in posted:
            lines.append(f"• {short(k)} <b>{e(r['episode']['title'])}</b> at {r.get('slot_label')} — <a href=\"{e(r.get('ig', {}).get('permalink'))}\">open</a>")
    else:
        lines.append("Nothing posted today.")
    week = [r for r in state["episodes"].values() if r["status"] == "published" and (r.get("metrics") or {}).get("24h")
            and parse(r["published_at"]) > n - timedelta(days=7)]
    if week:
        top = max(week, key=lambda r: r["metrics"]["score"])
        m = top["metrics"]["24h"]
        lines.append(f"🏆 Best this week: <b>{e(top['episode']['title'])}</b> — {m.get('views') or 0} views, "
                     f"{m.get('shares') or 0} shares, {m.get('saved') or 0} saves in 24h")
    lines.append("\n<b>What I learned</b>\n" + e(text))
    pending = [r for r in state["episodes"].values() if r["status"] in ("approved", "rendered") and not r.get("held")]
    if len(pending) < int(setting(state, cfg, "reels_per_day") or 3):
        lines.append("\n💡 Tomorrow's queue is thin. Approve more pitches in the morning, or send /more.")
    msg = "\n".join(lines)[:4000]
    telegram.send(msg)
    return text
