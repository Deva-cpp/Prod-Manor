"""Entry points for the GitHub workflows and for running things by hand.

  python -m agent plan [--force] [--fallback]   morning pitches → Telegram
  python -m agent tick                          Telegram inbox, scheduling, publishing, metrics
  python -m agent render                        render approved reels into ./media
  python -m agent report                        nightly marketer report + learnings
  python -m agent token                         refresh the Instagram token
  python -m agent brief [--n 4]                 print the exact brief the brain gets (used by the Claude task)
  python -m agent validate FILE                 check a pitches file against the episode contract
"""
from __future__ import annotations

import argparse
import sys

from . import bot, jobs, marketer, producer
from .common import load_state, log, save_state


def tick(state: dict) -> None:
    """Runs every 15 minutes. Each step is idempotent, so a skipped or cancelled run heals on the next one."""
    from .common import at_local, load_config, now, setting, today

    cfg = load_config()
    actions = bot.process(state)
    save_state(state)  # persist inbox progress early, so a later failure never replays your taps
    rendered = jobs.ingest_renders(state)
    producer.ingest_claude_rewrites(state)
    day, n = today(cfg), now(cfg)
    info = state["days"].setdefault(day, {})
    if not info.get("pitched") and n >= at_local(cfg, day, cfg.get("pitch_time", "07:00")):
        fallback = n >= at_local(cfg, day, cfg.get("claude_fallback_after", "07:40"))
        try:
            log("pitch:", producer.pitch_today(state, fallback_ok=fallback))
        except Exception as ex:
            log("pitch failed:", repr(ex))
            if not info.get("pitch_error_sent"):
                from . import telegram
                telegram.send(f"⚠️ Morning pitch failed: <code>{ex}</code>\nI'll retry every 15 minutes. /more forces it.")
                info["pitch_error_sent"] = True
        save_state(state)
    jobs.request_render(state)
    published = jobs.publish_due(state)
    save_state(state)
    updated = marketer.collect(state)
    nightly_due = not info.get("reported") and n >= at_local(cfg, day, cfg.get("report_time", "23:30"))
    if actions.get("report") or nightly_due:
        marketer.nightly(state)
        if nightly_due:
            info["reported"] = True
            log("token:", jobs.token_upkeep(state))
    log(f"tick done: rendered_in={rendered} published={published} metrics_updated={updated}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="agent")
    ap.add_argument("cmd")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--fallback", action="store_true")
    ap.add_argument("--n", type=int, default=None)
    a = ap.parse_args(argv)
    state = load_state()

    if a.cmd == "validate":
        from .schema import __file__ as schema_file
        import runpy
        sys.argv = [schema_file, a.file]
        runpy.run_path(schema_file, run_name="__main__")
        return
    if a.cmd == "brief":
        from . import brains
        from .common import load_config, setting, today
        cfg = load_config()
        n = a.n or int(setting(state, cfg, "pitches_per_day") or 4)
        system, user = brains.build_brief(state, n, today(cfg))
        print("=== SYSTEM ===\n" + system + "\n\n=== BRIEF ===\n" + user)
        return

    try:
        if a.cmd == "plan":
            log(producer.pitch_today(state, force=a.force, fallback_ok=a.fallback))
            producer.ingest_claude_rewrites(state)
        elif a.cmd == "tick":
            tick(state)
        elif a.cmd == "render":
            log("rendered:", jobs.render_pending(state))
        elif a.cmd == "report":
            marketer.nightly(state)
            log("token:", jobs.token_upkeep(state))
        elif a.cmd == "token":
            log(jobs.token_upkeep(state))
        else:
            ap.error(f"unknown command {a.cmd}")
    finally:
        save_state(state)


if __name__ == "__main__":
    main()
