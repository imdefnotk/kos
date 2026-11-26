"""K.OS startup video v2: cinematic, calm but striking. Logo only, ends on a
blinking red "recording" light. Timed to the same music grid (timeline.py).
"""
import math
import os
import subprocess
import sys
import numpy as np
import skia
import render as R
from render import (W, HH, BOLD, MED, BG, WHITE, RED, BLACK, GREY, clamp, prog, out_cubic, in_cubic,
                    in_out, out_back, paint, draw_text, K_SIZE, K_BASE, K_X, DOT_C, DOT_D, LOGO_C)
from timeline import HITS as H, DUR, FPS

# ---------- K outline as a path ----------
_f = skia.Font(BOLD, 1000)
K_GLYPH = _f.textToGlyphs("K")[0]
K_PATH_1000 = _f.getPath(K_GLYPH)  # baseline at y=0, size 1000
K_CAP_1000 = _f.getMetrics().fCapHeight
K_ADV_1000 = _f.measureText("K")


def k_path(size, x, base_y):
    m = skia.Matrix()
    m.setScale(size / 1000, size / 1000)
    m.postTranslate(x, base_y)
    p = skia.Path(K_PATH_1000)
    p.transform(m)
    return p


# ---------- film look ----------
rng = np.random.default_rng(3)
GRAIN = []
for _ in range(6):
    n = rng.normal(0, 1, (HH // 2, W // 2))
    v = np.clip(128 + n * 60, 0, 255).astype(np.uint8)
    a = np.full_like(v, 255)
    rgba = np.dstack([v, v, v, a])
    GRAIN.append(skia.Image.fromarray(rgba, colorType=skia.ColorType.kRGBA_8888_ColorType))


def grain(c, t, amount=0.045):
    img = GRAIN[int(t * FPS) % len(GRAIN)]
    p = skia.Paint()
    p.setAlphaf(amount)
    p.setBlendMode(skia.BlendMode.kOverlay)
    c.drawImageRect(img, skia.Rect(0, 0, W, HH), skia.SamplingOptions(skia.FilterMode.kLinear), p)


def vignette(c, strength=0.65):
    shader = skia.GradientShader.MakeRadial(
        (W / 2, HH / 2), W * 0.62, [skia.Color4f(0, 0, 0, 0).toColor(), skia.Color4f(0, 0, 0, strength).toColor()],
        [0.45, 1.0])
    p = skia.Paint()
    p.setShader(shader)
    c.drawRect(skia.Rect(0, 0, W, HH), p)


def glow_circle(c, x, y, r, color, alpha, blur):
    p = paint(color, clamp(alpha))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    c.drawCircle(x, y, r, p)


def lit_k(c, path, base_col, sweep_pos, sweep_angle, sweep_width, sweep_alpha=1.0, rim=None):
    """Draw a K lit by a moving soft light band, clipped to the letter."""
    c.drawPath(path, paint(base_col))
    c.save()
    c.clipPath(path, doAntiAlias=True)
    c.translate(sweep_pos[0], sweep_pos[1])
    c.rotate(sweep_angle)
    cols = [skia.Color4f(1, 1, 1, 0).toColor(), skia.Color4f(0.96, 0.96, 0.97, sweep_alpha).toColor(),
            skia.Color4f(1, 1, 1, 0).toColor()]
    sh = skia.GradientShader.MakeLinear([(-sweep_width, 0), (sweep_width, 0)], cols)
    p = skia.Paint(AntiAlias=True)
    p.setShader(sh)
    c.drawRect(skia.Rect(-sweep_width, -4000, sweep_width, 4000), p)
    c.restore()
    if rim:
        rp = paint(rim[0], rim[1], rim[2])
        rp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, rim[3]))
        c.drawPath(path, rp)


def macro_shot(c, t, start, end, size, kx, kbase, rot, sweep_from, sweep_to, angle, base=0x24):
    """Extreme close-up of the K with a light sweep and a slow push-in."""
    c.clear(BG)
    p = prog(t, start, end)
    z = 1 + 0.07 * p
    c.save()
    c.translate(W / 2, HH / 2)
    c.scale(z, z)
    c.rotate(rot)
    c.translate(-W / 2, -HH / 2)
    path = k_path(size, kx, kbase)
    sx = sweep_from[0] + (sweep_to[0] - sweep_from[0]) * in_out(p)
    sy = sweep_from[1] + (sweep_to[1] - sweep_from[1]) * in_out(p)
    lit_k(c, path, skia.Color(base, base, base + 3), (sx, sy), angle, size * 0.16, 0.95,
          rim=(RED, 0.35, 3, 6))
    c.restore()
    # quick fade in at each cut so cuts feel deliberate, not cartoony
    a = 1 - prog(t, start, start + 0.06)
    if a > 0:
        c.drawRect(skia.Rect(0, 0, W, HH), paint(BLACK, a * 0.8))


