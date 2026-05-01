"""
Procedural chiptune: square arp + faint bass loop.
Regenerate: python scripts/make_ratuba_chiptune_wav.py
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

SR = 22050
MASTER = 0.24


def clamp_i16(x: float) -> int:
    v = int(x * 32767.0)
    return max(-32768, min(32767, v))


def sq(sin_phase: float) -> float:
    return 1.0 if sin_phase >= 0.0 else -1.0


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    out = root / "media" / "ratuba-chiptune.wav"

    melody_hz = [
        523.25,
        659.26,
        783.99,
        1046.5,
        783.99,
        659.26,
        587.33,
        392.00,
        329.63,
        261.63,
    ]
    bass_hz = 130.81
    note_s = 0.085
    note_n = max(1, int(note_s * SR))

    laps = 18
    samp: list[float] = []
    phi_m = 0.0
    phi_b = 0.0
    two_pi = 2.0 * math.pi

    for _ in range(laps):
        for f in melody_hz:
            dw_m = two_pi * f / SR
            dw_b = two_pi * bass_hz / SR
            for i in range(note_n):
                phi_m = math.fmod(phi_m + dw_m, two_pi)
                phi_b = math.fmod(phi_b + dw_b, two_pi)
                sm = math.sin(phi_m)
                env = math.exp(-2.8 * i / note_n)
                melody = sq(sm) * 0.72
                bass = sq(math.sin(phi_b)) * 0.28
                samp.append(MASTER * env * (melody + bass))

    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        for x in samp:
            w.writeframes(struct.pack("<h", clamp_i16(x)))


if __name__ == "__main__":
    main()
