"""K.OS startup video v4: the Operator in profile dissolves into the K. logo.
The red light is drawn at the exact K.OS dot position from the moment it
switches on until the end, so it never moves. Timing and sound: timeline3.py.
"""
import math
import os
import subprocess
import sys
import skia
import render as R
import render2 as R2
import kos_operator_side as OS
from render import (W, HH, BG, BLACK, RED, WHITE, GREY, MED, clamp, prog, out_cubic, in_out, out_back, paint,
                    draw_text, DOT_C, DOT_D, K_SIZE, K_X, K_BASE, LOGO_C)
from timeline3 import T, DUR, FPS, BOOT

R2.H.update({"slash": T["streak"], "t1": T["c1"]})
OP_SCALE = 1.35
EYE_R0 = 13 * OP_SCALE


def light(t):
    """(brightness, radius, glow) of the red light at time t."""
    if t < T["eye"]:
        return 0.0, EYE_R0, 1.0
    lt = t - T["eye"]
    if lt < 0.12:
        on = 1.0 if (lt < 0.03 or 0.06 <= lt < 0.09) else 0.0
    else:
        on = 1.0
    grow = out_back(prog(t, T["dot"], T["dot"] + 0.28), 1.6)
    r = EYE_R0 + (DOT_D / 2 - EYE_R0) * grow
    glow = 1.0 + 0.8 * prog(t, T["eye"], T["rush"])
    if t >= T["dot"]:
        glow = 1.0 + 1.6 * math.exp(-(t - T["dot"]) * 4.5)
    if t >= T["roll"]:
        cyc = (t - T["roll"]) % 1.0
        on = (0.55 if cyc < 0.035 else 1.0) if cyc < 0.6 else 0.0
    on *= 1 - prog(t, DUR - 0.25, DUR - 0.02)
    return on, r, glow


def draw_light(c, t):
    on, r, glow = light(t)
    x, y = DOT_C
    if t >= T["dot"]:  # power-on ring when the light becomes the K.OS dot
        q = out_cubic(prog(t, T["dot"], T["dot"] + 0.9))
        c.drawCircle(x, y, r + q * 520, paint(RED, 0.35 * (1 - q), 2 + 6 * (1 - q)))
    if t < T["eye"]:
        return
    if on <= 0:
        c.drawCircle(x, y, r, paint(skia.Color(0x3A, 0x10, 0x10), 1 - prog(t, DUR - 0.25, DUR - 0.02)))
        return
    R2.glow_circle(c, x, y, r * (1.8 + 0.5 * glow), RED, 0.42 * on * glow, 30 + 10 * glow)
    c.drawCircle(x, y, r, paint(RED, on))
    R2.glow_circle(c, x - r * 0.2, y - r * 0.2, r * 0.28, skia.Color(0xFF, 0x9A, 0x90), 0.5 * on, 4)


def s_main(c, t):
    c.clear(BG)
    eye_on = light(t)[0] if t < T["dot"] else 1.0
    after_eye = prog(t, T["eye"], T["rush"])
    dissolve = in_out(prog(t, T["rush"] - 0.05, T["K"] + 0.25))
    # warm red ambience behind the Operator once its light is on
    R2.glow_circle(c, DOT_C[0] - 180, DOT_C[1] - 60, 430, RED, (0.04 + 0.14 * after_eye) * (1 - dissolve), 180)
    # the Operator: emerges, slow push-in around its own light, then dissolves
    op_a = out_cubic(prog(t, T["op"], T["op"] + 0.5)) * (1 - dissolve)
    if op_a > 0.003:
        s = OP_SCALE * (1 + 0.06 * in_out(prog(t, T["op"], T["K"] + 0.25)))
        c.saveLayerAlpha(None, int(255 * op_a))
        c.translate(DOT_C[0], DOT_C[1])
        c.scale(s, s)
        c.translate(-6 * dissolve, 0)
        OS.draw_body(c, white_rim=out_cubic(prog(t, T["op"], T["op"] + 0.7)),
                     red_rim=after_eye * eye_on, gloss=0.2 + 0.5 * prog(t, T["op"], T["rush"]),
                     eye_light=eye_on if t >= T["eye"] else 0.0)
        c.restore()
    # the K arrives where the Operator stood, revealed by a light sweep
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
        path = R2.k_path(K_SIZE, K_X, K_BASE)
        sweep = in_out(prog(t, tk, tk + 0.6))
        R2.lit_k(c, path, R.WHITE, (K_X - 300 + 900 * sweep, 0), 12, 120,
                 0.9 * (1 - prog(t, tk + 0.45, tk + 0.75)))
        c.restore()
        c.restore()
        a = out_cubic(prog(t, 4.5, 5.1)) * k_out
        if a > 0:
            draw_text(c, "K.OS", W / 2 + 0.2 * 28, 725 + 14 * (1 - a), 28, paint(GREY, a), tracking=0.4, tf=MED)
    # the red light, always at the same spot
    draw_light(c, t)


def draw_frame(c, t):
    if t < T["streak"]:
        R2.s_splash(c, t)
    elif t < T["c1"]:
        R2.s_streak(c, t)
    elif t < T["c2"]:
        R2.macro_shot(c, t, T["c1"], T["c2"], 2600, 120, 1780, -8, (-300, 0), (1900, 0), 25)
    elif t < T["c3"]:
        R2.macro_shot(c, t, T["c2"], T["c3"], 3200, -260, 2350, 0, (0, -300), (0, 1300), 90)
    elif t < T["op"]:
        R2.macro_shot(c, t, T["c3"], T["op"], 2600, -620, 1150, 7, (1900, 0), (-200, 0), -30)
    else:
        s_main(c, t)
    if t >= T["streak"]:
        R2.vignette(c, 0.55)
        R2.grain(c, t)
    fade_in = 0.0 if BOOT else 1 - prog(t, 0.0, 0.25)  # the boot glitch replaces the fade
    if fade_in > 0:
        c.drawRect(skia.Rect(0, 0, W, HH), paint(BLACK, fade_in))


def render(t):
    surf = skia.Surface(W, HH)
    c = surf.getCanvas()
    c.clear(BLACK)
    draw_frame(c, t)
    return surf


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "frames":
        for ts in sys.argv[2:]:
            render(float(ts)).makeImageSnapshot().save(f"{os.path.dirname(os.path.abspath(__file__))}/out/v4_{ts}.png", skia.kPNG)
    elif mode == "video":
        n = int(DUR * FPS)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
                               "-s", f"{W}x{HH}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "10",
                               "-preset", "veryfast", "-pix_fmt", "yuv420p", sys.argv[2]], stdin=subprocess.PIPE)
        for i in range(n):
            ff.stdin.write(render(i / FPS).makeImageSnapshot().tobytes())
        ff.stdin.close()
        sys.exit(ff.wait())