# ---------- scenes ----------
def s_splash(c, t):
    c.clear(BG)
    R.draw_logo(c)


def s_streak(c, t):
    """A thin anamorphic light streak passes and takes the logo into darkness."""
    c.clear(BG)
    p = in_out(prog(t, H["slash"], H["t1"] - 0.02))
    R.draw_logo(c, k_alpha=1 - p, dot_on=1 - p, glow=1 - p)
    x = -600 + (W + 1200) * p
    y = DOT_C[1]
    glow_circle(c, x, y, 40, RED, 0.5 * (1 - abs(p - 0.5) * 1.4), 50)
    for w_, a, col, blur in ((1400, 0.9, RED, 6), (900, 1.0, WHITE, 1.5)):
        sp = paint(col, a)
        sp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
        c.drawRect(skia.Rect(x - w_ / 2, y - 2, x + w_ / 2, y + 2), sp)


def s_macros(c, t):
    if t < H["t1b"]:   # upper arm of the K
        macro_shot(c, t, H["t1"], H["t1b"], 2600, 120, 1780, -8, (-300, 0), (1900, 0), 25)
    elif t < H["t2"]:  # stem and joint
        macro_shot(c, t, H["t1b"], H["t2"], 3200, -260, 2350, 0, (0, -300), (0, 1300), 90)
    elif t < H["t2b"]:  # lower leg
        macro_shot(c, t, H["t2"], H["t2b"], 2600, -620, 1150, 7, (1900, 0), (-200, 0), -30)
    else:              # full K in silhouette with a red rim light from behind
        c.clear(BG)
        p = prog(t, H["t2b"], H["m1"])
        z = 1.18 - 0.08 * out_cubic(p)
        c.save()
        c.translate(LOGO_C[0], LOGO_C[1])
        c.scale(z, z)
        c.translate(-LOGO_C[0], -LOGO_C[1])
        path = k_path(K_SIZE, K_X, K_BASE)
        glow_circle(c, LOGO_C[0] - 40, LOGO_C[1], 260, RED, 0.25 + 0.25 * p, 120)
        rp = paint(RED, 0.9, 4)
        rp.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 4))
        c.drawPath(path, rp)
        c.drawPath(path, paint(skia.Color(0x08, 0x08, 0x0A)))
        c.restore()
        a = 1 - prog(t, H["t2b"], H["t2b"] + 0.06)
        if a > 0:
            c.drawRect(skia.Rect(0, 0, W, HH), paint(BLACK, a * 0.8))


def s_quick(c, t):
    if t < H["m2"]:    # out of focus red light
        c.clear(BG)
        glow_circle(c, 1180, 470, 160, RED, 0.85, 70)
        glow_circle(c, 1180, 470, 70, skia.Color(0xFF, 0x7A, 0x70), 0.5, 40)
    elif t < H["m3"]:  # razor edge of the K
        macro_shot(c, t, H["m2"], H["m3"], 4200, -900, 3000, -14, (600, 0), (1500, 0), 20, base=0x22)
    elif t < H["m4"]:  # light comes into focus
        c.clear(BG)
        glow_circle(c, 820, 600, 90, RED, 0.9, 30)
        c.drawCircle(820, 600, 46, paint(RED, 0.9))
    else:              # darkness, a red light gathers (riser)
        c.clear(BG)
        p = in_cubic(prog(t, H["m4"], H["burst"]))
        glow_circle(c, DOT_C[0], DOT_C[1], 30 + 220 * p, RED, 0.25 + 0.6 * p, 30 + 120 * p)


def s_collapse(c, t):
    """The gathered light snaps down to a point, then darkness."""
    c.clear(BG)
    p = in_cubic(prog(t, H["burst"], H["K"] - 0.04))
    r = 250 * (1 - p) + 2
    glow_circle(c, DOT_C[0], DOT_C[1], r, RED, 0.85 * (1 - p) + 0.15, 40 * (1 - p) + 4)


DOT_FLICKER_ON = [(0.0, 0.03), (0.06, 0.085), (0.11, 9.0)]  # power-on stutter after the hit


def tally(t):
    """Brightness of the red dot: power-on stutter, steady, then a 'recording' blink."""
    td = H["dot"]
    if t < td:
        return 0.0
    lt = t - td
    if lt < 1.0:
        return 1.0 if any(a <= lt < b for a, b in DOT_FLICKER_ON) else 0.0
    # recording blink: on 0.6 s, off 0.4 s, each turn-on with a tiny flicker
    cyc = (lt - 1.0) % 1.0
    if cyc < 0.6:
        return 0.55 if cyc < 0.035 else 1.0
    return 0.0


