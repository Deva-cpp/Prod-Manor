"""Processes your Telegram taps, replies and commands. Runs inside every `tick` (every 15 minutes)."""
from __future__ import annotations

from . import producer, scheduler, telegram
from .common import find_episode, fmt_day, fmt_time, load_config, log, now, parse, setting, short
from .telegram import e

HELP = """<b>Prod Manor producer — commands</b>
/status — today's pipeline
/brain gemini · /brain claude — switch the writer
/perday 3 — reels per day (1-5)
/more 2 — pitch 2 more storylines now
/idea a ghost that haunts JSON.parse — add an idea to the next batch
/postnow B — publish pitch B at the next tick
/hold B · /release B — pause or resume one reel
/pause · /resume — stop or restart the whole pipeline
/report — marketer report now
Reply to any pitch with notes to rewrite it."""


def process(state: dict) -> dict:
    """Handle all pending updates. Returns a dict of follow-up actions for the tick."""
    cfg = load_config()
    owner = str(telegram.chat_id() or "")
    actions = {"report": False}
    tg = state["telegram"]
    updates = telegram.get_updates(int(tg.get("offset", 0)))
    for u in updates:
        tg["offset"] = u["update_id"] + 1
        try:
            if "callback_query" in u:
                cq = u["callback_query"]
                if str(cq["message"]["chat"]["id"]) != owner:
                    continue
                _callback(state, cfg, cq)
            elif "message" in u:
                msg = u["message"]
                if str(msg["chat"]["id"]) != owner:
                    # first-time setup helper: tell a new user their chat id, nothing else
                    if not owner and (msg.get("text") or "").startswith("/start"):
                        telegram.send_to(msg["chat"]["id"], f"Your chat id is <code>{msg['chat']['id']}</code>. "
                                         "Save it as the TELEGRAM_CHAT_ID secret in GitHub.")
                    continue
                if not msg.get("text"):
                    continue
                if _message(state, cfg, msg) == "report":
                    actions["report"] = True
        except Exception as ex:  # one bad update must never block the queue
            log("update failed:", repr(ex))
            telegram.send(f"⚠️ Couldn't process that: {e(ex)}")
    return actions


def number_episode(state: dict, ep_id: str) -> None:
    """Approved reels get a running episode number (EP 01, EP 02, ...) shown in the reel's top label."""
    rec = state["episodes"][ep_id]
    if rec.get("episode_no"):
        return
    n = max([r.get("episode_no", 0) for r in state["episodes"].values()] + [0]) + 1
    rec["episode_no"] = n
    rec["episode"]["series_tag"] = f"EP {n:02d}"


# ------------------------------------------------------------------ buttons

def _callback(state: dict, cfg: dict, cq: dict) -> None:
    data = cq.get("data", "")
    action, _, ep_id = data.partition(":")
    rec = state["episodes"].get(ep_id)
    mid = cq["message"]["message_id"]
    if not rec:
        telegram.answer(cq["id"], "That pitch no longer exists.")
        return
    ep = rec["episode"]
    if action == "ap":
        if rec["status"] not in ("pitched", "rewrite_queued"):
            telegram.answer(cq["id"], f"Already {rec['status']}.")
            return
        slot = scheduler.assign(state, ep_id)
        number_episode(state, ep_id)
        rec["status"] = "approved"
        rec["approved_at"] = now(cfg).isoformat()
        when = f"{fmt_day(slot, cfg)} {fmt_time(slot, cfg)}" if slot else "the next free slot"
        telegram.answer(cq["id"], "Approved — rendering now.")
        telegram.edit(mid, telegram.pitch_text(rec, status_line=f"✅ <b>Approved</b> · goes live {e(when)} · rendering…"))
    elif action == "rj":
        rec["status"] = "rejected"
        telegram.answer(cq["id"], "Rejected.")
        telegram.edit(mid, telegram.pitch_text(rec, status_line="❌ <b>Rejected</b>"))
    elif action == "rw":
        ask = telegram.send(f"✏️ What should change in <b>{e(ep['title'])}</b>? Reply to this message with your notes.",
                            reply_to=mid, force_reply=True)
        state["telegram"].setdefault("awaiting_rewrite", {})[str(ask)] = ep_id
        telegram.answer(cq["id"], "Send your notes as a reply.")
    elif action == "sc":
        telegram.answer(cq["id"])
        telegram.send(telegram.script_text(rec), reply_to=mid)
    elif action == "hold":
        rec["held"] = True
        telegram.answer(cq["id"], "On hold.")
        telegram.send(f"⏸ <b>{e(ep['title'])}</b> is on hold. Send /release {short(ep_id)} to put it back in the schedule.")
    elif action == "now":
        rec["post_now"] = True
        rec.pop("held", None)
        telegram.answer(cq["id"], "Posting at the next tick (≤15 min).")
    else:
        telegram.answer(cq["id"])


# ------------------------------------------------------------------ text

