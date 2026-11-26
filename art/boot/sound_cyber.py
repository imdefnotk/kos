"""K.OS startup sound, cyberpunk version: electrical and mechanical.
Synthesized from scratch. Mains hum (50 Hz, like Turkish power), arcs and
crackle, servo motors, hydraulics, metal clanks, ratchets, distorted bass, a
power-up whine and a synth version of the K.OS motif (A rising to D).
Timing comes from timeline3.py (KOS_LONG=1 for the 10 second version).
"""
import sys
import numpy as np
from scipy.io import wavfile
import sound as S
from sound import SR, t_axis, midi, place, lp, hp, bp, svf, reverb
from timeline3 import T, DUR

N = int(SR * DUR)
rng = np.random.default_rng(23)


def tail(x, secs):
    n = min(len(x), int(secs * SR))
    x = x.copy()
    x[-n:] *= np.linspace(1, 0, n) ** 2
    return x


def fade_in(x, secs):
    n = min(len(x), int(secs * SR))
    x = x.copy()
    x[:n] *= np.linspace(0, 1, n) ** 2
    return x


def drive(x, amount):
    return np.tanh(x * amount) / np.tanh(amount)


def crush(x, bits=6, hold=6):
    y = np.repeat(x[::hold], hold)[: len(x)]
    q = 2 ** (bits - 1)
    return np.round(y * q) / q


# ---------- electrical ----------
def mains_hum(dur, f=50.0):
    t = t_axis(dur)
    x = sum((0.9 / k) * np.sin(2 * np.pi * f * k * t + k) for k in range(1, 10))
    flicker = 1 + 0.15 * np.sin(2 * np.pi * 0.7 * t) * np.sin(2 * np.pi * 3.1 * t)
    return lp(drive(x * 0.6, 2.5), 2500) * flicker


def crackle(dur, density=30, amp=1.0):
    t = t_axis(dur)
    x = np.zeros(len(t))
    for _ in range(int(density * dur)):
        i = rng.integers(0, len(t) - 400)
        n = rng.integers(20, 300)
        x[i:i + n] += rng.standard_normal(n) * np.exp(-np.arange(n) / (n / 4)) * rng.uniform(0.2, 1.0)
    return hp(x, 2500) * amp


def arc(dur=0.35, f0=3200, f1=260):
    """Electric zap: gated noise plus a falling, distorted tone."""
    t = t_axis(dur)
    gate = (np.sin(2 * np.pi * rng.uniform(40, 90) * t + rng.uniform(0, 6)) > -0.2).astype(float)
    noise = bp(rng.standard_normal(len(t)), 1500, 9000) * gate
    f = f1 + (f0 - f1) * np.exp(-t * 14)
    tone = drive(np.sin(2 * np.pi * np.cumsum(f) / SR), 4) * 0.5
    env = np.minimum(1, t / 0.003) * np.exp(-t * 9)
    return (noise * 0.8 + tone) * env


def powerup(dur, f0=180, f1=2400):
    """Rising electric whine, like a capacitor charging."""
    t = t_axis(dur)
    p = t / dur
    f = f0 * (f1 / f0) ** (p ** 1.4)
    ph = 2 * np.pi * np.cumsum(f) / SR
    x = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.2 * np.sin(3 * ph)
    trem = 0.7 + 0.3 * np.sin(2 * np.pi * (6 + 30 * p) * t)
    return lp(x * trem, 6000) * p ** 1.3


def chirps(dur, count=14):
    """Fast data blips, like a machine handshaking."""
    t = t_axis(dur)
    x = np.zeros(len(t))
    for _ in range(count):
        i = rng.integers(0, max(1, len(t) - 2400))
        n = int(rng.uniform(0.012, 0.04) * SR)
        f = rng.choice([1320, 1760, 2093, 2637, 3136])
        tt = np.arange(n) / SR
        x[i:i + n] += np.sign(np.sin(2 * np.pi * f * tt)) * 0.3 * np.minimum(1, (n - np.arange(n)) / 60)
    return lp(x, 7000)


def rec_beep():
    t = t_axis(0.14)
    env = np.minimum(1, t / 0.003) * np.clip((0.14 - t) / 0.03, 0, 1)
    return (np.sin(2 * np.pi * 1975 * t) + 0.3 * np.sign(np.sin(2 * np.pi * 1975 * t))) * env * 0.3


