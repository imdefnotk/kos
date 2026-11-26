"""K.OS startup video v5: the generated Operator illustration (Canva, expanded
with Adobe) replaces the placeholder. Its red light sits exactly on the K.OS
dot, so the light never moves while the Operator dissolves into the K.
Timing and sound: timeline3.py / sound3.py.
"""
import math
import subprocess
import sys
import skia
import render as R
import render2 as R2
import render4 as R4
from render import W, HH, BG, BLACK, RED, GREY, MED, prog, out_cubic, in_out, paint, draw_text, DOT_C, K_SIZE, K_X, K_BASE, LOGO_C
from timeline3 import T, DUR, FPS, BOOT, LOCK
import numpy as np

import os
S4K = 2 if os.environ.get("KOS_4K") == "1" else 1
ART = skia.Image.open(os.path.join(R.HERE, "..", "operator", "operator_v1_cutout_4k_nolight.png" if S4K == 2
                                   else "operator_v1_cutout_nolight.png"))
ART_RECT = skia.Rect(0, 0, 2080, 1500)  # the art's size in 1080p units
ART_EYE = (1197.72, 660.75)  # measured center of the light in the image
R4.EYE_R0 = 9.0              # size of the light in the illustration


def cover_art_light(c, x, y):
    """Hide the light painted in the illustration so ours controls it."""
    R2.glow_circle(c, x, y, 21, skia.Color(2, 1, 0), 1.0, 6)
    R2.glow_circle(c, x, y, 15, skia.Color(2, 1, 0), 1.0, 2)


def s_main(c, t):
    c.clear(BG)
    eye_on = R4.light(t)[0] if t < T["dot"] else 1.0
    after_eye = prog(t, T["eye"], T["rush"])
    dissolve = in_out(prog(t, T["rush"] - 0.05, T["K"] + 0.25))
    op_a = out_cubic(prog(t, T["op"], T["op"] + 0.5)) * (1 - dissolve)
    if op_a > 0.003:
        # slow push-in around the light, so the light itself never moves
        s = 1.0 + 0.07 * in_out(prog(t, T["op"], T["K"] + 0.25))
        c.saveLayerAlpha(None, int(255 * op_a))
        c.translate(DOT_C[0], DOT_C[1])
        c.scale(s, s)
        c.translate(-ART_EYE[0], -ART_EYE[1])
        c.drawImageRect(ART, ART_RECT, skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear))
        cover_art_light(c, ART_EYE[0], ART_EYE[1])
        c.restore()
        # red light spills onto the scene once it is on
        R2.glow_circle(c, DOT_C[0], DOT_C[1], 120, RED, 0.12 * after_eye * eye_on * op_a, 70)
    # the K arrives where the Operator stood
    tk = T["K"]
    if t >= tk - 0.02:
        k_in = out_cubic(prog(t, tk, tk + 0.35))
        k_out = 1 - in_out(prog(t, T["fade"] - 0.3, T["fade"] + 0.45))
        z = 1.04 - 0.04 * out_cubic(prog(t, tk, tk + 1.4))
        c.save()
        c.translate(LOGO_C[0], LOGO_C[1])
        c.scale(z, z)
        c.translate(-LOGO_C[0], -LOGO_C[1])
        c.saveLayerAlpha(None, int(255 * k_in * k_out))
        sweep = in_out(prog(t, tk, tk + 0.6))
        R2.lit_k(c, R2.k_path(K_SIZE, K_X, K_BASE), R.WHITE, (K_X - 300 + 900 * sweep, 0), 12, 120,
                 0.9 * (1 - prog(t, tk + 0.45, tk + 0.75)))
        c.restore()
        c.restore()
        a = out_cubic(prog(t, tk + 0.9, tk + 1.5)) * k_out
        if a > 0:
            draw_text(c, "K.OS", W / 2 + 0.2 * 28, 725 + 14 * (1 - a), 28, paint(GREY, a), tracking=0.4, tf=MED)
    R4.draw_light(c, t)


def _logo_layer():
    surf = skia.Surface(W * S4K, HH * S4K)
    lc = surf.getCanvas()
    lc.clear(skia.ColorTRANSPARENT)
    lc.scale(S4K, S4K)
    R.draw_logo(lc)
    return surf.makeImageSnapshot()


LOGO_IMG = _logo_layer()
RED_ONLY = skia.ColorFilters.Matrix([1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0])
CYAN_ONLY = skia.ColorFilters.Matrix([0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0])
SAMP = skia.SamplingOptions(skia.FilterMode.kLinear)


