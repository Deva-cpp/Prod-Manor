# Prod Manor — the zero-cost reels producer

An autonomous producer and marketer for your programming-horror Reels. Every morning it pitches storylines to you on Telegram. You approve, rewrite or reject each one. Approved stories are rendered into finished 9:16 reels with your Claude Design characters. Each reel is posted to Instagram at its best time slot, and the agent learns from the results to make the next pitches better.

```
07:00  🧠 brain writes 4 storylines ──► 📱 Telegram: ✅ Approve · ✏️ Rewrite · ❌ Reject
           (Gemini free tier, or a Claude scheduled task)
        approve ──► 🎞 render (your characters, code panels, captions, SFX, voice) ──► 📱 preview + ⏸ Hold / 🚀 Post now
        slot time ──► 📤 Instagram Reel ──► 📱 "✅ Live" + link
24h/72h/7d ──► 📊 insights ──► learnings feed tomorrow's pitches and slot choices
23:30  🌙 marketer report in Telegram
```

## What it costs: ₹0

| Piece | Free tool | Notes |
|---|---|---|
| Runner + scheduler | GitHub Actions | Free for **public** repos. A private repo gets 2,000 min/month (see "Private repo" below) |
| Brain | Gemini API free tier (Flash models) | Or a Claude scheduled task on your existing Claude plan |
| Approvals | Telegram bot | Free |
| Rendering | Playwright + Chromium + ffmpeg | Your characters from `renderer/pm-characters.js` |
| Voice | Piper TTS (open source), espeak-ng fallback | Downloaded on the runner. Every narration and dialogue line is voiced; ffmpeg re-casts each character with a horror-comedy voice (`VOICES` in `agent/render.py`) |
| Hosting for Instagram to fetch | GitHub Pages | Only unpublished reels are kept |
| Posting + analytics | Official Instagram API | 50 API posts per 24h, far above 3–5/day |

One honest trade-off: on Gemini's free tier, Google may use your prompts to improve its models. That's fine for storylines, but don't put secrets in `/idea` notes.

## Setup (about 30 minutes, once)

