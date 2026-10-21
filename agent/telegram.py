"""Telegram Bot API wrapper + the message cards the producer sends you."""
from __future__ import annotations

import html
import json
from pathlib import Path

import requests

from .common import env, log, short
from .schema import NAMES, runtime

API = "https://api.telegram.org/bot{token}/{method}"
EMO = {"null": "👻", "caller": "☎️", "twins": "👯", "leak": "🫧", "ollie": "🕴️"}


def _call(method: str, files=None, **params):
    token = env("TELEGRAM_BOT_TOKEN")
    if not token:
        log(f"(telegram disabled) {method}: {json.dumps(params, ensure_ascii=False)[:300]}")
        return {"ok": True, "result": {"message_id": 0}}
    url = API.format(token=token, method=method)
    if files:
        data = {k: (json.dumps(v) if isinstance(v, (dict, list)) else v) for k, v in params.items()}
        r = requests.post(url, data=data, files=files, timeout=120)
    else:
        r = requests.post(url, json=params, timeout=60)
    out = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"ok": False, "description": r.text}
    if not out.get("ok"):
        log(f"telegram {method} failed: {out.get('description')}")
    return out


def chat_id():
    return env("TELEGRAM_CHAT_ID")


def send(text: str, buttons=None, reply_to: int | None = None, force_reply: bool = False) -> int:
    params = {"chat_id": chat_id(), "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if buttons:
        params["reply_markup"] = {"inline_keyboard": buttons}
    elif force_reply:
        params["reply_markup"] = {"force_reply": True, "input_field_placeholder": "What should change?"}
    if reply_to:
        params["reply_parameters"] = {"message_id": reply_to, "allow_sending_without_reply": True}
    res = _call("sendMessage", **params)
    return (res.get("result") or {}).get("message_id", 0)


def send_to(chat, text: str) -> None:
    _call("sendMessage", chat_id=chat, text=text, parse_mode="HTML")


def edit(message_id: int, text: str, buttons=None) -> None:
    if not message_id:
        return
    params = {"chat_id": chat_id(), "message_id": message_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    params["reply_markup"] = {"inline_keyboard": buttons or []}
    _call("editMessageText", **params)


def answer(callback_id: str, text: str = "") -> None:
    _call("answerCallbackQuery", callback_query_id=callback_id, text=text[:190])


def send_video(path: Path, caption: str, buttons=None) -> int:
    params = {"chat_id": chat_id(), "caption": caption[:1024], "parse_mode": "HTML", "supports_streaming": "true"}
    if buttons:
        params["reply_markup"] = {"inline_keyboard": buttons}
    if not env("TELEGRAM_BOT_TOKEN"):
        log(f"(telegram disabled) sendVideo {path}")
        return 0
    with open(path, "rb") as fh:
        res = _call("sendVideo", files={"video": (path.name, fh, "video/mp4")}, **params)
    return (res.get("result") or {}).get("message_id", 0)


def get_updates(offset: int) -> list[dict]:
    relay = env("TELEGRAM_RELAY_URL")
    if relay:
        return _relay_updates(relay.rstrip("/"), offset)
    res = _call("getUpdates", offset=offset, timeout=0, allowed_updates=["message", "callback_query"])
    return res.get("result") or [] if isinstance(res.get("result"), list) else []


def _relay_updates(relay: str, offset: int) -> list[dict]:
    """Instant mode (relay/worker.js): Telegram pushes updates to the relay, we pull them from there.
    Like getUpdates' offset, updates before `offset` were handled by a run whose state is saved, so drop them first."""
    auth = {"Authorization": f"Bearer {env('RELAY_SECRET', required=True)}"}
    try:
        if offset > 0:
            requests.post(f"{relay}/ack", params={"upto": offset - 1}, headers=auth, timeout=30)
        r = requests.get(f"{relay}/updates", headers=auth, timeout=30)
        if r.status_code == 403:
            log("relay refused the RELAY_SECRET")
            send("⚠️ Instant mode: the relay refused the bot. RELAY_SECRET in GitHub doesn't match the one in Cloudflare, "
                 "so your taps are waiting unread.")
            return []
        res = r.json()
    except (requests.RequestException, ValueError) as ex:
        log(f"relay unavailable: {ex!r}")
        return []
    updates = {u["update_id"]: u for u in res.get("result") or [] if "update_id" in u}
    try:  # the tap that started this run, handed over directly in case KV doesn't show it yet
        handed = json.loads(env("RELAY_UPDATE") or "null")
        if isinstance(handed, dict) and "update_id" in handed:
            updates.setdefault(handed["update_id"], handed)
    except ValueError:
        pass
    return [updates[k] for k in sorted(updates) if k >= offset]


# ------------------------------------------------------------------ cards

def e(s) -> str:
    return html.escape(str(s or ""), quote=False)


def pitch_text(rec: dict, idx=None, total=None, status_line: str = "") -> str:
    ep = rec["episode"]
    m = ep["monster"]
    beats = ep["beats"]
    code = next((b for b in beats if b["type"] == "code"), {})
    fix = next((b for b in beats if b["type"] == "fix"), {})
    bug_line = (fix.get("lines") or [""])[max(0, fix.get("fix_line", 1) - 1)] if fix else ""
    head = f"🎬 <b>Pitch {short(ep['id'])}</b>" + (f" · {idx}/{total}" if idx else "") + f" · {EMO.get(m, '')} {e(NAMES[m])} · {e(ep['level'])} · {e(ep['language'])}"
    parts = [
        head,
        f"<b>“{e(ep['title'])}”</b>",
        f"🪝 <i>Hook (0–2s):</i> {e(ep['hook'])}",
        f"📖 {e(ep['logline'])}",
        f"🐞 <code>{e(bug_line)}</code>  →  ✅ <code>{e(fix.get('after', ''))}</code>",
    ]
    if code.get("error"):
        parts.append(f"💥 <i>{e(code['error'])}</i>")
    parts.append(f"🎓 {e(ep['concept'])} · ⏱ {runtime(ep)}s · {len(beats)} beats · brain: {e(rec.get('brain'))}")
    if rec.get("notes"):
        parts.append(f"✏️ <i>Rewritten with your notes:</i> {e(rec['notes'])}")
    if status_line:
        parts.append(status_line)
    return "\n".join(parts)


def pitch_buttons(ep_id: str):
    return [[{"text": "✅ Approve", "callback_data": f"ap:{ep_id}"},
             {"text": "✏️ Rewrite", "callback_data": f"rw:{ep_id}"},
             {"text": "❌ Reject", "callback_data": f"rj:{ep_id}"}],
            [{"text": "📜 Full script", "callback_data": f"sc:{ep_id}"}]]


def send_pitch_header(day: str, brain: str, n: int, per_day: int, note: str = "") -> None:
    text = (f"☀️ <b>Morning, producer.</b> {n} storylines for {e(day)} from the <b>{e(brain)}</b> brain.\n"
            f"Approve up to {per_day} — I'll render them and post each at its best slot.\n"
            f"Tap ✏️ Rewrite (or just reply to a pitch) to give notes.")
    if note:
        text += f"\n\nℹ️ {e(note)}"
    send(text)


def send_pitch(state: dict, ep_id: str, idx, total, rewritten: bool = False) -> None:
    rec = state["episodes"][ep_id]
    mid = send(("🔁 <b>Rewrite ready</b>\n" if rewritten else "") + pitch_text(rec, idx, total), pitch_buttons(ep_id))
    rec["pitch_msg_id"] = mid
    state["telegram"].setdefault("msg_to_ep", {})[str(mid)] = ep_id


def script_text(rec: dict) -> str:
    ep = rec["episode"]
    lines = [f"📜 <b>{e(ep['title'])}</b> — full script"]
    for i, b in enumerate(ep["beats"], 1):
        row = f"\n<b>{i}. {b['type'].upper()}</b> ({b['dur']}s)"
        if b.get("text"):
            row += f" — {e(b['text'])}"
        if b.get("sub"):
            row += f"\n   <i>{e(b['sub'])}</i>"
        for s in b.get("say", []):
            row += f"\n   💬 {e(NAMES.get(s['who'], s['who']))}: “{e(s['text'])}”"
        if b.get("lines"):
            row += "\n<pre>" + e("\n".join(b["lines"])) + "</pre>"
        if b.get("error"):
            row += f"\n   💥 {e(b['error'])}"
        if b.get("after"):
            row += f"\n   ✅ line {b.get('fix_line')} → <code>{e(b['after'])}</code> · {e(b.get('note'))}"
        if b.get("lesson"):
            row += f"\n   🎓 {e(b['lesson'])}"
        if b.get("narration"):
            row += f"\n   🎙 {e(b['narration'])}"
        lines.append(row)
    lines.append(f"\n<b>Caption</b>\n{e(ep['caption'])}\n{e(' '.join(ep['hashtags']))}")
    return "\n".join(lines)[:4000]
