"""End-to-end simulation of a producer day with fake Telegram, Gemini and Instagram.

Runs on a temporary copy of the repo so real state is never touched:
    python -m unittest tests/test_e2e.py -v
"""
from __future__ import annotations

import copy
import importlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FIX = REPO / "tests" / "fixtures"


class FakeTelegram:
    def __init__(self):
        self.sent, self.updates, self.mid, self.uid, self.videos = [], [], 100, 1, []

    def call(self, method, files=None, **p):
        if method == "getUpdates":
            out = [u for u in self.updates if u["update_id"] >= p.get("offset", 0)]
            return {"ok": True, "result": out}
        if method in ("sendMessage", "sendVideo"):
            self.mid += 1
            self.sent.append({"method": method, "id": self.mid, **{k: v for k, v in p.items() if k != "reply_markup"},
                              "buttons": p.get("reply_markup")})
            return {"ok": True, "result": {"message_id": self.mid}}
        self.sent.append({"method": method, **p})
        return {"ok": True, "result": True}

    def tap(self, data, message_id):
        self.updates.append({"update_id": self.uid, "callback_query": {"id": f"cb{self.uid}", "data": data,
                             "message": {"message_id": message_id, "chat": {"id": 42}}}})
        self.uid += 1

    def say(self, text, reply_to=None, chat=42):
        m = {"message_id": 9000 + self.uid, "chat": {"id": chat}, "text": text}
        if reply_to:
            m["reply_to_message"] = {"message_id": reply_to}
        self.updates.append({"update_id": self.uid, "message": m})
        self.uid += 1

    def texts(self):
        return [s.get("text") or s.get("caption") or "" for s in self.sent if s["method"] in ("sendMessage", "sendVideo")]


