"""Synthesize the narration with a neural voice, and report each segment's measured duration.

Replaces narrate.ps1. Windows' local SAPI voices (David, Zira, Mark) are all the pre-neural
MSTTS_V110 generation and sound obviously synthetic; the lab's Graph Foundation Model explainer
runs 24 kHz mono AAC, which is the signature of a neural endpoint rather than SAPI's 22.05 kHz.
This uses edge-tts, Microsoft's Edge neural voices, and writes 24 kHz mono WAV to match.

Only the narration text leaves the machine, and that same text ships publicly as the caption
track.

  python narrate.py                 # synthesize all segments
  python narrate.py --samples       # one line in several voices, to choose between them
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg

HERE = Path(__file__).parent
RATE = 24000                     # matches the lab's other explainer
# "Reliable, Authority" reads as documentary rather than salesy, which suits a research explainer.
VOICE = "en-US-ChristopherNeural"
# Neural voices default to a brisk read; the reference track paces at about 95 wpm.
PROSODY_RATE = "-8%"
SAMPLE_VOICES = ["en-US-ChristopherNeural", "en-US-AndrewNeural",
                 "en-US-EricNeural", "en-US-AriaNeural"]


async def _say(text: str, voice: str, mp3: Path) -> None:
    await edge_tts.Communicate(text, voice, rate=PROSODY_RATE).save(str(mp3))


def _to_wav(mp3: Path, wav: Path) -> float:
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                    "-i", str(mp3), "-ac", "1", "-ar", str(RATE), str(wav)], check=True)
    mp3.unlink(missing_ok=True)
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def samples() -> None:
    out = HERE / "voice_samples"
    out.mkdir(exist_ok=True)
    line = ("A frozen open model reading these descriptions answers seventy point six percent of "
            "benchmark questions correctly. Reading the identical measurements as a table it "
            "manages thirty nine point five percent.")
    for v in SAMPLE_VOICES:
        mp3 = out / f"{v}.mp3"
        asyncio.run(_say(line, v, mp3))
        secs = _to_wav(mp3, out / f"{v}.wav")
        print(f"  {v:28s} {secs:5.2f}s   {out / (v + '.wav')}")
    print(f"\nlisten, then set VOICE in {Path(__file__).name} and rerun without --samples")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", action="store_true", help="write one line in several voices")
    ap.add_argument("--voice", default=VOICE)
    args = ap.parse_args()
    if args.samples:
        return samples()

    script = json.loads((HERE / "script.json").read_text(encoding="utf-8"))
    wavdir = HERE / "wav"
    wavdir.mkdir(exist_ok=True)

    report = []
    for seg in script["segments"]:
        n = int(seg["n"])
        wav = wavdir / f"seg{n:02d}.wav"
        mp3 = wavdir / f"seg{n:02d}.mp3"
        asyncio.run(_say(seg["narration"], args.voice, mp3))
        secs = _to_wav(mp3, wav)
        words = len(seg["narration"].split())
        report.append({"n": n, "wav": str(wav), "seconds": round(secs, 3),
                       "scripted": float(seg["seconds"]), "words": words,
                       "wpm": round(words / secs * 60)})
        print(f"seg{n:02d}  {secs:6.2f}s spoken / {seg['seconds']:5.1f}s scripted  "
              f"{words:3d} words  {round(words / secs * 60):3d} wpm")

    over = [r for r in report if r["seconds"] > r["scripted"]]
    if over:
        print("\nspeech longer than the scripted slot; build.py extends these to fit:")
        for r in over:
            print(f"  seg{r['n']:02d}  {r['seconds']:.2f}s > {r['scripted']:.1f}s")

    (wavdir / "durations.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"\nvoice: {args.voice} at {PROSODY_RATE}  |  "
          f"total spoken {sum(r['seconds'] for r in report):.1f}s")


if __name__ == "__main__":
    main()
