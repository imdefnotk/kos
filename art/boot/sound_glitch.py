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
from timeline3 import T, DUR

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


def build():
    out = np.zeros((N + SR, 2))
    # 1. Power on under the boot logo: relay, 50 Hz hum, sparks, a low pressure bed
    place(out, C.lock_click(), 0.05, 0, 0.5)
    place(out, tail(fade_in(C.mains_hum(T["K"] + 1.2), 0.4), 1.0), 0.05, 0, 0.14)
    place(out, C.crackle(T["K"], 5, 0.5), 0.3, 0.3, 0.3)
    place(out, tail(fade_in(braam(T["K"] + 0.4, 26, 260) * 0.5, 0.8), 0.6), 0.2, 0, 0.22)
    # 2. Streak: an electric arc that glitches
    place(out, C.arc(0.45), T["streak"] - 0.02, -0.4, 0.55)
    place(out, S.whoosh(0.45, 400, 7000), T["streak"] - 0.15, 0.4, 0.3)
    place(out, corruption(0.14, 0.7), T["streak"] + 0.12, 0.2, 0.4)
    # 3. Close-ups: clank, distorted bass, servo, latch, plus a corruption flick
    for key, n, f, pan in (("c1", 38, 170, -0.3), ("c2", 41, 205, 0.3), ("c3", 45, 240, -0.1)):
        place(out, C.clank(f), T[key], pan, 0.45)
        place(out, C.dist_hit(n), T[key], 0, 0.5)
        place(out, C.servo(0.32, 260, 620), T[key] + 0.05, -pan, 0.26)
        place(out, C.lock_click(), T[key], pan, 0.35)
        place(out, corruption(0.07, 0.6), T[key] + 0.18, -pan, 0.3)
    # 4. The Operator: a dark braam swell, growl, hydraulics, mechanical pulse
    op_len = T["K"] + 0.5 - T["op"]
    place(out, tail(braam(op_len, 26, 1100), 0.5), T["op"], 0, 0.5)
    place(out, tail(fade_in(C.growl_bass(op_len), 0.25), 0.5), T["op"], 0, 0.28)
    place(out, C.hydraulic(0.7), T["op"], -0.5, 0.5)
    place(out, C.servo(0.8, 180, 420), T["op"] + 0.25, 0.4, 0.3)
    for k in range(3):
        place(out, S.kick(0.35, 90, 40), T["op"] + 0.4 * k, 0, 0.5)
    # 5. Its light switches on: zap and corruption, then a rising whine into the reveal
    place(out, C.arc(0.2, 4000, 900), T["eye"], 0.2, 0.45)
    place(out, corruption(0.2, 0.8), T["eye"] + 0.04, -0.2, 0.4)
    rise = T["K"] + 0.03 - T["eye"]
    place(out, tail(C.powerup(rise), 0.04), T["eye"], 0, 0.3)
    place(out, tail(C.ratchet(rise), 0.04), T["eye"], -0.2, 0.22)
    place(out, tail(S.whoosh(rise, 300, 9000), 0.04), T["eye"], 0, 0.35)
    # 6. Reveal: giant braam, slam, sub drop, arc
    place(out, braam(2.8, 26, 1600), T["K"], 0, 0.9)
    place(out, S.sub_boom(2.2, 33), T["K"], 0, 0.8)
    place(out, C.clank(110, 1.4), T["K"], 0, 0.55)
    place(out, C.lock_click(), T["K"], 0, 0.6)
    place(out, C.arc(0.5, 2500, 120), T["K"], -0.2, 0.35)
    # 7. Dot powers on: the K.OS motif on a gritty synth, a corruption tick as it pops
    d = T["dot"]
    place(out, C.pad([50, 57, 62, 66, 69, 76], DUR - d), d, 0, 0.42)
    place(out, S.sub_boom(1.6, 37), d, 0, 0.35)
    place(out, C.synth_note(69, 1.6), d, -0.15, 0.55)
    place(out, C.synth_note(74, 2.6, 0.9), d + 0.16, 0.15, 0.6)
    place(out, corruption(0.06, 0.8), d, 0.3, 0.3)
    # 8. Rolling: recording beep, motor hum, a soft static tick each time the light comes on
    place(out, C.rec_beep(), T["roll"], 0, 0.5)
    hum = C.mains_hum(DUR - T["roll"], 100) * 0.5 + C.servo(DUR - T["roll"], 120, 140) * 0.4
    place(out, tail(fade_in(hum, 0.4), 1.0), T["roll"], 0, 0.15)
    b = T["roll"] + 1.0
    while b < DUR - 0.4:
        place(out, corruption(0.035, 0.5), b, 0, 0.18)
        b += 1.0

    out = reverb(out, 1.8, 0.18)
    # glitch edits on the finished mix
    out = stutter(out, T["streak"] + 0.02, [0.04, 0.04, 0.04])
    out = stutter(out, T["eye"], [0.03, 0.03])
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