def s_final(c, t):
    c.clear(BG)
    tk, td = H["K"], H["dot"]
    # K revealed by a vertical light sweep, settling from a slight push
    p = prog(t, tk, tk + 0.45)
    z = 1.06 - 0.06 * out_cubic(prog(t, tk, tk + 1.2))
    k_fade = 1 - in_out(prog(t, H["fade"] - 0.3, H["fade"] + 0.45))
    c.save()
    c.translate(LOGO_C[0], LOGO_C[1])
    c.scale(z, z)
    c.translate(-LOGO_C[0], -LOGO_C[1])
    path = k_path(K_SIZE, K_X, K_BASE)
    reveal = out_cubic(prog(t, tk, tk + 0.12))
    base_col = skia.Color4f(0.957 * reveal, 0.957 * reveal, 0.961 * reveal, 1).toColor()
    c.saveLayerAlpha(None, int(255 * k_fade))
    sx = K_X - 300 + 900 * in_out(p)
    lit_k(c, path, base_col, (sx, 0), 12, 120, 0.9 * (1 - prog(t, tk + 0.35, tk + 0.6)))
    c.restore()
    c.restore()
    # the red dot: power-on stutter, then rolling like a camera tally light
    b = tally(t)
    end_fade = 1 - prog(t, DUR - 0.25, DUR - 0.02)
    if t >= td:
        q = out_cubic(prog(t, td, td + 0.9))
        c.drawCircle(DOT_C[0], DOT_C[1], 31 + q * 520, paint(RED, 0.35 * (1 - q), 2 + 6 * (1 - q)))
    if b > 0:
        boost = 1 + 1.6 * math.exp(-(t - td) * 4.5)
        glow_circle(c, DOT_C[0], DOT_C[1], DOT_D / 2 * (1.7 + 0.4 * boost), RED, 0.42 * b * boost * end_fade,
                    36 + 12 * boost)
        c.drawCircle(DOT_C[0], DOT_C[1], DOT_D / 2, paint(RED, b * end_fade))
        # small hot core like a real LED
        glow_circle(c, DOT_C[0] - 6, DOT_C[1] - 6, 8, skia.Color(0xFF, 0x9A, 0x90), 0.5 * b * end_fade, 5)
    else:
        # LED off but still faintly visible, like a real light
        c.drawCircle(DOT_C[0], DOT_C[1], DOT_D / 2, paint(skia.Color(0x3A, 0x10, 0x10), (1 if t >= td else 0) * end_fade))
    # small K.OS under the logo
    a = out_cubic(prog(t, 4.5, 5.1)) * k_fade
    if a > 0:
        draw_text(c, "K.OS", W / 2 + 0.2 * 28, 725 + 14 * (1 - a), 28, paint(GREY, a), tracking=0.4, tf=MED)
    # soft flash when the K is revealed
    if t >= tk:
        fl = 0.22 * math.exp(-(t - tk) * 18)
        if fl > 0.01:
            c.drawRect(skia.Rect(0, 0, W, HH), paint(WHITE, fl))


SHAKE = {"K": 7, "dot": 3}


def draw_frame(c, t):
    dx = dy = 0.0
    for k, amp in SHAKE.items():
        if t >= H[k]:
            e = amp * math.exp(-(t - H[k]) * 20)
            dx += e * math.sin((t - H[k]) * 90)
            dy += e * math.cos((t - H[k]) * 77)
    c.save()
    c.translate(dx, dy)
    if t < H["slash"]:
        s_splash(c, t)
    elif t < H["t1"]:
        s_streak(c, t)
    elif t < H["m1"]:
        s_macros(c, t)
    elif t < H["burst"]:
        s_quick(c, t)
    elif t < H["K"]:
        s_collapse(c, t)
    else:
        s_final(c, t)
    c.restore()
    if t >= H["slash"]:
        vignette(c, 0.55)
        grain(c, t)
    fade_in = 1 - prog(t, 0.0, 0.25)
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
            render(float(ts)).makeImageSnapshot().save(f"{os.path.dirname(os.path.abspath(__file__))}/out/v2_{ts}.png", skia.kPNG)
    elif mode == "video":
        n = int(DUR * FPS)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
                               "-s", f"{W}x{HH}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "10",
                               "-preset", "veryfast", "-pix_fmt", "yuv420p", sys.argv[2]], stdin=subprocess.PIPE)
        for i in range(n):
            ff.stdin.write(render(i / FPS).makeImageSnapshot().tobytes())
        ff.stdin.close()
        sys.exit(ff.wait())
