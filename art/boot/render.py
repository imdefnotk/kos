"""K.OS startup video renderer (original artwork, Persona-style energy).
Usage:
  python3 render.py frames 0.3 1.0 3.7 ...   -> PNG stills for checking
  python3 render.py video out.mkv            -> raw RGBA piped to ffmpeg
"""
import math
import os
import subprocess
import sys
import numpy as np
import skia
from timeline import HITS as H, DUR, FPS

W, HH = 1920, 1080
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts") + os.sep
BOLD = skia.Typeface.MakeFromFile(FONT_DIR + "SpaceGrotesk-Bold.ttf")
MED = skia.Typeface.MakeFromFile(FONT_DIR + "SpaceGrotesk-Medium.ttf")

BG = skia.Color(0x0A, 0x0A, 0x0C)
WHITE = skia.Color(0xF4, 0xF4, 0xF5)
RED = skia.Color(0xE5, 0x32, 0x2D)
BLACK = skia.Color(0, 0, 0)
GREY = skia.Color(0x71, 0x71, 0x7A)


# ---------- easing ----------
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, a, b):
    return clamp((t - a) / (b - a))


def out_cubic(p):
    return 1 - (1 - p) ** 3


def in_cubic(p):
    return p ** 3


def in_out(p):
    return 4 * p ** 3 if p < 0.5 else 1 - (-2 * p + 2) ** 3 / 2


def out_back(p, s=1.9):
    p -= 1
    return 1 + (s + 1) * p ** 3 + s * p ** 2


# ---------- paint helpers ----------
def paint(color, alpha=1.0, stroke=0.0, aa=True):
    p = skia.Paint(Color=color, AntiAlias=aa)
    p.setAlphaf(alpha)
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        p.setStrokeJoin(skia.Paint.kMiter_Join)
    return p


def text_width(text, size, tracking, tf=BOLD):
    f = skia.Font(tf, size)
    ws = f.getWidths(f.textToGlyphs(text))
    return sum(ws) + tracking * size * (len(text) - 1), ws, f


def draw_text(c, text, x, y, size, p, tracking=-0.03, align="center", tf=BOLD):
    total, ws, f = text_width(text, size, tracking, tf)
    if align == "center":
        x -= total / 2
    for ch, w in zip(text, ws):
        c.drawString(ch, x, y, f, p)
        x += w + tracking * size


def cap_h(size, tf=BOLD):
    return skia.Font(tf, size).getMetrics().fCapHeight


# ---------- logo layout (matches the K.OS wallpaper) ----------
K_SIZE = 420
K_CAP = cap_h(K_SIZE)
K_BASE = 649.0
K_W = skia.Font(BOLD, K_SIZE).measureText("K") - 0.05 * K_SIZE
DOT_D, DOT_GAP = 62.0, 46.0
GROUP_W = K_W + DOT_GAP + DOT_D
K_X = W / 2 - GROUP_W / 2
DOT_C = (K_X + K_W + DOT_GAP + DOT_D / 2, K_BASE - DOT_D / 2)
LOGO_C = (W / 2, K_BASE - K_CAP / 2)


def draw_glow(c, x, y, r, strength):
    if strength <= 0:
        return
    p = paint(RED, clamp(0.45 * strength, 0, 1))
    p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 34 + 14 * strength))
    c.drawCircle(x, y, r * (1.6 + 0.5 * strength), p)


def draw_logo(c, k_alpha=1.0, dot_on=1.0, dot_dy=0.0, glow=1.0, shadow=(0, 0), stroke=0.0, dot_scale=1.0):
    f = skia.Font(BOLD, K_SIZE)
    if shadow != (0, 0):
        c.drawString("K", K_X + shadow[0], K_BASE + shadow[1], f, paint(RED, k_alpha))
    if stroke:
        c.drawString("K", K_X, K_BASE, f, paint(BLACK, k_alpha, stroke))
    c.drawString("K", K_X, K_BASE, f, paint(WHITE, k_alpha))
    if dot_on > 0:
        x, y = DOT_C[0], DOT_C[1] + dot_dy
        draw_glow(c, x, y, DOT_D / 2, glow * dot_on)
        c.drawCircle(x, y, DOT_D / 2 * dot_scale, paint(RED, dot_on))