# ---------- mechanical ----------
def servo(dur, f0=220, f1=520):
    """Servo motor whir with gear grit."""
    t = t_axis(dur)
    p = t / dur
    f = f0 * (f1 / f0) ** np.sin(np.pi * p * 0.5)
    ph = np.cumsum(f) / SR
    saw = 2 * (ph - np.floor(ph + 0.5))
    grit = (np.sin(2 * np.pi * np.cumsum(f * 7.3) / SR) > 0.6) * 0.25
    x = svf(saw + grit, 900 + 1800 * p, "band", 1.4)
    env = np.minimum(1, t / 0.04) * np.minimum(1, (dur - t) / 0.06)
    return x * env


def hydraulic(dur=0.5):
    t = t_axis(dur)
    n = svf(rng.standard_normal(len(t)), 2500 * np.exp(-t * 2) + 600, "band", 0.8)
    return n * np.minimum(1, t / 0.01) * np.exp(-t * 5)


def clank(f=180, dur=0.9):
    """Metal impact: inharmonic modes plus a sharp click."""
    t = t_axis(dur)
    x = np.zeros(len(t))
    for ratio, a, d in ((1.0, 1.0, 6), (2.76, 0.6, 9), (5.40, 0.4, 14), (8.93, 0.25, 20), (13.3, 0.15, 30)):
        x += a * np.sin(2 * np.pi * f * ratio * t + rng.uniform(0, 6)) * np.exp(-t * d)
    click = hp(rng.standard_normal(len(t)), 3000) * np.exp(-t * 300)
    return x * 0.5 + click * 0.6


def lock_click():
    """Visor or latch locking: ka-chunk."""
    out = np.zeros(int(0.25 * SR))
    for d, a, f in ((0.0, 0.8, 2600), (0.045, 1.0, 900)):
        i = int(d * SR)
        n = int(0.03 * SR)
        burst = bp(rng.standard_normal(n), f * 0.5, f * 2) * np.exp(-np.arange(n) / SR * 180)
        out[i:i + n] += burst * a
    thud = S.kick(0.2, 120, 60) * 0.5
    out[int(0.045 * SR):int(0.045 * SR) + len(thud)] += thud[: len(out) - int(0.045 * SR)]
    return out


def ratchet(dur, r0=8, r1=40):
    """Accelerating mechanical clicks."""
    t = t_axis(dur)
    rate = r0 + (r1 - r0) * (t / dur) ** 2
    ph = np.cumsum(rate) / SR
    ticks = np.diff(np.floor(ph), prepend=0) > 0
    x = np.zeros(len(t))
    for i in np.nonzero(ticks)[0]:
        n = min(300, len(t) - i)
        x[i:i + n] += bp(rng.standard_normal(n), 2000, 7000) * np.exp(-np.arange(n) / 50)
    return x * (0.4 + 0.6 * t / dur)


# ---------- musical, synthetic ----------
def growl_bass(dur, n=26):
    t = t_axis(dur)
    f = midi(n)
    x = S.saw(f, t, -0.004) + S.saw(f, t, 0.004) + 0.5 * np.sign(np.sin(2 * np.pi * f / 2 * t))
    cut = 160 + 420 * (0.5 + 0.5 * np.sin(2 * np.pi * 2.2 * t))
    return drive(svf(x * 0.5, cut, "low", 2.2), 2.2)


def dist_hit(n, dur=0.7):
    t = t_axis(dur)
    f = midi(n)
    x = S.saw(f, t, 0.006) + S.saw(f * 2, t, -0.004) * 0.4
    x = drive(svf(x, 300 + 3000 * np.exp(-t * 18), "low", 1.6), 3.0)
    return x * np.minimum(1, t / 0.003) * np.exp(-t * 4.5)


def synth_note(n, dur, decay=1.2):
    t = t_axis(dur)
    f = midi(n)
    x = S.saw(f, t, -0.005) + S.saw(f, t, 0.005) + 0.4 * np.sin(2 * np.pi * f * 2 * t)
    x = svf(x / 2.4, 900 + 2800 * np.exp(-t * 3), "low", 1.3)
    x = 0.8 * x + 0.2 * crush(x, 7, 4)
    return x * np.minimum(1, t / 0.006) * np.exp(-t * decay)


def pad(notes, dur):
    t = t_axis(dur)
    x = sum(S.saw(midi(n), t, -0.003) + S.saw(midi(n), t, 0.003) for n in notes)
    x = svf(x / (2 * len(notes)), 700 + 300 * np.sin(2 * np.pi * 0.3 * t), "low", 0.9)
    return x * np.minimum(1, t / 0.1) * np.exp(-t * 0.6)


