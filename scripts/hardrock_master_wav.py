"""
Hard-rock / guitar-heavy remaster preset (FFmpeg) from an existing WAV.
Targets: fuller low guitar body, scooped mids, aggressive upper-mid bite,
light saturation, slam compression, stereo width, limiting + loudnorm.

Requires: pip install static-ffmpeg

  python scripts/hardrock_master_wav.py
  python scripts/hardrock_master_wav.py --input media/other.wav --out media/out.wav

You must own rights to distribute the rendered output.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def ensure_ffmpeg() -> str:
    import static_ffmpeg  # noqa: PLC0415

    static_ffmpeg.add_paths()
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("ffmpeg missing; run `pip install static-ffmpeg`")
    return exe


def hardrock_af() -> str:
    """Single-line ffmpeg -af chain."""
    return (
        "highpass=f=45,"
        "equalizer=f=125:t=q:w=0.72:g=3.8,"
        "equalizer=f=240:t=q:w=0.9:g=1.9,"
        "equalizer=f=480:t=q:w=0.88:g=-2.6,"
        "equalizer=f=900:t=q:w=0.8:g=-1.9,"
        "equalizer=f=3000:t=q:w=1.12:g=5.8,"
        "equalizer=f=5200:t=q:w=1.45:g=3.9,"
        "equalizer=f=12600:t=h:w=6200:g=-5.5,"
        "extrastereo=m=10,"
        "acompressor=threshold=-20dB:ratio=5.5:attack=12:release=220:mix=0.93,"
        "acompressor=threshold=-34dB:ratio=3:attack=110:release=420:mix=0.35,"
        "acrusher=mode=log:bits=14:mix=0.18,"
        "alimiter=level_in=1:limit=0.93:attack=5:release=55,"
        "loudnorm=I=-12.8:TP=-1.05:LRA=8:linear=true:print_format=summary"
    )


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", type=Path, default=root / "media" / "modern-remaster-a7vz.wav")
    ap.add_argument("-o", "--out", type=Path, default=root / "media" / "modern-hardrock-a7vz.wav")
    args = ap.parse_args()

    src = args.input
    dst = args.out
    if not src.is_file():
        raise SystemExit(f"missing source wav: {src}")

    ffmpeg = ensure_ffmpeg()
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        str(src),
        "-af",
        hardrock_af(),
        "-ar",
        "48000",
        "-ac",
        "2",
        "-sample_fmt",
        "s16",
        "-c:a",
        "pcm_s16le",
        str(dst),
    ]
    print("ffmpeg ->", dst.name)
    r = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout)
        raise SystemExit(r.returncode)
    print("written:", dst, f"({dst.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
