"""Assemble the Jeus explainer video: narration, frames, captions, poster.

The same pipeline as bioglyph/video/build.py:

  1. narrate.py has written one WAV per segment plus durations.json.
  2. Each segment's on-screen time is max(spoken + TAIL_PAD, scripted), so a caption cue never
     drifts from the voice.
  3. scenes.render() draws one PNG per frame into a temp directory.
  4. The per-segment WAVs are padded with silence to their final lengths and concatenated, so the
     audio lines up with the frames by construction.
  5. ffmpeg muxes to H.264 / AAC; the poster is pulled from POSTER_AT seconds.
  6. The WebVTT track is written from the same final timings the frames used, with each
     segment's written caption (digits and symbols) in place of the spoken form.

Run:  python build.py            (from this directory)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).parent
ASSETS = HERE.parent / "assets"
FPS = 30
W, H = 1280, 720
TAIL_PAD = 1.4
POSTER_AT = 15.0  # the end of the first scene: every file and step shown, nothing half typed
SAMPLE_RATE = 24000
NAME = "jeus_explainer"
POSTER = "jeus-explainer-poster.jpg"
CAPTIONS = "jeus-explainer-captions.vtt"


def load_timeline() -> list[dict]:
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    measured = {d["n"]: d for d in json.loads((HERE / "wav" / "durations.json").read_text(encoding="utf-8-sig"))}
    timeline, clock = [], 0.0
    for seg in script["segments"]:
        n = int(seg["n"])
        spoken = float(measured[n]["seconds"])
        dur = max(spoken + TAIL_PAD, float(seg["seconds"]))
        timeline.append({"n": n, "start": clock, "duration": dur, "spoken": spoken,
                         "narration": seg["narration"], "caption": seg.get("caption") or seg["narration"],
                         "visual": seg["visual"],
                         "wav": HERE / "wav" / f"seg{n:02d}.wav"})
        clock += dur
    return timeline


def build_audio(timeline: list[dict], out: Path) -> None:
    frames = bytearray()
    for seg in timeline:
        with wave.open(str(seg["wav"])) as w:
            assert w.getframerate() == SAMPLE_RATE, f"{seg['wav']} is {w.getframerate()} Hz"
            assert w.getnchannels() == 1 and w.getsampwidth() == 2
            frames += w.readframes(w.getnframes())
        pad = int(round((seg["duration"] - seg["spoken"]) * SAMPLE_RATE))
        if pad > 0:
            frames += b"\x00\x00" * pad
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(bytes(frames))


def write_vtt(timeline: list[dict], out: Path) -> None:
    def stamp(t: float) -> str:
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"

    lines = ["WEBVTT", ""]
    for i, seg in enumerate(timeline, 1):
        lines += [str(i), f"{stamp(seg['start'])} --> {stamp(seg['start'] + seg['duration'])}", seg["caption"], ""]
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not (HERE / "wav" / "durations.json").exists():
        print("run narrate.py first", file=sys.stderr)
        return 2
    import scenes  # imported here so a scenes.py error does not hide the message above

    timeline = load_timeline()
    total = sum(s["duration"] for s in timeline)
    print(f"{len(timeline)} segments, {total:.1f}s total ({total/60:.2f} min)")
    for s in timeline:
        print(f"  seg{s['n']:02d}  start {s['start']:6.2f}  dur {s['duration']:5.2f}  (spoken {s['spoken']:5.2f})")

    ASSETS.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="jeus-video-"))
    try:
        n_frames = 0
        for seg in timeline:
            count = int(round(seg["duration"] * FPS))
            for k in range(count):
                scenes.render(seg, k / max(count - 1, 1), (W, H)).save(tmp / f"f{n_frames:06d}.png")
                n_frames += 1
            print(f"  rendered seg{seg['n']:02d}: {count} frames")

        audio = tmp / "narration.wav"
        build_audio(timeline, audio)
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        mp4 = ASSETS / f"{NAME}.mp4"
        subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%06d.png"),
                        "-i", str(audio), "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", "-c:a", "aac", "-b:a", "96k", "-ar", "24000", str(mp4)], check=True)
        subprocess.run([ff, "-y", "-loglevel", "error", "-ss", str(POSTER_AT), "-i", str(mp4), "-frames:v", "1",
                        "-q:v", "3", str(ASSETS / POSTER)], check=True)
        write_vtt(timeline, ASSETS / CAPTIONS)
        size = mp4.stat().st_size
        print(f"\nwrote {mp4.name}  {size/1e6:.2f} MB  {n_frames} frames  {total:.1f}s")
        print(f"      {POSTER}\n      {CAPTIONS}")
        if size > 8e6:
            print("NOTE: over 8 MB; consider raising -crf.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
