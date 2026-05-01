"""
Original NES-style chiptune (Mega Man–era *feel*, not a cover of copyrighted themes).
Square bass + doubled harmony + lead. Regenerate WAV:

  cd ratubaworld-pages
  python scripts/make_ratuba_chiptune_wav.py
"""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

# Slightly richer than DMG-only; keeps file modest vs 44100 stereo.
SR = 32000
BPM = 168.0

# Layers for gain staging (mix headroom applied after).
LAY = {"bass": 0.42, "harm": 0.22, "lead": 0.34}


def clamp_i16(x: float) -> int:
    v = int(x * 32767.0)
    return max(-32768, min(32767, v))


def midi_to_hz(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


def beats_to_samples(beats: float) -> int:
    return int(beats * (60.0 / BPM) * SR)


def env_staccato(i: int, n: int) -> float:
    """Short punchy NES note body + tiny tail."""
    if n <= 0:
        return 0.0
    a = max(1, min(80, n // 24))
    k = int(n * 0.88)
    if i < a:
        return i / a
    if i >= k:
        t = (n - i) / max(1, n - k)
        return max(0.0, t * t)
    return 1.0


def env_pad(i: int, n: int) -> float:
    """Softer harmonic bed."""
    if n <= 0:
        return 0.0
    a = max(1, min(200, n // 12))
    r = max(1, min(400, n // 6))
    if i < a:
        return i / a
    if i >= n - r:
        return max(0.0, (n - i) / r)
    return 1.0


def add_square(
    buf: list[float],
    start_s: int,
    dur_s: int,
    hz: float,
    gain: float,
    env_fn,
) -> None:
    phi = 0.0
    twopi = math.tau
    dw = twopi * hz / SR
    lim = min(len(buf), start_s + dur_s)
    for k, j in enumerate(range(start_s, lim)):
        phi = math.fmod(phi + dw, twopi)
        sm = math.sin(phi)
        sqv = 1.0 if sm >= 0.0 else -1.0
        e = env_fn(k, dur_s)
        buf[j] += gain * e * sqv


def normalize_peak(buf: list[float], peak: float = 0.92) -> None:
    m = 0.0
    for x in buf:
        ax = abs(x)
        if ax > m:
            m = ax
    if not m:
        return
    if m > peak:
        s = peak / m
        for i in range(len(buf)):
            buf[i] *= s


def fade_edges(buf: list[float], fade_in: int, fade_out: int) -> None:
    n = len(buf)
    for i in range(min(fade_in, n)):
        buf[i] *= i / max(1, fade_in)
    for i in range(max(0, n - fade_out), n):
        buf[i] *= (n - 1 - i) / max(1, fade_out)


def build_song() -> list[float]:
    total_beats = 112.0  # 28 bars (heroic “title” arc, then natural stop)
    total_s = beats_to_samples(total_beats) + SR // 4
    buf = [0.0] * total_s

    notes_bass: list[tuple[float, float, float, float]] = []
    notes_harm: list[tuple[float, float, float, float]] = []
    notes_lead: list[tuple[float, float, float, float]] = []

    # --- Intro: driving D power / A swap (bars 0–3) ---
    for bar in range(4):
        b0 = bar * 4.0
        for off, m in [
            (0.0, 38),
            (0.5, 38),
            (1.0, 45),
            (1.5, 45),
            (2.0, 38),
            (2.5, 38),
            (3.0, 45),
            (3.5, 45),
        ]:
            notes_bass.append((b0 + off, 0.45, float(m), LAY["bass"]))

    # --- Bars 4–7: walking pull into theme ---
    walk = [
        (16.0, 38, 0.5),
        (16.5, 45, 0.5),
        (17.0, 43, 0.5),
        (17.5, 41, 0.5),
        (18.0, 40, 0.5),
        (18.5, 38, 0.5),
        (19.0, 41, 0.5),
        (19.5, 43, 0.5),
        (20.0, 45, 0.5),
        (20.5, 43, 0.5),
        (21.0, 41, 0.5),
        (21.5, 40, 0.5),
        (22.0, 38, 0.5),
        (22.5, 40, 0.5),
        (23.0, 41, 0.5),
        (23.5, 43, 0.5),
    ]
    for b, m, d in walk:
        notes_bass.append((b, d, float(m), LAY["bass"] * 1.05))

    # --- Bars 8–15: syncopated rock bass under hook ---
    for bar in range(8, 16):
        b0 = bar * 4.0
        pat = [
            (0.0, 38, 0.75),
            (1.0, 38, 0.5),
            (1.75, 45, 0.5),
            (2.5, 43, 0.5),
            (3.25, 41, 0.75),
        ]
        for off, m, d in pat:
            notes_bass.append((b0 + off, d, float(m), LAY["bass"] * 1.08))

    # --- Bars 16–23: broader roots (chorus feel) ---
    for bar in range(16, 24):
        b0 = bar * 4.0
        roots = (38, 45, 41, 45) if bar % 2 == 0 else (38, 43, 40, 45)
        for i, m in enumerate(roots):
            notes_bass.append((b0 + float(i), 0.92, float(m), LAY["bass"] * 1.05))

    # --- Bars 24–27: cadence ---
    finale_bass = [
        (96.0, 38, 1.0),
        (97.0, 45, 1.0),
        (98.0, 43, 1.0),
        (99.0, 41, 1.0),
        (100.0, 38, 1.0),
        (101.0, 45, 0.5),
        (101.5, 43, 0.5),
        (102.0, 41, 0.5),
        (102.5, 40, 0.5),
        (103.0, 38, 2.75),
        (105.75, 38, 0.25),
    ]
    for b, m, d in finale_bass:
        notes_bass.append((b, d, float(m), LAY["bass"] * 1.1))

    # --- Pickup stab (bar 3) ---
    notes_lead.extend(
        [
            (10.5, 0.25, 69.0, LAY["lead"] * 0.55),
            (11.5, 0.25, 74.0, LAY["lead"] * 0.6),
        ]
    )

    # --- Theme A + answer (bars 4–15): original melodic arc in D minor ---
    theme_a: list[tuple[float, float, float, float]] = [
        (16.0, 0.5, 74.0, 0.95),
        (16.5, 0.5, 77.0, 0.95),
        (17.0, 1.0, 81.0, 0.98),
        (18.0, 0.5, 79.0, 0.92),
        (18.5, 0.5, 77.0, 0.92),
        (19.0, 1.0, 76.0, 0.93),
        (20.0, 0.5, 74.0, 0.94),
        (20.5, 0.5, 72.0, 0.9),
        (21.0, 1.0, 70.0, 0.94),
        (22.0, 0.5, 69.0, 0.9),
        (22.5, 0.5, 70.0, 0.9),
        (23.0, 1.0, 72.0, 0.95),
        (24.0, 0.5, 74.0, 0.96),
        (24.5, 0.5, 77.0, 0.96),
        (25.0, 0.5, 81.0, 0.98),
        (25.5, 0.5, 86.0, 1.0),
        (26.0, 1.0, 84.0, 0.97),
        (27.0, 1.0, 82.0, 0.96),
        (28.0, 0.5, 81.0, 0.96),
        (28.5, 0.5, 79.0, 0.94),
        (29.0, 1.0, 77.0, 0.95),
        (30.0, 0.5, 76.0, 0.92),
        (30.5, 0.5, 74.0, 0.93),
        (31.0, 1.0, 69.0, 0.92),
        # answer / lift
        (32.0, 0.5, 74.0, 0.96),
        (32.5, 0.5, 77.0, 0.96),
        (33.0, 1.25, 81.0, 1.0),
        (34.5, 0.5, 79.0, 0.93),
        (35.0, 0.5, 81.0, 0.95),
        (35.75, 0.75, 82.0, 0.96),
        (36.75, 0.5, 81.0, 0.94),
        (37.25, 0.5, 79.0, 0.92),
        (37.88, 0.62, 77.0, 0.94),
        (38.62, 0.38, 76.0, 0.9),
        (39.25, 0.75, 74.0, 0.95),
        # sequence continues up register
        (40.5, 0.5, 81.0, 0.97),
        (41.0, 0.5, 79.0, 0.95),
        (41.62, 0.38, 77.0, 0.92),
        (42.25, 1.0, 74.0, 0.96),
        (43.38, 0.62, 72.0, 0.9),
        (44.12, 0.88, 70.0, 0.92),
        (45.25, 0.75, 69.0, 0.94),
        (46.25, 0.75, 74.0, 0.97),
        (47.25, 0.75, 77.0, 0.98),
    ]
    for b, d, m, v in theme_a:
        notes_lead.append((b, d, m, LAY["lead"] * v))

    # Harmony: fifth below lead on strong pulses (bars 16–47)
    for b, d, m, v in list(theme_a):
        if int(b) % 2 == 0 or d >= 1.0:
            low = m - 7 if m % 12 not in (0, 5) else m - 5
            low = max(55.0, low)
            notes_harm.append((b, min(d + 0.15, 1.35), low, LAY["harm"] * v * 0.55))

    # --- Bridge (bars 12–15): climb into chorus ---
    bridge: list[tuple[float, float, float, float]] = [
        (48.0, 0.5, 69.0, 0.88),
        (48.5, 0.5, 72.0, 0.9),
        (49.0, 0.75, 74.0, 0.94),
        (49.88, 0.37, 76.0, 0.92),
        (50.38, 0.62, 77.0, 0.95),
        (51.12, 0.38, 76.0, 0.9),
        (51.62, 0.38, 74.0, 0.9),
        (52.12, 0.63, 72.0, 0.92),
        (52.88, 0.62, 70.0, 0.9),
        (53.62, 0.38, 72.0, 0.9),
        (54.25, 0.75, 74.0, 0.95),
        (55.25, 0.5, 76.0, 0.95),
        (55.88, 0.5, 79.0, 0.98),
        (56.5, 0.62, 81.0, 1.0),
        (57.25, 0.5, 79.0, 0.95),
        (57.88, 0.5, 77.0, 0.93),
        (58.5, 1.25, 76.0, 0.96),
        (59.88, 0.37, 77.0, 0.94),
        (60.38, 0.37, 79.0, 0.96),
        (60.88, 0.62, 81.0, 1.0),
        (61.62, 0.38, 82.0, 0.98),
        (62.12, 0.88, 84.0, 1.02),
        (63.25, 0.5, 86.0, 1.0),
    ]
    for b, d, m, v in bridge:
        notes_lead.append((b, d, m, LAY["lead"] * v))
        if d >= 0.62 or int(b) % 3 == 0:
            hh = max(57.0, m - 7)
            notes_harm.append((b, min(d + 0.2, 1.3), hh, LAY["harm"] * v * 0.48))

    # --- Chorus line (bars 16–21): brighter hook ---
    chorus: list[tuple[float, float, float, float]] = [
        (64.0, 0.5, 86.0, 1.0),
        (64.62, 0.38, 84.0, 0.96),
        (65.25, 0.5, 81.0, 0.98),
        (65.88, 0.5, 82.0, 0.97),
        (66.62, 0.38, 84.0, 1.0),
        (67.25, 0.75, 86.0, 1.0),
        (68.25, 0.5, 87.0, 1.0),
        (68.88, 0.5, 86.0, 0.98),
        (69.5, 0.5, 84.0, 0.96),
        (70.25, 0.75, 81.0, 0.98),
        (71.25, 0.5, 82.0, 0.95),
        (71.88, 0.5, 81.0, 0.95),
        (72.62, 0.38, 79.0, 0.92),
        (73.25, 1.0, 77.0, 0.96),
        (74.5, 0.5, 79.0, 0.95),
        (75.25, 0.75, 81.0, 1.0),
        (76.25, 0.5, 82.0, 1.0),
        (76.88, 0.5, 84.0, 1.0),
        (77.62, 1.37, 86.0, 1.05),
        (81.25, 0.5, 84.0, 0.98),
        (81.88, 0.5, 82.0, 0.96),
        (82.5, 1.25, 81.0, 1.0),
        (83.88, 0.62, 79.0, 0.94),
        (84.62, 0.63, 77.0, 0.94),
        (85.38, 0.62, 76.0, 0.92),
        (86.25, 0.75, 74.0, 0.96),
        (87.25, 0.75, 77.0, 0.98),
        (88.25, 0.75, 81.0, 1.0),
        (89.25, 0.5, 84.0, 1.0),
        (89.88, 0.5, 82.0, 0.97),
        (90.62, 0.38, 81.0, 0.96),
        (91.25, 0.75, 79.0, 0.95),
    ]
    for b, d, m, v in chorus:
        notes_lead.append((b, d, m, LAY["lead"] * v))
        fifth = m - 7 if m >= 74 else m - 5
        fifth = max(59.0, fifth)
        notes_harm.append((b, min(d + 0.22, 1.5), fifth, LAY["harm"] * v * 0.5))

    # --- Bars 92–112: triumphant rall + land on low D + high D ---
    outro_lead = [
        (92.25, 0.5, 88.0, 1.0),
        (92.88, 0.5, 87.0, 0.99),
        (93.5, 0.62, 86.0, 1.0),
        (94.25, 0.75, 84.0, 0.98),
        (95.25, 0.5, 86.0, 1.0),
        (95.88, 0.5, 87.0, 1.0),
        (96.62, 0.38, 86.0, 1.0),
        (97.25, 0.75, 84.0, 1.02),
        (98.25, 0.5, 82.0, 0.98),
        (98.88, 1.62, 81.0, 1.0),
        (100.62, 0.38, 79.0, 0.95),
        (101.25, 0.5, 77.0, 0.95),
        (101.88, 0.5, 74.0, 1.05),
        (102.62, 0.88, 81.0, 1.12),
        (103.62, 0.38, 77.0, 1.0),
        (104.25, 0.5, 74.0, 1.02),
        (104.88, 2.8, 86.0, 1.08),  # high ring over final bass
        (107.75, 2.35, 86.0, 0.92),  # hold / decay overlap
        (109.62, 1.62, 86.0, 0.65),
        (111.0, 0.92, 86.0, 0.4),
    ]
    for b, d, m, v in outro_lead:
        notes_lead.append((b, d, m, LAY["lead"] * v))

    outro_harm = [
        (92.25, 0.72, 79.0, LAY["harm"] * 0.45),
        (93.5, 0.92, 77.0, LAY["harm"] * 0.42),
        (95.25, 0.85, 79.0, LAY["harm"] * 0.45),
        (98.25, 1.62, 74.0, LAY["harm"] * 0.42),
        (101.88, 0.85, 69.0, LAY["harm"] * 0.38),
        (104.88, 2.2, 74.0, LAY["harm"] * 0.52),
        (109.62, 1.92, 77.0, LAY["harm"] * 0.48),
    ]
    notes_harm.extend(outro_harm)

    # Strum-ish pad on downbeats chorus (whole notes feel)
    for bar in range(18, 24):
        b0 = bar * 4.0
        notes_harm.append((b0, 3.85, 62.0, LAY["harm"] * 0.35))
        notes_harm.append((b0, 3.85, 69.0, LAY["harm"] * 0.28))

    # Render
    env_b = env_staccato
    env_h = env_pad
    env_l = env_staccato

    def render_batch(items: list[tuple[float, float, float, float]], use_env):
        for b_start, dur_b, midi, g in items:
            t0 = beats_to_samples(b_start)
            d = beats_to_samples(dur_b)
            if d <= 0 or g <= 0:
                continue
            hz = midi_to_hz(midi)
            add_square(buf, t0, d, hz, g, use_env)

    render_batch(notes_bass, env_b)
    render_batch(notes_harm, env_h)
    render_batch(notes_lead, env_l)

    normalize_peak(buf, peak=0.94)
    fade_edges(buf, int(SR * 0.024), int(SR * 0.045))
    return buf


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    out = root / "media" / "ratuba-chiptune.wav"
    buf = build_song()
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        for x in buf:
            w.writeframes(struct.pack("<h", clamp_i16(x)))


if __name__ == "__main__":
    main()
