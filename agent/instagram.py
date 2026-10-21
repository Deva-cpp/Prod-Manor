"""Instagram Graph API: publish Reels, read insights, refresh the access token.

Supports both official setups:
  * login: instagram → graph.instagram.com (no Facebook Page needed, Creator or Business account)
  * login: facebook  → graph.facebook.com  (account linked to a Facebook Page; allows resumable uploads)
"""
from __future__ import annotations

import time
from pathlib import Path

import requests

from .common import env, load_config, log


class IGError(RuntimeError):
    pass


def _cfg():
    c = load_config().get("instagram", {})
    login = env("IG_LOGIN") or c.get("login", "instagram")
    ver = env("IG_API_VERSION") or c.get("api_version", "v23.0")
    host = "https://graph.instagram.com" if login == "instagram" else "https://graph.facebook.com"
    return {"login": login, "ver": ver, "base": f"{host}/{ver}", "upload": env("IG_UPLOAD") or c.get("upload", "url"),
            "share_to_feed": c.get("share_to_feed", True)}


def _token():
    return env("IG_ACCESS_TOKEN", required=True)


def _req(method: str, url: str, **kw) -> dict:
    kw.setdefault("timeout", 90)
    for attempt in range(4):
        r = requests.request(method, url, **kw)
        try:
            data = r.json()
        except ValueError:
            data = {"error": {"message": r.text[:300]}}
        if r.status_code < 400 and "error" not in data:
            return data
        err = data.get("error", {})
        transient = r.status_code >= 500 or err.get("is_transient") or err.get("code") in (1, 2, 4, 17, 341)
        if transient and attempt < 3:
            time.sleep(10 * (attempt + 1))
            continue
        raise IGError(f"{err.get('code')}/{err.get('error_subcode')}: {err.get('message') or r.text[:300]}")
    raise IGError("unreachable")


def user_id() -> str:
    uid = env("IG_USER_ID")
    if uid:
        return uid
    c = _cfg()
    data = _req("GET", f"{c['base']}/me", params={"fields": "user_id,id,username", "access_token": _token()})
    return str(data.get("user_id") or data["id"])


def wait_url(url: str, tries: int = 20) -> None:
    """GitHub Pages can take a minute to serve a fresh file — wait until the URL answers 200."""
    for _ in range(tries):
        try:
            r = requests.head(url, timeout=20, allow_redirects=True)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(15)
    raise IGError(f"media URL not reachable yet: {url}")


def publish_reel(caption: str, video_url: str | None, cover_url: str | None, video_path: Path | None = None) -> dict:
    c = _cfg()
    ig = user_id()
    tok = _token()
    params = {"media_type": "REELS", "caption": caption, "share_to_feed": "true" if c["share_to_feed"] else "false", "access_token": tok}
    if cover_url:
        params["cover_url"] = cover_url
    if c["upload"] == "resumable" and video_path:
        params["upload_type"] = "resumable"
        cont = _req("POST", f"{c['base']}/{ig}/media", data=params)
        size = video_path.stat().st_size
        up = requests.post(f"https://rupload.facebook.com/ig-api-upload/{c['ver']}/{cont['id']}",
                           headers={"Authorization": f"OAuth {tok}", "offset": "0", "file_size": str(size)},
                           data=video_path.read_bytes(), timeout=600)
        if up.status_code >= 400:
            raise IGError(f"upload failed: {up.text[:300]}")
    else:
        if not video_url:
            raise IGError("no video_url for url-mode publishing")
        wait_url(video_url)
        if cover_url:
            try:
                wait_url(cover_url, tries=4)
            except IGError:
                params.pop("cover_url", None)
        params["video_url"] = video_url
        cont = _req("POST", f"{c['base']}/{ig}/media", data=params)
    cid = cont["id"]
    # Instagram processes the video asynchronously; poll the container (docs: about once a minute, up to ~5 min)
    status = {}
    for i in range(30):
        status = _req("GET", f"{c['base']}/{cid}", params={"fields": "status_code,status", "access_token": tok})
        code = status.get("status_code")
        if code == "FINISHED":
            break
        if code in ("ERROR", "EXPIRED"):
            raise IGError(f"container {code}: {status.get('status')}")
        time.sleep(10 if i < 6 else 30)
    else:
        raise IGError(f"container never finished: {status}")
    pub = _req("POST", f"{c['base']}/{ig}/media_publish", data={"creation_id": cid, "access_token": tok})
    media_id = pub["id"]
    link = ""
    try:
        link = _req("GET", f"{c['base']}/{media_id}", params={"fields": "permalink", "access_token": tok}).get("permalink", "")
    except IGError as ex:
        log("permalink lookup failed:", ex)
    return {"container_id": cid, "media_id": media_id, "permalink": link}


REEL_METRICS = ["views", "reach", "likes", "comments", "shares", "saved", "total_interactions",
                "ig_reels_avg_watch_time", "ig_reels_video_view_total_time"]


def reel_insights(media_id: str) -> dict:
    c = _cfg()
    tok = _token()
    out: dict = {}

    def read(metrics):
        data = _req("GET", f"{c['base']}/{media_id}/insights", params={"metric": ",".join(metrics), "access_token": tok})
        for row in data.get("data", []):
            vals = row.get("values") or [{}]
            v = vals[0].get("value") if vals else row.get("total_value", {}).get("value")
            if v is None and "total_value" in row:
                v = row["total_value"].get("value")
            out[row["name"]] = v

    try:
        read(REEL_METRICS)
    except IGError:
        for m in REEL_METRICS:  # a metric unsupported in this API version must not hide the others
            try:
                read([m])
            except IGError:
                pass
    return out


def account_snapshot() -> dict:
    c = _cfg()
    tok = _token()
    ig = user_id()
    snap = {}
    try:
        snap.update(_req("GET", f"{c['base']}/{ig}", params={"fields": "followers_count,media_count,username", "access_token": tok}))
    except IGError as ex:
        log("account fields failed:", ex)
    try:  # only available once the account has 100+ followers
        data = _req("GET", f"{c['base']}/{ig}/insights", params={"metric": "online_followers", "period": "lifetime", "access_token": tok})
        vals = (data.get("data") or [{}])[0].get("values") or []
        if vals and isinstance(vals[-1].get("value"), dict):
            snap["online_followers"] = vals[-1]["value"]
    except IGError:
        pass
    return snap


def refresh_token() -> dict:
    """Instagram-login long-lived tokens last 60 days and can be refreshed once they're 24h old."""
    c = _cfg()
    if c["login"] != "instagram":
        return {"skipped": "facebook-login page tokens don't need refreshing"}
    return _req("GET", "https://graph.instagram.com/refresh_access_token",
                params={"grant_type": "ig_refresh_token", "access_token": _token()})