def _message(state: dict, cfg: dict, msg: dict):
    text = msg["text"].strip()
    reply = msg.get("reply_to_message") or {}
    awaiting = state["telegram"].setdefault("awaiting_rewrite", {})
    msg_map = state["telegram"].setdefault("msg_to_ep", {})
    rid = str(reply.get("message_id", ""))
    if rid and not text.startswith("/") and (rid in awaiting or rid in msg_map):
        ep_id = awaiting.pop(rid, None) or msg_map.get(rid)
        rec = state["episodes"].get(ep_id)
        if rec and rec["status"] in ("pitched", "rewrite_queued"):
            telegram.send(f"🔁 Rewriting <b>{e(rec['episode']['title'])}</b> with your notes…")
            producer.rewrite(state, ep_id, text)
        elif rec:
            telegram.send(f"That pitch is already {rec['status']}, so I left it alone.")
        return None

    cmd, _, arg = text.partition(" ")
    cmd = cmd.split("@")[0].lower()
    arg = arg.strip()
    st = state["settings"]
    if cmd in ("/start", "/help"):
        telegram.send(HELP + f"\n\nYour chat id: <code>{msg['chat']['id']}</code>")
    elif cmd == "/brain":
        if arg not in ("gemini", "claude"):
            telegram.send(f"Current brain: <b>{e(setting(state, cfg, 'brain'))}</b>. Use /brain gemini or /brain claude.")
        else:
            st["brain"] = arg
            extra = (" Make sure your Claude scheduled task is set up (see CLAUDE_TASK.md). If its pitches don't arrive "
                     f"by {cfg.get('claude_fallback_after')}, Gemini writes the batch.") if arg == "claude" else ""
            telegram.send(f"🧠 Brain switched to <b>{arg}</b> from tomorrow's batch.{extra}")
    elif cmd == "/perday":
        try:
            n = max(1, min(5, int(arg)))
            st["reels_per_day"] = n
            telegram.send(f"📅 Posting up to <b>{n}</b> reels per day.")
        except ValueError:
            telegram.send("Usage: /perday 3")
    elif cmd == "/pause":
        st["paused"] = True
        telegram.send("⏸ Pipeline paused. Nothing will be pitched or posted until /resume.")
    elif cmd == "/resume":
        st["paused"] = False
        telegram.send("▶️ Pipeline resumed.")
    elif cmd == "/more":
        n = max(1, min(4, int(arg) if arg.isdigit() else 2))
        telegram.send(f"✍️ Writing {n} more pitches…")
        producer.more(state, n)
    elif cmd == "/idea":
        if arg:
            state.setdefault("ideas", []).append({"text": arg[:300], "at": now(cfg).isoformat()})
            telegram.send("💡 Saved. It goes into the next batch's brief.")
        else:
            telegram.send("Usage: /idea a ghost that haunts JSON.parse")
    elif cmd in ("/postnow", "/hold", "/release"):
        ep_id = find_episode(state, arg, cfg) if arg else None
        if not ep_id:
            telegram.send(f"Which one? e.g. {cmd} B")
            return None
        rec = state["episodes"][ep_id]
        if cmd == "/postnow":
            rec["post_now"] = True
            rec.pop("held", None)
            if rec["status"] == "pitched":
                rec["status"] = "approved"
                scheduler.assign(state, ep_id)
                number_episode(state, ep_id)
            telegram.send(f"🚀 <b>{e(rec['episode']['title'])}</b> will post as soon as it's rendered.")
        elif cmd == "/hold":
            rec["held"] = True
            telegram.send(f"⏸ Holding <b>{e(rec['episode']['title'])}</b>.")
        else:
            rec.pop("held", None)
            if not rec.get("slot_at") or parse(rec["slot_at"]) < now(cfg):
                scheduler.assign(state, ep_id, force=True)
            telegram.send(f"▶️ <b>{e(rec['episode']['title'])}</b> is back on the schedule.")
    elif cmd == "/status":
        telegram.send(status_text(state, cfg))
    elif cmd == "/report":
        return "report"
    elif text.startswith("/"):
        telegram.send("Unknown command. /help lists them.")
    return None


def status_text(state: dict, cfg: dict) -> str:
    """Counts first (what's waiting on you, what's ready), then every open item whatever day it came from."""
    n = now(cfg)
    today_s = n.date().isoformat()
    icons = {"pitched": "🕓", "rewrite_queued": "📝", "approved": "🎞", "rendered": "📦", "failed": "⚠️", "published": "✅"}
    eps = state["episodes"]
    count = lambda *st: sum(1 for v in eps.values() if v["status"] in st)
    live_today = [v for v in eps.values() if v["status"] == "published" and (v.get("published_at") or "")[:10] == today_s]
    s = state["settings"]
    head = (f"<b>Status</b> · brain {e(setting(state, cfg, 'brain'))} · {setting(state, cfg, 'reels_per_day')}/day"
            + (" · ⏸ PAUSED" if s.get("paused") else ""))
    summary = (f"📜 Scripts waiting for you: <b>{count('pitched', 'rewrite_queued')}</b>\n"
               f"🎞 Reels being made: <b>{count('approved')}</b>\n"
               f"📦 Reels ready to post: <b>{count('rendered')}</b>\n"
               f"✅ Posted today: <b>{len(live_today)}</b> · all time: <b>{count('published')}</b>")
    if count("failed"):
        summary += f"\n⚠️ Failed: <b>{count('failed')}</b>"
    open_recs = [(k, v) for k, v in eps.items() if v["status"] in icons and v["status"] != "published"]
    open_recs += [(k, v) for k, v in eps.items() if v in live_today]
    order = list(icons)
    open_recs.sort(key=lambda kv: (order.index(kv[1]["status"]), kv[1].get("slot_at") or "z"))
    rows = []
    for k, v in open_recs[:15]:
        when = ""
        if v.get("slot_at") and v["status"] != "published":
            when = f" · {fmt_day(parse(v['slot_at']), cfg)} {fmt_time(parse(v['slot_at']), cfg)}"
        held = " · ⏸ held" if v.get("held") else ""
        rows.append(f"{icons[v['status']]} {short(k)} <b>{e(v['episode']['title'])}</b> — {v['status']}{when}{held}")
    if len(open_recs) > 15:
        rows.append(f"…and {len(open_recs) - 15} more")
    return head + "\n\n" + summary + ("\n\n" + "\n".join(rows) if rows else "\n\nNothing in the pipeline yet. Send /more 2 for pitches.")
