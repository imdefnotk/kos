"""K.OS startup sound, glitch version: dark, heavy and digitally corrupted,
in the spirit of a cyberpunk logo sting (original composition, nothing sampled).
Keeps the electrical and mechanical layers, drops the data blips, and adds
distorted bass swells, buffer stutters, bit crushing and corruption bursts.
Timing from timeline3.py (KOS_LONG=1 for 10 seconds).
"""
import sys
import numpy as np
from scipy.io import wavfile
import sound as S
import sound_cyber as C
from sound import SR, t_axis, midi, place, lp, hp, bp, svf, reverb
from sound_cyber import tail, fade_in, drive, crush
from timeline3 import T, DUR, BOOT, LOCK

N = int(SR * DUR)
rng = np.random.default_rng(77)


def braam(dur, root=26, open_to=1400):
    """Huge distorted bass swell: detuned saws, heavy drive, opening filter."""
    t = t_axis(dur)
    p = t / dur
    x = np.zeros(len(t))
    for n, a in ((root, 1.0), (root + 7, 0.6), (root + 12, 0.7), (root + 19, 0.25)):
        f = midi(n)
        for d in (-0.008, 0.0, 0.007):
            x += a * S.saw(f, t, d)
    x = svf(x / 8, 90 + open_to * (1 - np.exp(-t * 3.5)) * (1 - 0.6 * p), "low", 1.5)
    x = drive(x, 3.5)
    env = np.minimum(1, t / 0.08) * np.exp(-t * 0.9)
    return x * env


