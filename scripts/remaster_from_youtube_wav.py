"""
Download audio from YouTube URL and emit a WAV "streaming-style" master (2026-ish):
  48 kHz, stereo, 16-bit PCM, rumble-cut + EBU R128-ish loudnorm (target -14 LUFS).

Requires: yt-dlp, static-ffmpeg (pip install yt-dlp static-ffmpeg).

Usage:
  python scripts/remaster_from_youtube_wav.py [--url URL] [--out media/out.wav]

You must hold rights to distribute the material you're processing.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def ensure_ffmpeg() -> str:
    import static_ffmpeg  # noqa: PLC0415 — optional heavy import

    static_ffmpeg.add_paths()
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit(
            "ffmpeg not found after static_ffmpeg.add_paths(); "
            "`pip install static-ffmpeg` and retry."
        )
    return exe


def dl_wav(download_dir: Path, url: str) -> Path:
    import yt_dlp  # noqa: PLC0415

    out_tpl = str(download_dir / "source.%(ext)s")
    ydl_opts: dict = {
        "quiet": False,
        "no_warnings": False,
        "format": "bestaudio/best",
        "outtmpl": out_tpl,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            },
        ],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    wavs = list(download_dir.glob("*.wav"))
    if not wavs:
        raise SystemExit("yt-dlp did not produce a .wav — check FFmpeg + URL.")
    return wavs[0]


def ffmpeg_remaster(
    ffmpeg: str,
    src: Path,
    dst: Path,
    *,
    lufs_i: float = -14.0,
    tp: float = -1.5,
    lra: float = 11.0,
) -> None:
    """Stereo, rumble-cut, perceptual-ish clarity bump, limiting via loudnorm."""
    af = (
        "highpass=f=35,"
        "equalizer=f=3200:t=q:w=1:g=1.5,"
        "equalizer=f=11000:t=h:w=4800:g=1,"
        f"loudnorm=I={lufs_i}:TP={tp}:LRA={lra}:linear=true:print_format=summary"
    )
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-i",
        str(src),
        "-af",
        af,
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
    print("running:", " ".join(cmd[:6]), "...")
    r = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    if r.returncode != 0:
        print(r.stderr or r.stdout or "(no ffmpeg output)")
        raise SystemExit(r.returncode)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--url",
        default="https://www.youtube.com/watch?v=a7vzD-bmblw",
        help="YouTube watch URL or video ID",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output WAV path (default: repo media/modern-remaster-a7vz.wav)",
    )
    args = p.parse_args()

    root = Path(__file__).resolve().parent.parent
    dst = (
        Path(args.out)
        if args.out is not None
        else root / "media" / "modern-remaster-a7vz.wav"
    )

    ffmpeg = ensure_ffmpeg()
    with tempfile.TemporaryDirectory(prefix="rwav_") as td:
        tdir = Path(td)
        src = dl_wav(tdir, args.url)
        dst.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_remaster(ffmpeg, src, dst)

    print("written:", dst, f"({dst.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
