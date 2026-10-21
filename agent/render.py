"""Render an episode JSON into a 1080x1920 MP4 reel + cover image.

Pipeline (all free, runs on a GitHub Actions runner):
  1. voice: every dialogue line and narration → WAV, each character re-cast with a horror-comedy voice
     (Piper TTS if installed, else espeak-ng, else silent)
  2. stretch beats so dialogue + narration always fit, and hand the line timings to the stage
  3. Playwright drives renderer/stage.html frame by frame → JPEG pipe → ffmpeg
  4. sound design synthesized with ffmpeg (pager buzz, crash, ding, ring, drone) and mixed with the voices
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RENDERER = ROOT / "renderer"
FPS = int(os.environ.get("PM_FPS", "30"))

# ---------------------------------------------------------------- voice

def _wav_seconds(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    ).stdout.strip()
    try:
        return float(out)
    except ValueError:
        return 0.0


def synth_voice(text: str, out: Path, length: float = 0.92) -> bool:
    """Try Piper (natural voice; CLI flags differ between releases), then espeak-ng. False = no TTS available.
    length > 1 speaks slower, < 1 faster."""
    voice = os.environ.get("PIPER_VOICE", str(ROOT / ".voices" / "en_US-ryan-medium.onnx"))
    good = lambda: out.exists() and out.stat().st_size > 2000
    ls = f"{length:.2f}"
    if Path(voice).exists():
        attempts = []
        if shutil.which("piper"):
            attempts += [
                (["piper", "-m", voice, "-f", str(out), "--length-scale", ls], text),
                (["piper", "--model", voice, "--output_file", str(out), "--length_scale", ls], text),
            ]
        attempts += [
            ([sys.executable, "-m", "piper", "-m", voice, "-f", str(out), "--length-scale", ls, "--", text], None),
            ([sys.executable, "-m", "piper", "-m", voice, "-f", str(out), "--", text], None),
        ]
        for cmd, stdin in attempts:
            try:
                r = subprocess.run(cmd, input=stdin, text=True, capture_output=True, timeout=120)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if r.returncode == 0 and good():
                return True
    for exe in ("espeak-ng", "espeak"):
        if shutil.which(exe):
            r = subprocess.run([exe, "-v", "en-us+m3", "-s", str(int(160 / length)), "-p", "35", "-w", str(out), text],
                               capture_output=True)
            if r.returncode == 0 and good():
                return True
    if shutil.which("say"):  # macOS, for local previews only
        aiff = out.with_suffix(".aiff")
        r = subprocess.run(["say", "-r", str(int(185 / length)), "-o", str(aiff), text], capture_output=True)
        if r.returncode == 0 and aiff.exists():
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff), str(out)], capture_output=True)
            if good():
                return True
    return False


# ---------------------------------------------------------------- horror-comedy voice cast
# One base TTS voice, re-cast per character with ffmpeg filters (free, no extra downloads).
# Each profile: speaking length (Piper length scale), loudness (LUFS) and a filter graph from [0:a] to [v].

def _pitch(k: float) -> str:
    """Shift pitch by k without changing speed."""
    return f"aresample=44100,asetrate={int(44100 * k)},aresample=44100,atempo={1 / k:.4f}"


VOICES = {
    # deep horror-trailer narrator who sounds mildly disappointed in you: dry and close, no echo, so every word is clear
    "narrator": (1.1, -15, f"[0:a]{_pitch(0.84)},highpass=f=60,bass=g=4:f=110,equalizer=f=3000:t=q:w=1.2:g=4,"
                           f"lowpass=f=8000,acompressor=threshold=0.1:ratio=3:attack=5:release=120[v]"),
    # scared young boy: plain and simple, higher, a little quick, just a slight tremble
    "junior": (0.9, -15, f"[0:a]{_pitch(1.28)},vibrato=f=6:d=0.1,highpass=f=150[v]"),
    # shy little ghost: airy whisper with a long hallway echo
    "null": (1.15, -18, f"[0:a]{_pitch(1.32)},highpass=f=380,tremolo=f=5:d=0.35,aecho=0.8:0.85:260|520:0.45|0.28[v]"),
    # rotary phone: telephone line, crunchy, and every word calls itself again
    "caller": (0.95, -16, f"[0:a]{_pitch(1.06)},highpass=f=450,lowpass=f=3000,acrusher=bits=8:mode=log:aa=1:mix=0.35,"
                          f"aecho=0.9:0.7:190|380|570:0.55|0.38|0.22[v]"),
    # identical twins: two voices in eerie not-quite-unison
    "twins": (0.95, -15, f"[0:a]aresample=44100,asplit=2[a][b];[a]{_pitch(1.3)}[a1];[b]{_pitch(0.86)},adelay=40[b1];"
                         f"[a1][b1]amix=inputs=2:normalize=0[v]"),
    # hungry slime: very low, slow and gloopy
    "leak": (1.3, -15, f"[0:a]{_pitch(0.62)},vibrato=f=3.5:d=0.6,lowpass=f=2400,bass=g=3[v]"),
    # too-polite tall neighbour: slow, old-butler warble, small parlour reverb
    "ollie": (1.14, -15, f"[0:a]{_pitch(0.9)},vibrato=f=5:d=0.12,aecho=0.8:0.4:45:0.3[v]"),
}


def speak(text: str, who: str, out: Path) -> bool:
    """Voice one line in character. Falls back to the plain TTS voice if the effects fail."""
    length, lufs, graph = VOICES.get(who, VOICES["narrator"])
    raw = out.with_name(out.stem + "_raw.wav")
    if not synth_voice(text, raw, length):
        return False
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-filter_complex",
                        f"{graph};[v]loudnorm=I={lufs}:TP=-2:LRA=11[o]", "-map", "[o]", "-ac", "1", "-ar", "44100", str(out)],
                       capture_output=True)
    if r.returncode != 0 or not out.exists():
        print(f"  voice fx failed for {who}: {r.stderr.decode()[-200:]}", flush=True)
        shutil.copy(raw, out)
    return True


# ---------------------------------------------------------------- sound design

SFX = {
    # name: (duration, ffmpeg aevalsrc expression)
    "pager": (1.6, "0.55*sgn(sin(2*PI*880*t))*gt(sin(2*PI*5*t),0)*exp(-0.4*t)"),
    "ring": (1.8, "0.35*(sin(2*PI*440*t)+sin(2*PI*480*t))*gt(sin(2*PI*20*t),0)*lt(mod(t,1),0.8)"),
    "crash": (1.2, "0.8*(random(0)*2-1)*exp(-3.5*t)+0.5*sin(2*PI*55*t)*exp(-2*t)"),
    "ding": (1.4, "0.45*sin(2*PI*1318*t)*exp(-3*t)+0.25*sin(2*PI*1976*t)*exp(-4*t)"),
    "whoosh": (0.7, "0.35*(random(0)*2-1)*sin(PI*t/0.7)"),
    "thud": (0.6, "0.8*sin(2*PI*70*t*exp(-2*t))*exp(-6*t)"),
    "creak": (1.2, "0.25*sin(2*PI*(180+60*sin(2*PI*1.3*t))*t)*sin(PI*t/1.2)"),
    "heartbeat": (1.6, "0.7*sin(2*PI*55*t)*(exp(-25*mod(t,0.8))+0.7*exp(-25*mod(t-0.22,0.8))*gt(mod(t,0.8),0.22))"),
    "slurp": (0.9, "0.4*sin(2*PI*(300-200*t)*t)*sin(PI*t/0.9)"),
    "glitch": (0.8, "0.4*sgn(sin(2*PI*(200+800*random(0))*t))*gt(sin(2*PI*14*t),0.2)"),
}
AUTO_SFX = {"pager": ["pager"], "crash": ["crash", "glitch"], "fix": ["ding"], "title": ["whoosh"], "outro": ["creak"]}


def build_audio(ep: dict, beats: list[dict], voice_clips: list[tuple[float, Path]], total: float, work: Path) -> Path:
    inputs, filters, labels = [], [], []
    # low horror drone bed for the whole reel
    drone = f"0.05*sin(2*PI*55*t)+0.035*sin(2*PI*82.4*t)*(0.6+0.4*sin(2*PI*0.2*t))+0.02*sin(2*PI*110.3*t)"
    inputs += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", f"aevalsrc=exprs='{drone}':s=44100"]
    filters.append("[0:a]volume=1.0[bed]")
    labels.append("[bed]")
    n = 1
    for i, b in enumerate(beats):
        names = list(b.get("sfx") or []) + AUTO_SFX.get(b.get("type"), [])
        seen = set()
        for name in names:
            if name in seen or name not in SFX:
                continue
            seen.add(name)
            d, expr = SFX[name]
            inputs += ["-f", "lavfi", "-t", str(d), "-i", f"aevalsrc=exprs='{expr}':s=44100"]
            ms = int(b["_t0"] * 1000)
            filters.append(f"[{n}:a]adelay={ms}|{ms},volume=0.9[s{n}]")
            labels.append(f"[s{n}]")
            n += 1
    for t, wav in voice_clips:
        inputs += ["-i", str(wav)]
        ms = int(t * 1000)
        filters.append(f"[{n}:a]aresample=44100,pan=mono|c0=c0,adelay={ms}|{ms}[v{n}]")
        labels.append(f"[v{n}]")
        n += 1
    mix = "".join(labels) + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.9,atrim=0:{total:.2f}[aout]"
    filters.append(mix)
    out = work / "audio.m4a"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[aout]", "-ac", "2", "-c:a", "aac", "-b:a", "160k", str(out)]
    subprocess.run(cmd, check=True)
    return out


# ---------------------------------------------------------------- frames

async def _capture_chunk(browser, ep: dict, f0: int, f1: int, seg: Path) -> None:
    page = await browser.new_page(viewport={"width": 1080, "height": 1920})
    await page.goto((RENDERER / "stage.html").as_uri())
    await page.evaluate("document.fonts.ready")
    await page.evaluate("(ep) => window.PMR.load(ep)", ep)
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS), str(seg)],
        stdin=subprocess.PIPE,
    )
    stage = page.locator("#stage")
    for f in range(f0, f1):
        await page.evaluate("(t) => window.PMR.seek(t)", f / FPS)
        ff.stdin.write(await stage.screenshot(type="jpeg", quality=93))
        if (f - f0) % 200 == 0:
            print(f"  frames {f}/{f1}", flush=True)
    ff.stdin.close()
    await asyncio.get_running_loop().run_in_executor(None, ff.wait)
    await page.close()


async def capture(ep: dict, video_out: Path, cover_out: Path) -> float:
    """Render frames in parallel pages (one contiguous chunk each), then join the chunks losslessly."""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        exe = os.environ.get("PM_CHROMIUM")
        browser = await p.chromium.launch(executable_path=exe) if exe else await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1080, "height": 1920})
        await page.goto((RENDERER / "stage.html").as_uri())
        await page.evaluate("document.fonts.ready")
        info = await page.evaluate("(ep) => window.PMR.load(ep)", ep)
        total = info["total"]
        frames = int(round(total * FPS))
        workers = max(1, min(int(os.environ.get("PM_WORKERS", os.cpu_count() or 2)), 6))
        step = -(-frames // workers)
        segs = [video_out.with_name(f"seg{i}.mp4") for i in range(workers)]
        await asyncio.gather(*[
            _capture_chunk(browser, ep, i * step, min(frames, (i + 1) * step), segs[i])
            for i in range(workers) if i * step < frames
        ])
        lst = video_out.with_name("segs.txt")
        lst.write_text("".join(f"file '{s}'\n" for i, s in enumerate(segs) if i * step < frames))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-c", "copy", str(video_out)], check=True)
        # cover: the title beat at its strongest moment (or 1.6s in)
        cover_t = next((c["t0"] + min(1.8, c["d"] * 0.7) for c in info["beats"] if c["type"] == "title"), 1.6)
        await page.evaluate("(t) => window.PMR.seek(t)", cover_t)
        await page.locator("#stage").screenshot(path=str(cover_out), type="jpeg", quality=92)
        await browser.close()
        return total


def render_episode(ep: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="pm_"))
    beats = ep["beats"]
    use_voice = os.environ.get("PM_VOICE", "1") != "0"
    # every line gets a voice: dialogue first (in character, one after another), then the narrator.
    # Timings go to the stage as _say_t / _narr_t so bubbles, lip flap and captions follow the audio.
    clips: list[tuple[int, float, Path]] = []  # (beat index, offset in beat, wav)
    for i, b in enumerate(beats):
        if not use_voice:
            break
        cur, voiced = 0.15, False
        says = [s for s in (b.get("say") or []) if s.get("text")]
        say_t = []
        for j, s in enumerate(says):
            wav = work / f"s{i}_{j}.wav"
            if speak(s["text"], s["who"], wav):
                d, voiced = _wav_seconds(wav), True
                clips.append((i, cur, wav))
            else:
                d = 0.6 + 0.06 * len(s["text"])
            say_t.append([round(cur, 3), round(d, 3)])
            cur += d + 0.25
        text = (b.get("narration") or "").strip()
        if text:
            wav = work / f"n{i}.wav"
            if speak(text, "narrator", wav):
                d, voiced = _wav_seconds(wav), True
                clips.append((i, cur, wav))
                b["_narr_t"] = [round(cur, 3), round(d, 3)]
                cur += d + 0.15
        if voiced:
            if says:
                b["_say_t"] = say_t
            b["dur"] = max(float(b.get("dur", 3)), cur + 0.4)
    t = 0.0
    for b in beats:
        b["dur"] = max(0.8, float(b.get("dur", 3)))
        b["_t0"] = t
        t += b["dur"]
    voice_clips = [(beats[i]["_t0"] + off, wav) for i, off, wav in clips]
    video_silent = work / "video.mp4"
    cover = out_dir / f"{ep['id']}.jpg"
    total = asyncio.run(capture(ep, video_silent, cover))
    audio = build_audio(ep, beats, voice_clips, total, work)
    final = out_dir / f"{ep['id']}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_silent), "-i", str(audio),
                    "-c:v", "copy", "-c:a", "copy", "-shortest", "-movflags", "+faststart", str(final)], check=True)
    for b in beats:
        for k in ("_t0", "_say_t", "_narr_t"):
            b.pop(k, None)
    shutil.rmtree(work, ignore_errors=True)
    return {"video": str(final), "cover": str(cover), "seconds": round(total, 2), "voiced": bool(voice_clips)}


if __name__ == "__main__":
    src = Path(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out"
    data = json.loads(src.read_text())
    eps = data if isinstance(data, list) else data.get("episodes", [data])
    for e in eps:
        print(json.dumps(render_episode(e, out)))