# ---------- textures ----------
def make_halftone(color):
    surf = skia.Surface(W, HH)
    c = surf.getCanvas()
    c.clear(skia.ColorTRANSPARENT)
    p = paint(color)
    step = 26
    for gy in range(-1, HH // step + 2):
        for gx in range(-1, W // step + 2):
            x = gx * step + (step / 2 if gy % 2 else 0)
            y = gy * step
            g = clamp((x / W) * 0.6 + (1 - y / HH) * 0.6 - 0.2)
            r = 1.2 + 9.5 * g ** 1.4
            c.drawCircle(x, y, r, p)
    return surf.makeImageSnapshot()


HT_BLACK = make_halftone(BLACK)
HT_WHITE = make_halftone(WHITE)


def halftone(c, img, alpha, dx=0.0, dy=0.0):
    p = skia.Paint()
    p.setAlphaf(alpha)
    c.drawImage(img, dx, dy, skia.SamplingOptions(), p)


def jag_path(cx, cy, w, h, seed, amt=0.035):
    r = np.random.default_rng(seed)
    pts = []
    # corners and a few mid-edge notches for a cut-paper look
    base = [(-0.5, -0.5), (0.1, -0.5), (0.5, -0.5), (0.5, 0.05), (0.5, 0.5), (-0.05, 0.5), (-0.5, 0.5), (-0.5, -0.1)]
    for bx, by in base:
        pts.append((cx + bx * w + r.uniform(-amt, amt) * w, cy + by * h + r.uniform(-amt, amt) * h * 1.6))
    path = skia.Path()
    path.moveTo(*pts[0])
    for pt in pts[1:]:
        path.lineTo(*pt)
    path.close()
    return path


def burst_path(cx, cy, r_out, seed, n=16):
    r = np.random.default_rng(seed)
    path = skia.Path()
    for i in range(n * 2):
        a = math.pi * 2 * i / (n * 2) + r.uniform(-0.06, 0.06)
        rr = r_out * (r.uniform(0.85, 1.15) if i % 2 == 0 else r.uniform(0.52, 0.62))
        x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr
        (path.moveTo if i == 0 else path.lineTo)(x, y)
    path.close()
    return path


def speed_lines(c, t, color, alpha, seed):
    r = np.random.default_rng(seed)
    p = paint(color, alpha)
    for i in range(9):
        y0 = r.uniform(-200, HH + 200)
        length = r.uniform(300, 900)
        speed = r.uniform(5000, 9000)
        thick = r.uniform(4, 14)
        x0 = ((r.uniform(0, W + 2000) + t * speed) % (W + 2000)) - 1000
        path = skia.Path()
        path.moveTo(x0, y0)
        path.lineTo(x0 + length, y0 - length * 0.36)
        path.lineTo(x0 + length, y0 - length * 0.36 + thick)
        path.lineTo(x0, y0 + thick)
        path.close()
        c.drawPath(path, p)


# ---------- camera shake ----------
SHAKE = {"t1": 20, "t1b": 10, "t2": 20, "t2b": 10, "m1": 9, "m2": 9, "m3": 9, "K": 28, "dot": 14}


def shake(t):
    dx = dy = 0.0
    for k, amp in SHAKE.items():
        h = H[k]
        if t >= h:
            e = amp * math.exp(-(t - h) * 22)
            dx += e * math.sin((t - h) * 97 + h * 13)
            dy += e * math.cos((t - h) * 83 + h * 7)
    return dx, dy


# ---------- scenes ----------
def scene_splash(c, t):
    c.clear(BG)
    draw_logo(c)


def scene_slash(c, t):
    p = in_out(prog(t, H["slash"] + 0.12, H["t1"] - 0.02))
    c.clear(BG)
    # logo splits along a diagonal through its center
    d = out_cubic(prog(t, H["slash"] + 0.05, H["t1"])) * 140
    ang = math.radians(-28)
    ux, uy = math.cos(ang), math.sin(ang)
    nx, ny = -uy, ux
    cx, cy = LOGO_C[0] + 60, LOGO_C[1]
    for side in (-1, 1):
        c.save()
        half = skia.Path()
        L = 3000
        a = (cx - ux * L, cy - uy * L)
        b = (cx + ux * L, cy + uy * L)
        half.moveTo(*a)
        half.lineTo(*b)
        half.lineTo(b[0] + nx * L * side, b[1] + ny * L * side)
        half.lineTo(a[0] + nx * L * side, a[1] + ny * L * side)
        half.close()
        c.clipPath(half, doAntiAlias=True)
        c.translate(ux * d * side, uy * d * side + side * d * 0.25)
        draw_logo(c)
        c.restore()
    # white cut streak along the split line
    cut = prog(t, H["slash"], H["slash"] + 0.06)
    fade_cut = 1 - prog(t, H["slash"] + 0.06, H["slash"] + 0.2)
    if fade_cut > 0:
        L = 1400 * out_cubic(cut)
        streak = skia.Path()
        th = 10 * fade_cut
        streak.moveTo(cx - ux * L, cy - uy * L - th)
        streak.lineTo(cx + ux * L, cy + uy * L - th)
        streak.lineTo(cx + ux * L, cy + uy * L + th)
        streak.lineTo(cx - ux * L, cy - uy * L + th)
        streak.close()
        c.drawPath(streak, paint(WHITE, fade_cut))
    # red wipe sweeping from the left with a slanted edge
    xb = -700 + p * (W + 1500)
    region = skia.Path()
    region.moveTo(-800, -10)
    region.lineTo(xb + 560, -10)
    region.lineTo(xb, HH + 10)
    region.lineTo(-800, HH + 10)
    region.close()
    c.save()
    c.clipPath(region, doAntiAlias=True)
    c.clear(RED)
    halftone(c, HT_BLACK, 0.32)
    c.restore()
    if p < 1:
        edge = skia.Path()
        edge.moveTo(xb + 560, -10)
        edge.lineTo(xb + 590, -10)
        edge.lineTo(xb + 30, HH + 10)
        edge.lineTo(xb, HH + 10)
        edge.close()
        c.drawPath(edge, paint(WHITE))


def panel_scene(c, t, start, pop, bg, ht, ht_a, lines_col, back_col, panel_col, l1, l1_col, l2, l2_col,
                rot, from_x, back_off, size, seed):
    c.clear(bg)
    halftone(c, ht, ht_a, dx=-(t - start) * 60, dy=(t - start) * 25)
    speed_lines(c, t, lines_col, 0.35, seed)
    zoom = 1 + 0.035 * prog(t, start, start + 0.8)
    slide = out_back(prog(t, start, start + 0.16), 1.4)
    c.save()
    c.translate(W / 2, HH / 2)
    c.scale(zoom, zoom)
    c.rotate(rot)
    c.translate(from_x * (1 - slide), 0)
    c.translate(-W / 2, -HH / 2)
    pw, ph = 1400, 480
    c.save()
    c.translate(back_off[0], back_off[1])
    c.rotate(2.5 * (1 if rot < 0 else -1), W / 2, HH / 2)
    c.drawPath(jag_path(W / 2, HH / 2, pw + 50, ph + 40, seed + 1), paint(back_col))
    c.restore()
    c.drawPath(jag_path(W / 2, HH / 2, pw, ph, seed), paint(panel_col))
    draw_text(c, l1, W / 2, HH / 2 - 38, size, paint(l1_col))
    if t >= pop:
        q = prog(t, pop, pop + 0.09)
        s = 1.6 - 0.6 * out_cubic(q)
        c.save()
        c.translate(W / 2, HH / 2 + 110)
        c.scale(s, s)
        c.translate(-W / 2, -(HH / 2 + 110))
        draw_text(c, l2, W / 2, HH / 2 + 158, size, paint(l2_col, clamp(q * 2.5)))
        c.restore()
    c.restore()


def scene_text1(c, t):
    panel_scene(c, t, H["t1"], H["t1b"], RED, HT_BLACK, 0.33, WHITE, WHITE, BLACK,
                "KONSOL", WHITE, "SADELİĞİ", RED, -7, -1900, (22, 16), 190, 11)


def scene_text2(c, t):
    panel_scene(c, t, H["t2"], H["t2b"], BG, HT_WHITE, 0.10, RED, RED, WHITE,
                "BİLGİSAYAR", BLACK, "KABİLİYETİ", RED, 6, 1900, (-22, 18), 165, 23)


def giant_k(c, t, start, bg, col, rot, cx, cy, size=1500, stroke=0.0, ht=None, ht_a=0.0):
    c.clear(bg)
    if ht is not None:
        halftone(c, ht, ht_a)
    z = 1 + 0.08 * prog(t, start, start + 0.2)
    f = skia.Font(BOLD, size)
    kw = f.measureText("K")
    kc = cap_h(size)
    c.save()
    c.translate(cx, cy)
    c.rotate(rot)
    c.scale(z, z)
    c.drawString("K", -kw / 2, kc / 2, f, paint(col, 1.0, stroke))
    c.restore()


def scene_montage(c, t):
    if t < H["m2"]:
        giant_k(c, t, H["m1"], RED, WHITE, -12, 860, 560, ht=HT_BLACK, ht_a=0.3)
    elif t < H["m3"]:
        c.clear(WHITE)
        stripe = jag_path(W / 2, HH / 2, 2600, 260, 5)
        c.save()
        c.rotate(-18, W / 2, HH / 2)
        c.drawPath(stripe, paint(RED))
        c.restore()
        z = 1 + 0.08 * prog(t, H["m2"], H["m2"] + 0.2)
        f = skia.Font(BOLD, 1350)
        c.save()
        c.translate(1120, 590)
        c.rotate(9)
        c.scale(z, z)
        c.drawString("K", -f.measureText("K") / 2, cap_h(1350) / 2, f, paint(BLACK))
        c.restore()
    elif t < H["m4"]:
        giant_k(c, t, H["m3"], BLACK, RED, -4, W / 2, HH / 2, 1250, stroke=24, ht=HT_WHITE, ht_a=0.12)
    else:
        c.clear(BG)
        p = in_cubic(prog(t, H["m4"], H["burst"]))
        r = 30 + 1250 * p
        for i in range(3):
            rr = r + 60 + i * 70 * (1 - p)
            c.drawCircle(W / 2, HH / 2, rr, paint(WHITE, 0.25 * (1 - i / 3) * (1 - p), 6))
        c.drawCircle(W / 2, HH / 2, r, paint(RED))
        draw_glow(c, W / 2, HH / 2, r, 0.6)


def scene_burst(c, t):
    c.clear(RED)
    halftone(c, HT_BLACK, 0.25)
    e = in_cubic(prog(t, H["burst"], H["K"] - 0.02))
    for side in (-1, 1):
        path = skia.Path()
        if side < 0:
            path.moveTo(-50, -50); path.lineTo(W + 120, -50); path.lineTo(-50, HH + 140)
        else:
            path.moveTo(W + 50, HH + 50); path.lineTo(-120, HH + 50); path.lineTo(W + 50, -140)
        path.close()
        c.save()
        c.translate(side * (1 - e) * W * 0.55, side * (1 - e) * HH * 0.55)
        c.drawPath(path, paint(BLACK))
        c.restore()


def scene_final(c, t):
    c.clear(BG)
    tk, td = H["K"], H["dot"]
    # starburst behind the logo: pops in, then shrinks away
    grow = out_back(prog(t, tk, tk + 0.18), 1.6)
    shrink = 1 - in_cubic(prog(t, td - 0.2, td - 0.02))
    bs = grow * shrink
    if bs > 0.001:
        spin = (t - tk) * 22
        c.save()
        c.translate(LOGO_C[0] + 40, LOGO_C[1])
        c.rotate(spin + 8)
        c.scale(bs * 1.08, bs * 1.08)
        c.drawPath(burst_path(0, 0, 430, 3), paint(WHITE))
        c.restore()
        c.save()
        c.translate(LOGO_C[0] + 40, LOGO_C[1])
        c.rotate(spin)
        c.scale(bs, bs)
        c.drawPath(burst_path(0, 0, 430, 3), paint(RED))
        c.restore()
    # K slams in from big to normal size
    ks = 1 + 1.6 * (1 - out_back(prog(t, tk, tk + 0.16), 1.3))
    settle = in_out(prog(t, td - 0.2, td))
    sh = (16 * (1 - settle), 10 * (1 - settle))
    # dot drops in on the main hit
    dot_on = 1.0 if t >= td else 0.0
    dot_scale = out_back(prog(t, td, td + 0.13), 2.4)
    glow = 1 + 2.6 * math.exp(-(t - td) * 5.5) if t >= td else 0
    c.save()
    c.translate(LOGO_C[0], LOGO_C[1])
    c.scale(ks, ks)
    c.translate(-LOGO_C[0], -LOGO_C[1])
    draw_logo(c, dot_on=dot_on, dot_scale=dot_scale, glow=glow, shadow=sh, stroke=10 * (1 - settle))
    c.restore()
    # power-on ring from the dot
    if t >= td:
        q = out_cubic(prog(t, td, td + 0.7))
        c.drawCircle(DOT_C[0], DOT_C[1], 31 + q * 700, paint(RED, 0.55 * (1 - q), 5 + 10 * (1 - q)))
    # small K.OS under the logo
    a = out_cubic(prog(t, 4.6, 5.1))
    if a > 0:
        draw_text(c, "K.OS", W / 2 + 0.2 * 28, 725 + 18 * (1 - a), 28,
                  paint(GREY, a), tracking=0.4, tf=MED)
    # white flash on the K slam and the dot hit
    fl = 0.0
    if t >= tk:
        fl = max(fl, 0.55 * math.exp(-(t - tk) * 30))
    if t >= td:
        fl = max(fl, 0.5 * math.exp(-(t - td) * 26))
    if fl > 0.01:
        c.drawRect(skia.Rect(0, 0, W, HH), paint(WHITE, fl))


def draw_frame(c, t):
    dx, dy = shake(t)
    c.save()
    c.translate(dx, dy)
    if dx or dy:  # zoom a touch around the center so shaking never shows edges
        c.translate(W / 2, HH / 2)
        c.scale(1.03, 1.03)
        c.translate(-W / 2, -HH / 2)
    if t < H["slash"]:
        scene_splash(c, t)
    elif t < H["t1"]:
        scene_slash(c, t)
    elif t < H["t2"]:
        scene_text1(c, t)
    elif t < H["m1"]:
        scene_text2(c, t)
    elif t < H["burst"]:
        scene_montage(c, t)
    elif t < H["K"]:
        scene_burst(c, t)
    else:
        scene_final(c, t)
    c.restore()
    # fade in from black at the start, fade to black at the end
    fade = max(1 - prog(t, 0.0, 0.25), in_out(prog(t, H["fade"], DUR - 0.05)))
    if fade > 0:
        c.drawRect(skia.Rect(0, 0, W, HH), paint(BLACK, fade))


def render(t):
    surf = skia.Surface(W, HH)
    c = surf.getCanvas()
    c.clear(BLACK)
    # Shake scaling is around the top-left; center it instead
    draw_frame(c, t)
    return surf


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "frames":
        for ts in sys.argv[2:]:
            render(float(ts)).makeImageSnapshot().save(f"{os.path.dirname(os.path.abspath(__file__))}/out/f_{ts}.png", skia.kPNG)
    elif mode == "video":
        out = sys.argv[2]
        n = int(DUR * FPS)
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
                               "-s", f"{W}x{HH}", "-r", str(FPS), "-i", "-",
                               "-c:v", "libx264", "-crf", "10", "-preset", "veryfast", "-pix_fmt", "yuv420p", out],
                              stdin=subprocess.PIPE)
        for i in range(n):
            img = render(i / FPS).makeImageSnapshot()
            ff.stdin.write(img.tobytes())
        ff.stdin.close()
        sys.exit(ff.wait())
    elif mode == "still":
        render(float(sys.argv[2])).makeImageSnapshot().save(sys.argv[3], skia.kPNG)
