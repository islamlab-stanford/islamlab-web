"""Assemble the BioGlyph explainer video: narration, frames, captions, poster.

Pipeline, in order:

  1. narrate.ps1 has already written one WAV per segment plus durations.json.
  2. Each segment's on-screen time is max(spoken + TAIL_PAD, scripted). Timing follows the
     measured speech rather than the script's estimate, because SAPI's pace varies with the
     text and a caption cue that drifts from the voice is worse than a slightly long segment.
  3. Frames are rendered by scenes.render(), one PNG per frame, into a temp directory.
  4. The per-segment WAVs are padded with silence to their final lengths and concatenated, so
     the audio track lines up with the frames by construction instead of by ffmpeg's -shortest.
  5. ffmpeg muxes to H.264 / AAC. The poster is pulled from POSTER_AT seconds.
  6. The WebVTT track is written from the same final timings the frames used.

Run:  python build.py            (from this directory)
"""
from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).parent
ASSETS = HERE.parent / "assets"
FPS = 30
W, H = 1920, 1080
TAIL_PAD = 1.4        # silence after each segment's speech, so lines do not run together
POSTER_AT = 3.0       # seconds; a frame from segment 1 that shows the title card
SAMPLE_RATE = 22050


def load_timeline() -> list[dict]:
    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    # PowerShell's Set-Content -Encoding utf8 prepends a BOM, which json.loads rejects
    measured = {d["n"]: d for d in
                json.loads((HERE / "wav" / "durations.json").read_text(encoding="utf-8-sig"))}

    timeline, clock = [], 0.0
    for seg in script["segments"]:
        n = int(seg["n"])
        spoken = float(measured[n]["seconds"])
        dur = max(spoken + TAIL_PAD, float(seg["seconds"]))
        timeline.append({
            "n": n,
            "start": clock,
            "duration": dur,
            "spoken": spoken,
            "narration": seg["narration"],
            "visual": seg["visual"],
            "wav": HERE / "wav" / f"seg{n:02d}.wav",
        })
        clock += dur
    return timeline


def build_audio(timeline: list[dict], out: Path) -> None:
    """Concatenate the segment WAVs, padding each with silence to its final duration."""
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
        lines += [str(i), f"{stamp(seg['start'])} --> {stamp(seg['start'] + seg['duration'])}",
                  seg["narration"], ""]
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    if not (HERE / "wav" / "durations.json").exists():
        print("run narrate.ps1 first:\n"
              "  powershell -File narrate.ps1 -ScriptJson script.json -OutDir wav", file=sys.stderr)
        return 2

    import scenes  # imported here so a scenes.py syntax error does not hide the message above

    timeline = load_timeline()
    total = sum(s["duration"] for s in timeline)
    print(f"{len(timeline)} segments, {total:.1f}s total ({total/60:.2f} min)")
    for s in timeline:
        print(f"  seg{s['n']:02d}  start {s['start']:6.2f}  dur {s['duration']:5.2f}  "
              f"(spoken {s['spoken']:5.2f})")

    ASSETS.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="bioglyph-video-"))
    try:
        n_frames = 0
        for seg in timeline:
            count = int(round(seg["duration"] * FPS))
            for k in range(count):
                img = scenes.render(seg, k / max(count - 1, 1), (W, H))
                img.save(tmp / f"f{n_frames:06d}.png")
                n_frames += 1
            print(f"  rendered seg{seg['n']:02d}: {count} frames")

        audio = tmp / "narration.wav"
        build_audio(timeline, audio)

        ff = imageio_ffmpeg.get_ffmpeg_exe()
        mp4 = ASSETS / "bioglyph_explainer.mp4"
        subprocess.run([
            ff, "-y", "-loglevel", "error",
            "-framerate", str(FPS), "-i", str(tmp / "f%06d.png"),
            "-i", str(audio),
            "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
            # so browsers can start playing before the whole file arrives
            "-movflags", "+faststart",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            str(mp4),
        ], check=True)

        subprocess.run([
            ff, "-y", "-loglevel", "error", "-ss", str(POSTER_AT), "-i", str(mp4),
            "-frames:v", "1", "-q:v", "3", str(ASSETS / "bioglyph-explainer-poster.jpg"),
        ], check=True)

        write_vtt(timeline, ASSETS / "bioglyph-explainer-captions.vtt")

        size = mp4.stat().st_size
        print(f"\nwrote {mp4.name}  {size/1e6:.2f} MB  {n_frames} frames  {total:.1f}s")
        print(f"      {(ASSETS / 'bioglyph-explainer-poster.jpg').name}")
        print(f"      {(ASSETS / 'bioglyph-explainer-captions.vtt').name}")
        if size > 8e6:
            print("NOTE: over 8 MB. Dynomap's is 2.1 MB; consider raising -crf.")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