def glitch_logo(c, t, strength):
    """The logo as a broken signal: shifted slices, red/cyan split, corruption blocks."""
    rng = np.random.default_rng(int(t * FPS) * 7 + 3)
    split = 6 + 22 * strength
    y = 0.0
    while y < HH:
        h = float(rng.integers(8, 90))
        dx = float(rng.normal(0, 70 * strength)) if rng.random() < 0.55 else 0.0
        src = skia.Rect(0, y * S4K, W * S4K, (y + h) * S4K)
        for cf, off in ((RED_ONLY, -split), (CYAN_ONLY, split)):
            p = skia.Paint(ColorFilter=cf)
            p.setBlendMode(skia.BlendMode.kPlus)
            p.setAlphaf(float(rng.uniform(0.7, 1.0)))
            c.drawImageRect(LOGO_IMG, src, skia.Rect(dx + off, y, W + dx + off, y + h), SAMP, p)
        y += h
    # blocky digital corruption around the logo area
    for _ in range(int(6 + 16 * strength)):
        bw, bh = float(rng.integers(20, 260)), float(rng.integers(4, 40))
        bx = float(rng.normal(LOGO_C[0], 320))
        by = float(rng.normal(LOGO_C[1] + 40, 160))
        col = [skia.Color(0x1C, 0x1C, 0x22), RED, R.WHITE, skia.Color(0x30, 0x0A, 0x0A)][int(rng.integers(0, 4))]
        c.drawRect(skia.Rect(bx, by, bx + bw, by + bh), paint(col, float(rng.uniform(0.15, 0.6)) * strength))
    # thin scanlines over everything
    for sy in range(0, HH, 4):
        c.drawRect(skia.Rect(0, sy, W, sy + 1), paint(BLACK, 0.25 * strength))


def s_splash(c, t):
    """Opening: the signal glitches in and locks, then the dot breathes while the console loads."""
    c.clear(BG)
    if BOOT and t < LOCK:
        active = [(a, b) for a, b in BOOT if a <= t < b]
        if active:
            a, b = active[0]
            glitch_logo(c, t, 0.6 + 0.4 * math.sin(math.pi * (t - a) / (b - a)))
        elif t > BOOT[0][0]:
            # between bursts: a faint ghost of the logo, flickering
            p = skia.Paint()
            p.setAlphaf(0.08 + 0.06 * (int(t * FPS) % 2))
            c.drawImageRect(LOGO_IMG, skia.Rect(0, 0, W, HH), SAMP, p)
        return
    lt = t - LOCK
    breath = 1.0 + 0.3 * math.sin(lt * 2 * math.pi / 1.6 - math.pi / 2) if lt > 0.25 else 1.0
    R.draw_logo(c, glow=breath)
    # a last small shudder right after it locks
    if BOOT and lt < 0.08:
        c.drawRect(skia.Rect(0, 0, W, HH), paint(R.WHITE, 0.12 * (1 - lt / 0.08)))


R2.s_splash = s_splash

_grng = np.random.default_rng(5)
GRAIN = []
for _ in range(4):
    v = np.clip(128 + _grng.normal(0, 40, (HH * S4K, W * S4K)), 0, 255).astype(np.uint8)
    GRAIN.append(skia.Image.fromarray(np.dstack([v, v, v, np.full_like(v, 255)]),
                                      colorType=skia.ColorType.kRGBA_8888_ColorType))


def grain(c, t, amount=0.022):
    p = skia.Paint()
    p.setAlphaf(amount)
    p.setBlendMode(skia.BlendMode.kOverlay)
    c.drawImageRect(GRAIN[int(t * FPS) % len(GRAIN)], skia.Rect(0, 0, W, HH),
                    skia.SamplingOptions(skia.FilterMode.kNearest), p)


R2.grain = grain
R4.s_main = s_main  # reuse v4's frame flow (splash, streak, close-ups) with the new main scene


def render(t):
    surf = skia.Surface(W * S4K, HH * S4K)
    c = surf.getCanvas()
    c.clear(BLACK)
    c.scale(S4K, S4K)
    R4.draw_frame(c, t)
    return surf


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "frames":
        os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"), exist_ok=True)
        for ts in sys.argv[2:]:
            render(float(ts)).makeImageSnapshot().save(f"{os.path.dirname(os.path.abspath(__file__))}/out/v5_{ts}.png", skia.kPNG)
    elif mode == "video":
        n = int(DUR * FPS)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
                               "-s", f"{W * S4K}x{HH * S4K}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12",
                               "-preset", "veryfast", "-pix_fmt", "yuv420p", sys.argv[2]], stdin=subprocess.PIPE)
        for i in range(n):
            ff.stdin.write(render(i / FPS).makeImageSnapshot().tobytes())
        ff.stdin.close()
        sys.exit(ff.wait())
