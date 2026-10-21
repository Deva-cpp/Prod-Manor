"""The jobs the GitHub workflows run: render, publish and token upkeep."""
from __future__ import annotations

import os
import shutil
import subprocess
from datetime import timedelta
from pathlib import Path


from . import instagram, scheduler, telegram
from .common import MEDIA_OUT, env, fmt_day, fmt_time, load_config, log, now, parse, setting, short
from .schema import full_caption
from .telegram import e


def media_base() -> str:
    base = env("MEDIA_BASE_URL")
    if base:
        return base.rstrip("/") + "/"
    repo = env("GITHUB_REPOSITORY", "owner/repo")
    owner, name = repo.split("/", 1)
    return f"https://{owner.lower()}.github.io/{name}/"


# ------------------------------------------------------------------ render

RENDERED = MEDIA_OUT.parent / "state" / "rendered"


def render_pending(state: dict, limit: int = 5) -> list[str]:
    """Render approved reels. Results go to state/rendered/<id>.json (never db.json), so this job can run
    alongside the tick without git conflicts; the next tick merges them in."""
    import json

    from .render import render_episode

    cfg = load_config()
    MEDIA_OUT.mkdir(exist_ok=True)
    RENDERED.mkdir(parents=True, exist_ok=True)
    prune_media(state)
    os.environ.setdefault("PM_FPS", str(cfg.get("render", {}).get("fps", 30)))
    if not cfg.get("render", {}).get("voice", True):
        os.environ["PM_VOICE"] = "0"
    todo = sorted((k for k, r in state["episodes"].items() if r["status"] == "approved" and not (RENDERED / f"{k}.json").exists()),
                  key=lambda k: state["episodes"][k].get("slot_at") or "z")[:limit]
    done = []
    for k in todo:
        rec = state["episodes"][k]
        try:
            log("rendering", k, rec["episode"]["title"])
            out = render_episode(rec["episode"], MEDIA_OUT)
        except Exception as ex:
            log("render failed", k, repr(ex))
            (RENDERED / f"{k}.json").write_text(json.dumps({"id": k, "error": str(ex)[:500]}))
            continue
        v, c = Path(out["video"]).name, Path(out["cover"]).name
        result = {"id": k, "rendered_at": now(cfg).isoformat(),
                  "media": {"video": v, "cover": c, "video_url": media_base() + v, "cover_url": media_base() + c,
                            "seconds": out["seconds"], "voiced": out["voiced"]}}
        slot = parse(rec.get("slot_at"))
        when = f"{fmt_day(slot, cfg)} at {fmt_time(slot, cfg)}" if slot and slot > now(cfg) else "at the next free slot"
        if rec.get("explore"):
            when += " (testing this slot)"
        cap = f"🎬 <b>{e(rec['episode']['title'])}</b> is ready · {out['seconds']}s\nGoes live {e(when)}."
        result["preview_msg_id"] = telegram.send_video(
            Path(out["video"]), cap,
            [[{"text": "🚀 Post now", "callback_data": f"now:{k}"}, {"text": "⏸ Hold", "callback_data": f"hold:{k}"}]])
        (RENDERED / f"{k}.json").write_text(json.dumps(result, indent=2))
        done.append(k)
    return done


def ingest_renders(state: dict) -> list[str]:
    """Merge render results into the state (run by the tick)."""
    import json

    cfg = load_config()
    got = []
    for f in sorted(RENDERED.glob("*.json")) if RENDERED.exists() else []:
        res = json.loads(f.read_text())
        rec = state["episodes"].get(res.get("id"))
        f.unlink()
        if not rec or rec["status"] != "approved":
            continue
        if res.get("error"):
            rec["render_attempts"] = rec.get("render_attempts", 0) + 1
            if rec["render_attempts"] >= 2:
                rec["status"] = "failed"
                rec["error"] = f"render: {res['error']}"
                telegram.send(f"⚠️ Render failed twice for <b>{e(rec['episode']['title'])}</b>: <code>{e(res['error'][:300])}</code>")
            continue
        rec.update(status="rendered", media=res["media"], rendered_at=res["rendered_at"], preview_msg_id=res.get("preview_msg_id"))
        if not rec.get("slot_at") or parse(rec["slot_at"]) < now(cfg) - timedelta(minutes=30):
            scheduler.assign(state, res["id"], force=True)
        got.append(res["id"])
    return got