def corruption(dur=0.15, intensity=1.0):
    """Digital corruption burst: sample-and-hold noise, square fragments, dropouts."""
    t = t_axis(dur)
    x = np.zeros(len(t))
    i = 0
    while i < len(t):
        n = int(rng.uniform(0.004, 0.02) * SR)
        kind = rng.integers(0, 3)
        seg = np.arange(min(n, len(t) - i))
        if kind == 0:
            hold = rng.integers(8, 60)
            v = np.repeat(rng.uniform(-1, 1, len(seg) // hold + 1), hold)[: len(seg)]
        elif kind == 1:
            f = rng.choice([180, 360, 720, 1440, 2880])
            v = np.sign(np.sin(2 * np.pi * f * seg / SR)) * 0.6
        else:
            v = np.zeros(len(seg))  # dropout
        x[i:i + len(seg)] = v
        i += n
    x = crush(x, 4, 3)
    env = np.minimum(1, t / 0.002) * np.minimum(1, (dur - t) / 0.01)
    return hp(x, 150) * env * intensity


def stutter(out, t0, slices):
    """Buffer repeat glitch on the mix: repeat the slice starting at t0."""
    i = int(t0 * SR)
    pos = i
    for L in slices:
        n = int(L * SR)
        if pos + n >= len(out) or i + n >= len(out):
            break
        seg = out[i:i + n].copy()
        ramp = min(64, n // 4)
        seg[:ramp] *= np.linspace(0, 1, ramp)[:, None]
        seg[-ramp:] *= np.linspace(1, 0, ramp)[:, None]
        out[pos:pos + n] = seg
        pos += n
    return out


def crush_region(out, t0, t1, bits=5, hold=8):
    i, j = int(t0 * SR), int(t1 * SR)
    for c in range(2):
        seg = out[i:j, c]
        cr = crush(seg / (np.max(np.abs(seg)) + 1e-9), bits, hold) * (np.max(np.abs(seg)) + 1e-9)
        w = np.ones(len(seg))
        r = min(200, len(seg) // 4)
        w[:r] = np.linspace(0, 1, r)
        w[-r:] = np.linspace(1, 0, r)
        out[i:j, c] = seg * (1 - w) + cr * w
    return out


def slash(dur=0.42, pan_from=-0.7):
    """Blade slash: a fast falling band of noise with a short metallic shing."""
    t = t_axis(dur)
    cut = 7000 * np.exp(-t * 9) + 900
    swoosh = svf(rng.standard_normal(len(t)), cut, "band", 2.2)
    env = (t / 0.05) ** 2 * (t < 0.05) + np.exp(-(t - 0.05) * 9) * (t >= 0.05)
    shing = np.zeros(len(t))
    for f, a, d in ((3150, 0.5, 14), (4730, 0.35, 18), (6290, 0.25, 22), (8110, 0.15, 30)):
        shing += a * np.sin(2 * np.pi * f * t * (1 + 0.004 * np.sin(2 * np.pi * 7 * t))) * np.exp(-np.clip(t - 0.04, 0, None) * d) * (t > 0.035)
    air = lp(rng.standard_normal(len(t)), 900) * env * 0.5
    return swoosh * env * 1.2 + shing * 0.18 + air


def place_sweep(out, sig, start, pan_from, pan_to, gain):
    """Place a mono sound that travels across the stereo field."""
    i = int(start * SR)
    sig = sig[: out.shape[0] - i] * gain
    p = np.linspace(pan_from, pan_to, len(sig))
    out[i:i + len(sig), 0] += sig * np.cos((p + 1) * np.pi / 4) * 1.414
    out[i:i + len(sig), 1] += sig * np.sin((p + 1) * np.pi / 4) * 1.414


def arc_soft(dur=0.4):
    """Electric arc that is mostly crackle, with almost no tone."""
    t = t_axis(dur)
    gate = (np.sin(2 * np.pi * rng.uniform(40, 90) * t + rng.uniform(0, 6)) > -0.2).astype(float)
    noise = bp(rng.standard_normal(len(t)), 1500, 9000) * gate
    return noise * np.minimum(1, t / 0.003) * np.exp(-t * 9)


def build():
    out = np.zeros((N + SR, 2))
    # 1. Power on under the boot logo: relay, 50 Hz hum, sparks, a low pressure bed
    # signal locking on: a corruption burst for every visual glitch, then the latch
    for k, (a, b) in enumerate(BOOT):
        place(out, corruption(b - a + 0.02, 0.9), a, (-0.4, 0.4)[k % 2], 0.55)
        place(out, C.crackle(b - a + 0.05, 60, 0.8), a, 0, 0.35)
    if BOOT:
        place(out, S.kick(0.4, 70, 35), BOOT[0][0], 0, 0.5)
        place(out, tail(S.whoosh(LOCK - BOOT[0][0], 200, 5000), 0.03), BOOT[0][0], 0, 0.2)
    place(out, C.lock_click(), LOCK + 0.01, 0, 0.6)
    place(out, S.kick(0.35, 110, 45), LOCK + 0.01, 0, 0.45)
    place(out, tail(fade_in(C.mains_hum(T["K"] + 1.2 - LOCK), 0.3), 1.0), LOCK, 0, 0.14)
    place(out, C.crackle(T["K"] - LOCK, 5, 0.5), LOCK + 0.2, 0.3, 0.3)
    place(out, tail(fade_in(braam(T["K"] + 0.4 - LOCK, 26, 260) * 0.5, 0.6), 0.6), LOCK, 0, 0.22)
    # 2. Streak: an electric arc that glitches
    place(out, arc_soft(0.45), T["streak"] - 0.02, -0.4, 0.5)
    place(out, S.whoosh(0.45, 400, 7000), T["streak"] - 0.15, 0.4, 0.3)
    place(out, corruption(0.14, 0.7), T["streak"] + 0.12, 0.2, 0.4)
    # 3. Close-ups: clank, distorted bass, servo, latch, plus a corruption flick
    for key, pf, pt in (("c1", -0.8, 0.7), ("c2", 0.8, -0.7), ("c3", -0.6, 0.8)):
        place_sweep(out, slash(), T[key] - 0.06, pf, pt, 0.42)
        place(out, S.kick(0.3, 85, 40), T[key], 0, 0.35)
        place(out, corruption(0.06, 0.7), T[key] + 0.16, pt, 0.32)
    # 4. The Operator: a dark braam swell, growl, hydraulics, mechanical pulse
    op_len = T["K"] + 0.5 - T["op"]
    place(out, tail(braam(op_len, 26, 1100), 0.5), T["op"], 0, 0.34)
    place(out, tail(fade_in(C.growl_bass(op_len), 0.25), 0.5), T["op"], 0, 0.2)
    place(out, C.hydraulic(0.7), T["op"], -0.5, 0.5)
    for k in range(3):
        place(out, S.kick(0.35, 90, 40), T["op"] + 0.4 * k, 0, 0.5)
    # 5. Its light switches on: zap and corruption, then a rising whine into the reveal
    place(out, arc_soft(0.22), T["eye"], 0.2, 0.45)
    place(out, corruption(0.2, 0.8), T["eye"] + 0.04, -0.2, 0.4)
    rise = T["K"] + 0.03 - T["eye"]
    place(out, tail(C.ratchet(rise), 0.04), T["eye"], -0.2, 0.22)
    place(out, tail(S.whoosh(rise, 300, 9000), 0.04), T["eye"], 0, 0.35)
    # 6. Reveal: giant braam, slam, sub drop, arc
    place(out, braam(2.8, 26, 1600), T["K"], 0, 0.9)
    place(out, S.sub_boom(2.2, 33), T["K"], 0, 0.8)
    place(out, C.clank(110, 1.4), T["K"], 0, 0.55)
    place(out, C.lock_click(), T["K"], 0, 0.6)
    place(out, arc_soft(0.5), T["K"], -0.2, 0.35)
    place_sweep(out, slash(0.6), T["K"] - 0.04, -0.9, 0.9, 0.6)
    # 7. Dot powers on: the K.OS motif on a gritty synth, a corruption tick as it pops
    d = T["dot"]
    place(out, C.pad([50, 57, 62, 66, 69, 76], DUR - d), d, 0, 0.42)
    place(out, S.sub_boom(1.6, 37), d, 0, 0.35)
    place(out, C.synth_note(69, 1.6), d, -0.15, 0.55)
    place(out, C.synth_note(74, 2.6, 0.9), d + 0.16, 0.15, 0.6)
    place(out, corruption(0.06, 0.8), d, 0.3, 0.3)
    # 8. Rolling: recording beep, motor hum, a soft static tick each time the light comes on
    place(out, C.lock_click(), T["roll"], 0, 0.4)
    place(out, corruption(0.05, 0.6), T["roll"], 0, 0.25)
    hum = C.mains_hum(DUR - T["roll"], 50) * 0.6
    place(out, tail(fade_in(hum, 0.4), 1.0), T["roll"], 0, 0.15)
    b = T["roll"] + 1.0
    while b < DUR - 0.4:
        place(out, corruption(0.035, 0.5), b, 0, 0.18)
        b += 1.0

    out = reverb(out, 1.8, 0.18)
    # glitch edits on the finished mix
    if BOOT:
        out = stutter(out, BOOT[2][0], [0.025, 0.025, 0.02, 0.02])
        out = stutter(out, BOOT[4][0], [0.03, 0.02, 0.02, 0.015])
    out = stutter(out, T["streak"] + 0.02, [0.04, 0.04, 0.04])
    out = stutter(out, T["eye"], [0.03, 0.03])
    for key in ("c1", "c2", "c3"):
        out = stutter(out, T[key] + 0.05, [0.035, 0.035, 0.025])
        out = crush_region(out, T[key] + 0.15, T[key] + 0.26, bits=5, hold=9)
    # accelerating buffer stutter right before the reveal
    pre = T["K"] - 0.24
    out = stutter(out, pre, [0.06, 0.05, 0.04, 0.03, 0.025, 0.02, 0.015])
    # the reveal hit stutters once, then lands, then a crushed flicker
    out = stutter(out, T["K"] + 0.0, [0.045, 0.045])
    out = crush_region(out, T["K"] + 0.28, T["K"] + 0.42, bits=5, hold=10)
    out = crush_region(out, T["dot"] + 0.02, T["dot"] + 0.08, bits=6, hold=6)

    t = np.arange(len(out)) / SR
    out = np.stack([lp(hp(out[:, c], 28), 13500) for c in range(2)], 1)
    fade = np.clip((DUR - 0.05 - t) / (DUR - 0.05 - T["fade"]), 0, 1) ** 1.2
    out *= np.where(t < T["fade"], 1.0, fade)[:, None]
    out = out[:N]
    out /= np.max(np.abs(out)) + 1e-9
    return (out * 0.8).astype(np.float32)


if __name__ == "__main__":
    wavfile.write(sys.argv[1], SR, build())
