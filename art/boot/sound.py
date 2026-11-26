"""Original K.OS startup sound, synthesized from scratch (no samples).
Writes three variations as 48 kHz stereo WAV masters (before loudness normalizing).
"""
import sys
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
from timeline import HITS, DUR

SR = 48000
N = int(SR * 7.2)
rng = np.random.default_rng(7)


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def place(buf, sig, start, pan=0.0, gain=1.0):
    i = int(start * SR)
    if i >= buf.shape[0]:
        return
    sig = sig[: buf.shape[0] - i] * gain
    left = np.cos((pan + 1) * np.pi / 4)
    right = np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * left * 1.414
    buf[i:i + len(sig), 1] += sig * right * 1.414


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def svf(x, cut, mode="low", q=0.9):
    """State-variable filter with a per-sample cutoff (no clicks)."""
    cut = np.broadcast_to(np.asarray(cut, dtype=float), x.shape)
    g = np.tan(np.pi * np.clip(cut, 20, SR * 0.45) / SR)
    k = 1.0 / q
    ic1 = ic2 = 0.0
    out = np.empty_like(x)
    for i in range(len(x)):
        gi = g[i]
        a1 = 1.0 / (1.0 + gi * (gi + k))
        v3 = x[i] - ic2
        v1 = a1 * ic1 + gi * a1 * v3
        v2 = ic2 + gi * v1
        ic1 = 2 * v1 - ic1
        ic2 = 2 * v2 - ic2
        out[i] = v2 if mode == "low" else (v1 if mode == "band" else x[i] - k * v1 - v2)
    return out


def kick(dur=0.35, f0=150, f1=45):
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 9) + 0.15 * lp(rng.standard_normal(len(t)), 2000) * np.exp(-t * 80)


def clap(dur=0.25):
    t = t_axis(dur)
    n = bp(rng.standard_normal(len(t)), 900, 5000)
    env = np.exp(-t * 22)
    for d in (0.0, 0.011, 0.022):
        env += 0.6 * np.exp(-np.clip(t - d, 0, None) * 120) * (t >= d)
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30)
    return 0.5 * n * env + 0.3 * body


def hat(dur=0.06):
    t = t_axis(dur)
    return hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * 70) * 0.35


def saw(f, t, detune=0.0):
    ph = (f * (1 + detune)) * t
    return 2 * (ph - np.floor(ph + 0.5))


def stab(notes, dur=0.32, bright=3500, decay=7.0):
    """Brass-like chord stab: detuned saws through a closing low-pass."""
    t = t_axis(dur)
    x = np.zeros(len(t))
    for n in notes:
        f = midi(n)
        for d in (-0.004, 0.0, 0.005):
            x += saw(f, t, d)
    x /= len(notes) * 3
    # Filter sweep down for a punchy attack
    out = svf(x, 400 + bright * np.exp(-t * 14), "low", 1.2)
    env = np.minimum(1, t / 0.006) * np.exp(-t * decay)
    return out * env


def bass(n, dur=0.22):
    t = t_axis(dur)
    f = midi(n)
    x = 0.7 * np.sin(2 * np.pi * f * t) + 0.3 * lp(saw(f, t), 900)
    return x * np.minimum(1, t / 0.004) * np.exp(-t * 6)


def whoosh(dur=0.25, lo=300, hi=4000, rise=True):
    t = t_axis(dur)
    n = rng.standard_normal(len(t))
    p = t / dur if rise else 1 - t / dur
    out = svf(n, lo * (hi / lo) ** p, "band", 1.5)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return out * env


def riser(dur, f0=200, f1=1400):
    t = t_axis(dur)
    p = t / dur
    f = f0 * (f1 / f0) ** p
    ph = np.cumsum(f) / SR
    tone = 2 * (ph - np.floor(ph + 0.5))
    tone = lp(tone, 3000)
    noise = whoosh(dur, 400, 7000, True)
    env = p ** 2
    return (0.35 * tone + 0.8 * noise) * env


def sub_boom(dur=1.4, f=46):
    t = t_axis(dur)
    ff = f + 30 * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(ff) / SR
    return np.sin(ph) * np.exp(-t * 3.2)


def bell(n, dur=2.6, ratio=3.5, index=2.2):
    """Soft FM bell: the K.OS power-on tone."""
    t = t_axis(dur)
    f = midi(n)
    mod_env = np.exp(-t * 5)
    x = np.sin(2 * np.pi * f * t + index * mod_env * np.sin(2 * np.pi * f * ratio * t))
    return x * np.minimum(1, t / 0.003) * np.exp(-t * 1.6)


def pad(notes, dur=2.6):
    t = t_axis(dur)
    x = np.zeros(len(t))
    for n in notes:
        f = midi(n)
        x += saw(f, t, -0.003) + saw(f, t, 0.003)
    x = lp(x / (2 * len(notes)), 1600)
    env = np.minimum(1, t / 0.02) * np.exp(-t * 1.5)
    return x * env