def build():
    out = np.zeros((N + SR, 2))
    # 1. Power comes on under the boot logo: relay click, mains hum, faint crackle
    place(out, lock_click(), 0.05, 0, 0.5)
    hum_len = T["K"] + 1.2
    place(out, tail(fade_in(mains_hum(hum_len), 0.4), 1.0), 0.05, 0, 0.16)
    place(out, crackle(T["K"], 6, 0.5), 0.3, 0.3, 0.35)
    # 2. Streak: an arc of electricity across the screen
    place(out, arc(0.45), T["streak"] - 0.02, -0.4, 0.55)
    place(out, S.whoosh(0.45, 400, 7000), T["streak"] - 0.15, 0.4, 0.35)
    # 3. Close-ups: metal clank, servo, shutter, distorted bass hit (D, F, A)
    for key, n, f, pan in (("c1", 38, 170, -0.3), ("c2", 41, 205, 0.3), ("c3", 45, 240, -0.1)):
        place(out, clank(f), T[key], pan, 0.45)
        place(out, dist_hit(n), T[key], 0, 0.45)
        place(out, servo(0.32, 260, 620), T[key] + 0.05, -pan, 0.28)
        place(out, lock_click(), T[key], pan, 0.35)
    # 4. The Operator: growling bass, hydraulics, servos as it turns, mechanical pulse
    op_len = T["K"] + 0.5 - T["op"]
    place(out, tail(fade_in(growl_bass(op_len), 0.25), 0.5), T["op"], 0, 0.42)
    place(out, hydraulic(0.7), T["op"], -0.5, 0.5)
    place(out, servo(0.8, 180, 420), T["op"] + 0.25, 0.4, 0.3)
    for k in range(3):
        place(out, S.kick(0.35, 90, 40), T["op"] + 0.4 * k, 0, 0.55)
    # 5. Its light switches on: zap, data chirps, power-up whine and ratchet into the reveal
    place(out, arc(0.2, 4000, 900), T["eye"], 0.2, 0.45)
    place(out, chirps(0.5), T["eye"] + 0.05, 0.3, 0.35)
    rise = T["K"] + 0.03 - T["eye"]
    place(out, tail(powerup(rise), 0.04), T["eye"], 0, 0.32)
    place(out, tail(ratchet(rise), 0.04), T["eye"], -0.2, 0.4)
    place(out, tail(S.whoosh(rise, 300, 9000), 0.04), T["eye"], 0, 0.35)
    # 6. Reveal: heavy mechanical slam with a sub drop and a big distorted chord
    place(out, S.sub_boom(2.2, 33), T["K"], 0, 0.9)
    place(out, clank(110, 1.4), T["K"], 0, 0.6)
    place(out, lock_click(), T["K"], 0, 0.6)
    place(out, arc(0.5, 2500, 120), T["K"], -0.2, 0.4)
    for n in (26, 38, 45, 50):
        place(out, dist_hit(n, 1.2), T["K"], 0, 0.25)
    # 7. The dot powers on: synth K.OS motif (A to D) over a D major pad, electric sparkle
    d = T["dot"]
    place(out, pad([50, 57, 62, 66, 69, 76], DUR - d), d, 0, 0.46)
    place(out, S.sub_boom(1.6, 37), d, 0, 0.35)
    place(out, synth_note(69, 1.6), d, -0.15, 0.55)
    place(out, synth_note(74, 2.6, 0.9), d + 0.16, 0.15, 0.6)
    place(out, lock_click(), d, 0, 0.35)
    place(out, S.bell(86, 1.8, 3.0, 1.0), d + 0.16, 0, 0.08)
    place(out, crackle(0.6, 25, 0.6), d, 0.4, 0.3)
    # 8. Rolling: recording beep, motor hum and quiet data chatter
    place(out, rec_beep(), T["roll"], 0, 0.5)
    place(out, tail(fade_in(mains_hum(DUR - T["roll"], 100) * 0.5 + servo(DUR - T["roll"], 120, 140) * 0.4, 0.4), 1.0),
          T["roll"], 0, 0.16)
    place(out, chirps(DUR - T["roll"] - 0.5, 8) * 0.5, T["roll"] + 0.3, -0.3, 0.25)

    out = reverb(out, 1.8, 0.2)
    t = np.arange(len(out)) / SR
    out = np.stack([lp(hp(out[:, c], 28), 13500) for c in range(2)], 1)
    fade = np.clip((DUR - 0.05 - t) / (DUR - 0.05 - T["fade"]), 0, 1) ** 1.2
    out *= np.where(t < T["fade"], 1.0, fade)[:, None]
    out = out[:N]
    out /= np.max(np.abs(out)) + 1e-9
    return (out * 0.8).astype(np.float32)


if __name__ == "__main__":
    wavfile.write(sys.argv[1], SR, build())
