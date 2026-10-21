"""Shared config, state and time helpers. All state lives in state/db.json, committed by the workflows."""
from __future__ import annotations

import json
import os
import string
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "db.json"
LEARNINGS = ROOT / "state" / "learnings.md"
QUEUE = ROOT / "queue"
MEDIA_OUT = ROOT / "media"


def load_config() -> dict:
    cfg = yaml.safe_load((ROOT / "config.yaml").read_text())
    return cfg


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    v = os.environ.get(name, default)
    if required and not v:
        raise RuntimeError(f"Missing required secret/env: {name}")
    return v


# ------------------------------------------------------------------ state

DEFAULT_STATE = {
    "episodes": {},
    "telegram": {"offset": 0, "awaiting_rewrite": {}},
    "settings": {},
    "ideas": [],
    "days": {},           # date -> {"pitched": true, "brain": "gemini", "note": ...}
    "token": {},          # {"refreshed_at": iso, "expires_at": iso}
    "render": {},         # {"requested_at": iso}
    "followers": [],      # [{"at": iso, "count": n}]
}


def load_state() -> dict:
    if STATE.exists():
        data = json.loads(STATE.read_text() or "{}")
    else:
        data = {}
    for k, v in DEFAULT_STATE.items():
        data.setdefault(k, json.loads(json.dumps(v)))
    return data


def save_state(state: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=False) + "\n")


def setting(state: dict, cfg: dict, key: str):
    """Runtime override (set from Telegram) wins over config.yaml."""
    return state["settings"].get(key, cfg.get(key))


# ------------------------------------------------------------------ time

def tz(cfg: dict) -> ZoneInfo:
    return ZoneInfo(cfg.get("timezone", "Asia/Kolkata"))


def now(cfg: dict) -> datetime:
    fake = os.environ.get("PM_NOW")  # tests: ISO timestamp
    if fake:
        d = datetime.fromisoformat(fake)
        return d if d.tzinfo else d.replace(tzinfo=tz(cfg))
    return datetime.now(tz(cfg))


def today(cfg: dict) -> str:
    return now(cfg).date().isoformat()


def at_local(cfg: dict, day: str, hhmm: str) -> datetime:
    h, m = (int(x) for x in hhmm.split(":"))
    d = datetime.fromisoformat(day)
    return datetime(d.year, d.month, d.day, h, m, tzinfo=tz(cfg))


def parse(iso: str | None) -> datetime | None:
    return datetime.fromisoformat(iso) if iso else None


def fmt_time(dt: datetime, cfg: dict) -> str:
    return dt.astimezone(tz(cfg)).strftime("%H:%M")


def fmt_day(dt: datetime, cfg: dict) -> str:
    local = dt.astimezone(tz(cfg))
    n = now(cfg)
    if local.date() == n.date():
        return "today"
    if local.date() == (n + timedelta(days=1)).date():
        return "tomorrow"
    return local.strftime("%a %d %b")


# ------------------------------------------------------------------ ids

def next_ids(state: dict, day: str, n: int) -> list[str]:
    used = {k for k in state["episodes"] if k.startswith(day)}
    out = []
    for letter in string.ascii_lowercase:
        cand = f"{day}-{letter}"
        if cand not in used:
            out.append(cand)
            used.add(cand)
        if len(out) == n:
            break
    return out


def short(ep_id: str) -> str:
    return ep_id.rsplit("-", 1)[-1].upper()


def find_episode(state: dict, ref: str, cfg: dict) -> str | None:
    """Accept a full id, or a letter like 'b' meaning today's (or most recent day's) episode b."""
    ref = ref.strip().lower()
    if ref in state["episodes"]:
        return ref
    if len(ref) <= 3:
        cands = sorted((k for k in state["episodes"] if k.split("-", 3)[-1] == ref), reverse=True)
        return cands[0] if cands else None
    return None


def log(*a):
    print("[prod-manor]", *a, flush=True)