### 1. Instagram
1. Switch your Instagram account to **Professional → Creator** (Settings → Account type and tools).
2. Go to [developers.facebook.com](https://developers.facebook.com) → **Create app** → use case **"Manage messaging & content on Instagram"**.
3. In the app, open **Instagram → API setup with Instagram login**. Add your Instagram account and **Generate token**. Grant `instagram_business_basic`, `instagram_business_content_publish` and `instagram_business_manage_insights`.
4. Copy the long-lived token (valid 60 days; the agent refreshes it weekly). Leave the app in development mode. Posting to your own account doesn't need app review.

### 2. Telegram bot
1. In Telegram, message **@BotFather** → `/newbot` → copy the **bot token**.
2. Open your new bot and press **Start** (you'll get your chat id after step 4).

### 3. Gemini key
[aistudio.google.com](https://aistudio.google.com) → **Get API key** → create a key. No billing needed.

### 4. GitHub
1. Create a **public** repository and push this folder to `main`.
2. **Settings → Secrets and variables → Actions → Secrets**:
   | Secret | Value |
   |---|---|
   | `TELEGRAM_BOT_TOKEN` | from BotFather |
   | `TELEGRAM_CHAT_ID` | leave empty for now |
   | `GEMINI_API_KEY` | from AI Studio |
   | `IG_ACCESS_TOKEN` | from step 1 |
   | `GH_PAT` *(optional)* | fine-grained token for this repo with **Secrets: read & write**, so refreshed Instagram tokens save themselves |
3. **Settings → Pages → Build and deployment → Source: GitHub Actions.**
4. **Settings → Actions → General → Workflow permissions: Read and write.**
5. **Actions → tick → Run workflow.** Then send `/start` to your bot and run tick again. The bot replies with your chat id. Save it as `TELEGRAM_CHAT_ID`.
6. **Actions → tick → Run workflow** once more, then send `/help` to the bot. If it answers, you're live.

Tomorrow at 07:00 IST the first pitches arrive. Want some now? Send `/more 2`.

### 5. Tune it (`config.yaml`)
- `instagram_handle`: your handle, used in captions.
- `slots`: candidate posting times. The marketer favors the winners and keeps testing the rest (`explore_rate`).
- `reels_per_day` (3–5) and `pitches_per_day`. You can also change these from Telegram.
- `pitch_time`, `report_time`, `timezone`.

## Telegram commands
| Command | What it does |
|---|---|
| tap ✅ / ✏️ / ❌ | approve, rewrite with notes, reject a pitch (or just *reply* to a pitch with notes) |
| `/status` | today's pipeline |
| `/brain gemini` · `/brain claude` | switch the writer |
| `/perday 4` | reels per day (1–5) |
| `/more 2` | pitch more storylines now |
| `/idea a ghost that haunts JSON.parse` | feed an idea into the next batch |
| `/postnow B` · `/hold B` · `/release B` | control a single reel |
| `/pause` · `/resume` | stop or restart everything |
| `/report` | marketer report now |

## Two brains

**Gemini (default, fully automatic).** The tick calls the Gemini free tier at `pitch_time`. Nothing else to set up.

**Claude (when you want stronger writing).** Create a Claude scheduled task that runs daily at ~06:40 IST with this repo attached and push access. Its instructions are in [`CLAUDE_TASK.md`](CLAUDE_TASK.md). Then send `/brain claude`. Claude reads the exact same brief Gemini gets (`python -m agent brief`), writes `queue/pitches/<date>.json`, validates it and pushes. Your pitches arrive in Telegram within a minute. If Claude's pitches haven't arrived by `claude_fallback_after` (07:40), Gemini writes the batch so you never miss a day. Rewrites use Gemini in both modes because they're instant. If no Gemini key is set, they're queued for Claude's next run.

## How the "producer + marketer" works
- **Producer** (`bible/SERIES_BIBLE.md`, `bible/topics.yaml`): rotates monsters and avoids repeating topics from the last 30 days. It varies hook styles within a batch and enforces the beat sheet: 2-second hook → title → encounter → real buggy code → consequence → one-line fix → lesson and next-monster tease. Every script passes `agent/schema.py` before you ever see it.
- **Marketer** (`agent/marketer.py`, `agent/scheduler.py`): pulls views, reach, shares, saves, comments and watch time at 24h, 72h and 7d. Each reel is scored as views + 8×shares + 6×saves + 3×comments + likes, boosted by watch time. Scores are aggregated by monster, level, language and slot, and written to `state/learnings.md`, which goes into every brief. Slots are chosen best-first, with a share reserved for testing under-sampled slots. After 100 followers, Instagram's "followers online" data also weighs in.

## Look & animation
- Your approved designs live in `design/`: the style guide and cast lineup from Claude Design. Open them in a browser.
- `bible/STYLE_GUIDE.md` is the text version of the style guide, plus the animation rules.
- Characters are rigged without being redrawn. Arms pivot at the shoulder, with props attached (Junior's flashlight beam follows his arm). Heads tilt, eyes dart and look at whoever's talking, brows lift, and mouths lip-sync while a speech bubble types out.
- Scripts can direct 19 gestures per actor (wave, point, shrug, facepalm, celebrate, cower, dance, laugh…) and sequence them within a beat. The brain is instructed to give every scene a performance.

## Adding your own content
- **New topics:** add lines to `bible/topics.yaml`.
- **Tone or rules:** edit `bible/SERIES_BIBLE.md`.
- **Render a script locally:** `pip install -r requirements.txt && python -m playwright install chromium`, then `python agent/render.py tests/fixtures/pilot_null.json out/`.

## Private repo?
It works, but minutes are capped. Change the tick cron to `*/30 * * * *`, which gives roughly 1,500 min/month plus about 5 min per render. GitHub Pages on a private repo needs a paid plan, so set the repo variable `IG_LOGIN=facebook` and `IG_UPLOAD=resumable`. Your Instagram account must then be linked to a Facebook Page, and you need a Page token in `IG_ACCESS_TOKEN`.

## Instagram API limits to know
- Reels posted through the API can't use songs from Instagram's music library. The reels ship with their own sound design and voice instead.
- 50 API-published posts per rolling 24 hours.
- Long-lived tokens last 60 days. The weekly refresh keeps them alive. Without `GH_PAT`, the bot reminds you to paste the new one.