class E2E(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pm_e2e_"))
        shutil.copytree(REPO, self.tmp / "repo", ignore=shutil.ignore_patterns(".git", "media", "out", "__pycache__"))
        self.root = self.tmp / "repo"
        (self.root / "state" / "db.json").unlink(missing_ok=True)
        for f in (self.root / "queue" / "pitches").glob("*.json"):
            f.unlink()
        sys.path.insert(0, str(self.root))
        for m in [m for m in sys.modules if m == "agent" or m.startswith("agent.")]:
            del sys.modules[m]
        os.environ.update(TELEGRAM_BOT_TOKEN="x", TELEGRAM_CHAT_ID="42", GEMINI_API_KEY="k", IG_ACCESS_TOKEN="t", IG_USER_ID="1")
        for k in ("GITHUB_TOKEN", "GITHUB_REPOSITORY", "GH_PAT"):
            os.environ.pop(k, None)
        self.A = importlib.import_module("agent.__main__")
        self.tg = FakeTelegram()
        importlib.import_module("agent.telegram")._call = self.tg.call
        batch = json.loads((FIX / "batch.json").read_text())["episodes"]
        pilot = json.loads((FIX / "pilot_null.json").read_text())
        self.gemini_calls = []

        def fake_gemini(system, user, temperature=0.9):
            self.gemini_calls.append(user)
            if "OWNER NOTES" in user:
                ep = copy.deepcopy(batch[1])
                ep["title"] = "Room Zero, Again"
                return {"episodes": [ep]}
            bad = {"title": "broken", "monster": "dracula", "beats": []}
            return {"episodes": [copy.deepcopy(pilot), *copy.deepcopy(batch), bad]}

        importlib.import_module("agent.brains").gemini = fake_gemini
        jobs = importlib.import_module("agent.jobs")
        self.published = []

        def fake_render(ep, out_dir):
            out_dir.mkdir(parents=True, exist_ok=True)
            v, c = out_dir / f"{ep['id']}.mp4", out_dir / f"{ep['id']}.jpg"
            v.write_bytes(b"\0" * 2048)
            c.write_bytes(b"\0" * 512)
            return {"video": str(v), "cover": str(c), "seconds": 26.2, "voiced": True}

        importlib.import_module("agent.render").render_episode = fake_render
        ig = importlib.import_module("agent.instagram")

        def fake_publish(caption, video_url, cover_url, video_path=None):
            self.published.append({"caption": caption, "video_url": video_url})
            return {"container_id": "c1", "media_id": f"m{len(self.published)}", "permalink": f"https://instagram.com/reel/{len(self.published)}"}

        ig.publish_reel = fake_publish
        ig.reel_insights = lambda mid: {"views": 1000 * int(mid[1:]), "reach": 800, "shares": 12, "saved": 30, "comments": 9, "likes": 70, "ig_reels_avg_watch_time": 9000}
        ig.account_snapshot = lambda: {"followers_count": 120}
        ig.refresh_token = lambda: {"access_token": "t", "expires_in": 5184000}
        self.common = importlib.import_module("agent.common")

    def tearDown(self):
        sys.path.remove(str(self.root))
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("PM_NOW", None)

    def run_tick(self, when):
        os.environ["PM_NOW"] = when
        st = self.common.load_state()
        self.A.tick(st)
        self.common.save_state(st)
        return self.common.load_state()

    def card(self, title_part):
        for s in self.tg.sent:
            if s["method"] == "sendMessage" and s.get("buttons") and title_part in (s.get("text") or ""):
                return s
        raise AssertionError(f"no card for {title_part}")

    def test_full_day(self):
        # 06:50 — before pitch time, nothing happens
        st = self.run_tick("2026-10-22T06:50:00+05:30")
        self.assertEqual(st["episodes"], {})
        # 07:05 — Gemini pitches; the invalid episode is filtered out
        st = self.run_tick("2026-10-22T07:05:00+05:30")
        self.assertEqual(len(st["episodes"]), 4)
        self.assertTrue(st["days"]["2026-10-22"]["pitched"])
        self.assertTrue(any("Morning, producer" in t for t in self.tg.texts()))
        self.assertIn("Planned lineup", self.gemini_calls[0])
        # a second tick must not pitch again
        self.run_tick("2026-10-22T07:20:00+05:30")
        self.assertEqual(len(self.gemini_calls), 1)

        null_card, caller_card = self.card("Nobody Checked"), self.card("Inside")
        room_card, leak_card = self.card("Room Zero"), self.card("Listener")
        self.tg.tap(f"ap:{self._id(st, 'Nobody Checked')}", null_card["id"])
        self.tg.tap(f"ap:{self._id(st, 'Inside')}", caller_card["id"])
        self.tg.tap(f"rj:{self._id(st, 'Listener')}", leak_card["id"])
        self.tg.say("make the hook about pagination instead", reply_to=room_card["id"])  # reply-to-rewrite
        self.tg.say("/perday 3")
        self.tg.say("/idea a ghost that haunts JSON.parse")
        self.tg.say("/help", chat=999)  # a stranger: must be ignored
        st = self.run_tick("2026-10-22T07:35:00+05:30")
        approved = [k for k, r in st["episodes"].items() if r["status"] == "approved"]
        self.assertEqual(len(approved), 2)
        self.assertTrue(all(st["episodes"][k]["slot_at"] for k in approved))
        self.assertEqual({st["episodes"][k]["episode"]["series_tag"] for k in approved}, {"EP 01", "EP 02"})
        rejected = [k for k, r in st["episodes"].items() if r["status"] == "rejected"]
        self.assertEqual(len(rejected), 1)
        superseded = [k for k, r in st["episodes"].items() if r["status"] == "superseded"]
        self.assertEqual(len(superseded), 1)
        new = st["episodes"][superseded[0]]["superseded_by"]
        self.assertEqual(st["episodes"][new]["episode"]["title"], "Room Zero, Again")
        self.assertEqual(st["episodes"][new]["notes"], "make the hook about pagination instead")
        self.assertEqual(st["settings"]["reels_per_day"], 3)
        self.assertEqual(st["ideas"][0]["text"], "a ghost that haunts JSON.parse")
        self.assertFalse(any("999" in json.dumps(s) for s in self.tg.sent))
        slots = sorted(st["episodes"][k]["slot_at"] for k in approved)
        from datetime import datetime
        gap = datetime.fromisoformat(slots[1]) - datetime.fromisoformat(slots[0])
        self.assertGreaterEqual(gap.total_seconds(), 120 * 60)

        # render job (normally a separate workflow) → result files → merged by the next tick
        os.environ["PM_NOW"] = "2026-10-22T07:40:00+05:30"
        os.environ["GITHUB_REPOSITORY"] = "dev/prod-manor"
        jobs = importlib.import_module("agent.jobs")
        st = self.common.load_state()
        self.assertEqual(len(jobs.render_pending(st)), 2)
        self.assertTrue(any(s["method"] == "sendVideo" for s in self.tg.sent))
        st = self.run_tick("2026-10-22T07:50:00+05:30")
        self.assertEqual(sorted(r["status"] for r in st["episodes"].values() if r.get("media")), ["rendered", "rendered"])
        url = next(r["media"]["video_url"] for r in st["episodes"].values() if r.get("media"))
        self.assertTrue(url.startswith("https://dev.github.io/prod-manor/"))

        # hold one, then let the slots pass: only the other posts
        held = approved[0]
        preview = next(s for s in self.tg.sent if s["method"] == "sendVideo")
        self.tg.tap(f"hold:{held}", preview["id"])
        st = self.run_tick("2026-10-22T23:59:00+05:30")
        pub = [k for k, r in st["episodes"].items() if r["status"] == "published"]
        self.assertEqual(len(pub), 1)
        self.assertNotIn(held, pub)
        self.assertIn("#", self.published[0]["caption"])
        self.assertTrue(any("✅ <b>Live:</b>" in t for t in self.tg.texts()))
        self.assertTrue(st["days"]["2026-10-22"]["reported"])  # nightly report ran
        self.assertTrue(any("Marketer report" in t for t in self.tg.texts()))

        # 25h later: insights collected and scored; slot learning sees it
        st = self.run_tick("2026-10-24T00:30:00+05:30")
        m = st["episodes"][pub[0]]["metrics"]
        self.assertIn("24h", m)
        self.assertGreater(m["score"], 1000)
        sched = importlib.import_module("agent.scheduler")
        self.assertIn(st["episodes"][pub[0]]["slot_label"], sched.slot_stats(st))

        # release the held reel: it gets a fresh future slot
        self.tg.say(f"/release {held.rsplit('-', 1)[1]}")
        st = self.run_tick("2026-10-24T00:45:00+05:30")
        self.assertNotIn("held", st["episodes"][held])
        self.assertGreater(st["episodes"][held]["slot_at"], "2026-10-24T00:45")

    def test_claude_mode_and_fallback(self):
        self.tg.say("/brain claude")
        st = self.run_tick("2026-10-22T06:00:00+05:30")
        self.assertEqual(st["settings"]["brain"], "claude")
        # 07:05 without Claude's file → wait (no Gemini call)
        st = self.run_tick("2026-10-22T07:05:00+05:30")
        self.assertEqual(self.gemini_calls, [])
        self.assertFalse(st["days"]["2026-10-22"].get("pitched"))
        # Claude pushes its file → ingested on the next tick, credited to claude
        batch = json.loads((FIX / "batch.json").read_text())
        (self.root / "queue" / "pitches" / "2026-10-22.json").write_text(json.dumps({"brain": "claude", **batch}))
        st = self.run_tick("2026-10-22T07:20:00+05:30")
        self.assertEqual(self.gemini_calls, [])
        self.assertEqual({r["brain"] for r in st["episodes"].values()}, {"claude"})
        # next day Claude is late → Gemini fallback after 07:40
        st = self.run_tick("2026-10-23T07:30:00+05:30")
        self.assertFalse(st["days"]["2026-10-23"].get("pitched"))
        st = self.run_tick("2026-10-23T07:45:00+05:30")
        self.assertTrue(st["days"]["2026-10-23"]["pitched"])
        self.assertEqual(len(self.gemini_calls), 1)
        self.assertTrue(any("didn't arrive in time" in t for t in self.tg.texts()))

    def test_delete_renumber_no_repeats_and_reset(self):
        st = self.run_tick("2026-10-22T07:05:00+05:30")
        a, b, c, d = (self._id(st, t) for t in ("Nobody Checked", "Inside", "Room Zero", "Listener"))
        for k in (a, b, c):
            self.tg.tap(f"ap:{k}", self.card(st["episodes"][k]["episode"]["title"])["id"])
        st = self.run_tick("2026-10-22T07:20:00+05:30")
        self.assertEqual([st["episodes"][k]["episode"]["series_tag"] for k in (a, b, c)], ["EP 01", "EP 02", "EP 03"])

        # /delete asks first; confirming frees EP 02 for the next reel and retires the id
        self.tg.say(f"/delete {b.rsplit('-', 1)[1]}")
        self.run_tick("2026-10-22T07:35:00+05:30")
        ask = next(s for s in reversed(self.tg.sent) if s.get("buttons") and "Delete" in (s.get("text") or ""))
        self.tg.tap(f"delok:{b}", ask["id"])
        self.tg.tap(f"ap:{d}", self.card("Listener")["id"])
        st = self.run_tick("2026-10-22T07:50:00+05:30")
        self.assertNotIn(b, st["episodes"])
        self.assertIn(b, st["retired_ids"])
        self.assertEqual(st["episodes"][d]["episode"]["series_tag"], "EP 02")
        self.assertNotIn(b, self.common.next_ids(st, "2026-10-22", 3))

        # the brief lists every taught concept, and a batch that repeats them is thrown away
        self.tg.say("/more 2")
        st = self.run_tick("2026-10-22T08:05:00+05:30")
        self.assertIn("ALREADY TAUGHT", self.gemini_calls[-1])
        self.assertIn("null reference / optional chaining", self.gemini_calls[-1])
        self.assertIn("INTERMEDIATE", self.gemini_calls[-1])
        new = [r["episode"]["title"] for k, r in st["episodes"].items() if k not in (a, c, d)]
        self.assertEqual(new, ["The Call Is Coming From Inside"])  # b was deleted before going live, so it's free again
        self.assertIn("concept already taught (null reference / optional chaining)", "\n".join(self.tg.texts()))

        # reset: everything goes, the published reel's concept stays taught, today's pitch runs again
        st["episodes"][a]["status"] = "published"
        self.common.save_state(st)
        self.tg.say("/reset")
        self.run_tick("2026-10-22T08:20:00+05:30")
        ask = next(s for s in reversed(self.tg.sent) if s.get("buttons") and "start fresh" in (s.get("text") or ""))
        self.tg.tap("reset:keep", ask["id"])
        st = self.run_tick("2026-10-22T08:35:00+05:30")
        self.assertEqual([t["concept"] for t in st["taught"]], ["null reference / optional chaining"])
        self.assertTrue(st["days"]["2026-10-22"]["pitched"])  # re-pitched on the same tick
        titles = {r["episode"]["title"] for r in st["episodes"].values()}
        self.assertNotIn("Nobody Checked On Him", titles)
        self.assertIn("Inside", " ".join(titles))  # freed by the reset, so it can be pitched again
        self.assertFalse(set(st["episodes"]) & {a, b, c, d})

    def test_stages_wake_time_and_news(self):
        os.environ["PM_NOW"] = "2026-10-22T09:00:00+05:30"
        brains, schema = importlib.import_module("agent.brains"), importlib.import_module("agent.schema")
        st = self.common.load_state()
        # stage auto starts with languages; every pitch gets its own random clock, never 3:00 AM
        lineup = brains.plan_lineup(st, 4, "seed")
        self.assertEqual({x["stage"] for x in lineup}, {"languages"})
        self.assertEqual(len({x["monster"] for x in lineup}), 4)
        self.assertNotIn("3:00 AM", [x["wake_time"] for x in lineup])
        # once every language topic is taught, the series moves on to frameworks
        st["taught"] = [{"concept": t["fix"], "topic": t["topic"]} for t in brains.load_topics()["languages"]]
        self.assertEqual(brains.active_stage(st), "frameworks")
        self.assertEqual({x["stage"] for x in brains.plan_lineup(st, 3, "s2")}, {"frameworks"})
        st["settings"]["stage"] = "tools"
        self.assertEqual({x["stage"] for x in brains.plan_lineup(st, 3, "s3")}, {"tools"})
        # the pager shows the episode's wake_time; a missing or 3:00 AM one is replaced by a random time
        pilot = json.loads((FIX / "pilot_null.json").read_text())
        ep, _ = schema.validate(copy.deepcopy(pilot))
        pager = next(b for b in ep["beats"] if b["type"] == "pager")
        self.assertEqual(pager["time"], ep["wake_time"])
        self.assertRegex(pager["time"], schema.CLOCK)
        self.assertNotEqual(pager["time"], "3:00 AM")
        ep, _ = schema.validate({**copy.deepcopy(pilot), "wake_time": "4:17 pm"})
        self.assertEqual(next(b for b in ep["beats"] if b["type"] == "pager")["time"], "4:17 PM")

        # /news: research → one pitch written from the brief, with sources on the card
        brains.research = lambda q: {"brief": "ROOT CAUSE: null pointer in the session handler (test brief)",
                                     "sources": [{"title": "example.com", "url": "https://example.com/a"}], "note": ""}
        self.tg.say("/news OpenAI found two bugs in PHP")
        st = self.run_tick("2026-10-22T06:30:00+05:30")
        self.assertIn("BREAKING NEWS", self.gemini_calls[-1])
        self.assertIn("test brief", self.gemini_calls[-1])
        (k, rec), = st["episodes"].items()
        self.assertEqual(rec["news"]["query"], "OpenAI found two bugs in PHP")
        self.assertIn('📰 <i>Breaking news</i> · sources: <a href="https://example.com/a">', self.card("Nobody Checked")["text"])

    def test_news_research_falls_back_when_search_is_empty(self):
        brains = importlib.import_module("agent.brains")
        calls = []
        empty = {"candidates": [{"content": {"parts": [{"thought": True, "text": "..."}]}, "finishReason": "MAX_TOKENS"}],
                 "usageMetadata": {"thoughtsTokenCount": 7990}}
        ok = {"candidates": [{"content": {"parts": [{"text": "WHAT HAPPENED: PHP memory bugs"}]}}]}
        brains._generate = lambda body: calls.append("tools" in body) or (empty if "tools" in body else ok)
        brains._page_text = lambda url: "Wiz Research uncovered critical vulnerabilities in core PHP"
        res = brains.research("https://www.wiz.io/blog/php2shell-php-rce")
        self.assertEqual(calls, [True, True, False])  # search, search retry, then the article alone
        self.assertEqual(res["brief"], "WHAT HAPPENED: PHP memory bugs")
        self.assertIn("linked article only", res["note"])
        self.assertEqual(res["sources"][0]["url"], "https://www.wiz.io/blog/php2shell-php-rce")
        # no link and no search: the error says why and asks for a link
        with self.assertRaisesRegex(RuntimeError, "finish=MAX_TOKENS.*thinking_tokens=7990.*with a link"):
            brains.research("OpenAI found two bugs in PHP")

    def test_schema_rejects_and_repairs(self):
        schema = importlib.import_module("agent.schema")
        pilot = json.loads((FIX / "pilot_null.json").read_text())
        with self.assertRaises(schema.EpisodeError):
            schema.validate({**pilot, "monster": "vampire"})
        no_fix = copy.deepcopy(pilot)
        no_fix["beats"] = [b for b in no_fix["beats"] if b["type"] != "fix"]
        with self.assertRaises(schema.EpisodeError):
            schema.validate(no_fix)
        same = copy.deepcopy(pilot)
        fix = next(b for b in same["beats"] if b["type"] == "fix")
        fix["after"] = fix["lines"][fix["fix_line"] - 1]
        with self.assertRaises(schema.EpisodeError):
            schema.validate(same)
        messy = copy.deepcopy(pilot)
        messy["beats"] = [b for b in messy["beats"] if b["type"] not in ("pager", "title", "outro")]
        messy["beats"][0]["dur"] = 99
        messy["beats"][0]["actors"].append({"who": "dracula"})
        ep, warns = schema.validate(messy)
        self.assertEqual(ep["beats"][0]["type"], "title")
        self.assertEqual(ep["beats"][-1]["type"], "outro")
        self.assertLessEqual(max(b["dur"] for b in ep["beats"]), 6)
        self.assertTrue(warns)
        # gestures: valid ones survive, unknown ones are dropped
        g = copy.deepcopy(pilot)
        g["beats"][2]["actors"][0]["gestures"].append({"g": "moonwalk", "at": 0.9})
        g["beats"][2]["actors"][1]["gesture"] = "teleport"
        ep, _ = schema.validate(g)
        a0, a1 = ep["beats"][2]["actors"]
        self.assertEqual([x["g"] for x in a0["gestures"]], ["gasp", "point"])
        self.assertNotIn("gesture", a1)

    def _id(self, st, title_part):
        return next(k for k, r in st["episodes"].items() if title_part in r["episode"]["title"])


if __name__ == "__main__":
    unittest.main()