def reverb(x, secs=1.6, mix=0.25):
    t = t_axis(secs)
    ir_l = rng.standard_normal(len(t)) * np.exp(-t * 4.2)
    ir_r = rng.standard_normal(len(t)) * np.exp(-t * 4.2)
    ir_l = lp(ir_l, 6000)
    ir_r = lp(ir_r, 6000)
    wl = fftconvolve(x[:, 0], ir_l)[: len(x)]
    wr = fftconvolve(x[:, 1], ir_r)[: len(x)]
    wet = np.stack([wl, wr], 1)
    wet *= np.max(np.abs(x)) / (np.max(np.abs(wet)) + 1e-9)
    return x * (1 - mix) + wet * mix


def build(variant):
    dry = np.zeros((N, 2))
    H = HITS
    groove = variant == "A"
    stabs = variant in ("A", "B")

    # Swooshes for every slash and slam (all variants)
    place(dry, whoosh(0.32, 300, 5000), H["slash"] - 0.22, -0.4, 0.5)
    for k, pan in (("t1", -0.5), ("t2", 0.5)):
        place(dry, whoosh(0.2, 500, 6000), H[k] - 0.16, pan, 0.45)
    for k in ("m1", "m2", "m3"):
        place(dry, whoosh(0.12, 800, 7000), H[k] - 0.08, 0.0, 0.25)

    # Groove: kick, clap, hats at 150 BPM
    if groove:
        for b in np.arange(0.8, 3.0, 0.4):
            place(dry, kick(), b, 0, 0.9)
        for b in (1.2, 2.0, 2.8):
            place(dry, clap(), b, 0.1, 0.55)
        for i, b in enumerate(np.arange(0.4, 3.4, 0.1)):
            place(dry, hat(), b, 0.35 if i % 2 else -0.35, 0.5 if i % 2 else 0.3)
        line = [(0.8, 38), (1.2, 41), (1.6, 43), (2.0, 45), (2.4, 46), (2.6, 47), (2.8, 48), (3.0, 49)]
        for b, n in line:
            place(dry, bass(n), b, 0, 0.7)

    # Chord stabs on the text slams and montage cuts (jazzy minor 9ths climbing)
    if stabs:
        chords = {
            "t1": [62, 65, 69, 72, 76],   # Dm9
            "t1b": [62, 65, 69, 72, 76],
            "t2": [58, 62, 65, 69, 72],   # Bbmaj7 (add 9 feel)
            "t2b": [60, 64, 67, 69, 74],  # C6/9
            "m1": [61, 65, 68, 71],       # rising tension
            "m2": [62, 66, 69, 72],
            "m3": [63, 67, 70, 73],
            "m4": [64, 68, 71, 74],
        }
        for k, notes in chords.items():
            short = k.startswith("m")
            place(dry, stab(notes, 0.22 if short else 0.34, 3800, 9 if short else 6.5), H[k],
                  -0.25 if k.endswith("b") else 0.2, 0.55 if groove else 0.85)
    else:
        # Minimal: soft low thumps instead of stabs
        for k in ("t1", "t2", "m1", "m2", "m3"):
            place(dry, kick(0.25, 110, 50), H[k], 0, 0.5)

    # Riser from the red dot growth into the K slam
    place(dry, riser(H["K"] - H["m4"]), H["m4"], 0, 0.55 if variant != "C" else 0.35)

    # K slam: boom + big stab
    place(dry, kick(0.5, 170, 42), H["K"], 0, 1.0)
    place(dry, sub_boom(1.2), H["K"], 0, 0.6)
    if stabs:
        place(dry, stab([50, 62, 65, 69, 72, 76], 0.5, 4200, 4.5), H["K"], 0, 0.6)

    # Dot powers on: warm D major 9 resolution with the K.OS bell
    place(dry, sub_boom(1.8, 38), H["dot"], 0, 0.45)
    place(dry, pad([50, 57, 62, 66, 69, 73, 76], 2.6), H["dot"], 0, 0.55)
    place(dry, bell(81, 2.6), H["dot"], -0.15, 0.32)        # A5
    place(dry, bell(78, 2.4, 2.0, 1.4), H["dot"] + 0.07, 0.2, 0.22)  # F#5
    place(dry, bell(86, 2.0, 3.0, 1.0), H["dot"] + 0.14, 0.0, 0.10)  # D6, soft

    out = reverb(dry, 1.8, 0.22)
    # Clean the extreme lows and harsh highs for TV speakers
    out = np.stack([lp(hp(out[:, c], 30), 12000) for c in range(2)], 1)
    # Fade out with the picture
    t = np.arange(N) / SR
    fade = np.clip((DUR - 0.05 - t) / (DUR - 0.05 - HITS["fade"]), 0, 1) ** 1.5
    out *= np.where(t < HITS["fade"], 1.0, fade)[:, None]
    out = out[: int(SR * DUR)]
    out /= np.max(np.abs(out)) + 1e-9
    return (out * 0.8).astype(np.float32)


if __name__ == "__main__":
    outdir = sys.argv[1]
    for v in ("A", "B", "C"):
        wavfile.write(f"{outdir}/raw_{v}.wav", SR, build(v))
        print("wrote", v)