def prune_media(state: dict) -> None:
    """Keep the media branch small: only files for reels that aren't published yet (plus 2 days of grace)."""
    cfg = load_config()
    keep = set()
    for k, r in state["episodes"].items():
        m = r.get("media") or {}
        recent = r["status"] != "published" or parse(r.get("published_at")) > now(cfg) - timedelta(days=2)
        if m and recent and r["status"] not in ("rejected", "superseded", "failed"):
            keep.update({m.get("video"), m.get("cover")})
    for f in MEDIA_OUT.glob("*"):
        if f.is_file() and f.suffix in (".mp4", ".jpg") and f.name not in keep:
            f.unlink()
    (MEDIA_OUT / ".nojekyll").touch()
    (MEDIA_OUT / "index.html").write_text("<!doctype html><title>Prod Manor media</title>")


def request_render(state: dict) -> bool:
    """Kick off the render workflow when something is approved and not yet rendered."""
    cfg = load_config()
    pending = [k for k, r in state["episodes"].items() if r["status"] == "approved" and not (RENDERED / f"{k}.json").exists()]
    if not pending:
        return False
    last = parse(state["render"].get("requested_at"))
    if last and now(cfg) - last < timedelta(minutes=25):
        return False
    # The workflow starts render.yml only AFTER this tick's state is committed, so the render job
    # always checks out the approvals it needs (see the last step of tick.yml).
    (MEDIA_OUT.parent / ".render_needed").write_text(",".join(pending))
    state["render"]["requested_at"] = now(cfg).isoformat()
    log("render requested for", pending)
    return True


# ------------------------------------------------------------------ publish

def publish_due(state: dict) -> list[str]:
    cfg = load_config()
    handle = cfg.get("instagram_handle", "")
    done = []
    per_day = int(setting(state, cfg, "reels_per_day") or 3)
    for k in scheduler.due(state):
        rec = state["episodes"][k]
        today_count = sum(1 for r in state["episodes"].values()
                          if r["status"] == "published" and (r.get("published_at") or "")[:10] == now(cfg).date().isoformat())
        if today_count >= per_day and not rec.get("post_now"):
            scheduler.assign(state, k, force=True)  # daily cap reached → move to the next free slot
            continue
        m = rec["media"]
        try:
            res = instagram.publish_reel(full_caption(rec["episode"], handle), m.get("video_url"), m.get("cover_url"),
                                         MEDIA_OUT / m["video"] if (MEDIA_OUT / m["video"]).exists() else None)
        except Exception as ex:
            rec["publish_attempts"] = rec.get("publish_attempts", 0) + 1
            log("publish failed", k, repr(ex))
            if rec["publish_attempts"] >= 3:
                rec["status"] = "failed"
                rec["error"] = f"publish: {ex}"
                telegram.send(f"⚠️ Couldn't publish <b>{e(rec['episode']['title'])}</b> after 3 tries:\n<code>{e(str(ex)[:400])}</code>\n"
                              f"Fix the cause, then send /release {short(k)}.")
            continue
        rec.update(status="published", published_at=now(cfg).isoformat(), ig=res)
        rec.pop("post_now", None)
        telegram.send(f"✅ <b>Live:</b> {e(rec['episode']['title'])}\n{e(res.get('permalink') or '')}")
        done.append(k)
    return done


# ------------------------------------------------------------------ token

def token_upkeep(state: dict) -> str:
    """Refresh the Instagram token weekly. With a GH_PAT secret the new token is saved automatically."""
    cfg = load_config()
    t = state["token"]
    last = parse(t.get("refreshed_at"))
    if last and now(cfg) - last < timedelta(days=6):
        return "fresh"
    try:
        res = instagram.refresh_token()
    except Exception as ex:
        telegram.send(f"⚠️ Instagram token refresh failed: <code>{e(ex)}</code>\nGenerate a new long-lived token and update the IG_ACCESS_TOKEN secret.")
        return "failed"
    if res.get("skipped"):
        t["refreshed_at"] = now(cfg).isoformat()
        return res["skipped"]
    new = res.get("access_token")
    t["refreshed_at"] = now(cfg).isoformat()
    t["expires_at"] = (now(cfg) + timedelta(seconds=int(res.get("expires_in", 5184000)))).isoformat()
    if new and new != env("IG_ACCESS_TOKEN") and env("GH_PAT") and shutil.which("gh"):
        r = subprocess.run(["gh", "secret", "set", "IG_ACCESS_TOKEN", "--repo", env("GITHUB_REPOSITORY"), "--body", new],
                           env={**os.environ, "GH_TOKEN": env("GH_PAT")}, capture_output=True, text=True)
        return "saved new token" if r.returncode == 0 else f"could not save token: {r.stderr[:200]}"
    if new and new != env("IG_ACCESS_TOKEN"):
        telegram.send("🔑 Instagram issued a new access token, but I can't save it without a GH_PAT secret. "
                      "Add GH_PAT (see README) or paste the new token into IG_ACCESS_TOKEN within 60 days.")
    return "refreshed"
