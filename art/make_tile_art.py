#!/usr/bin/env python3
"""K.OS tile artwork generator (placeholder design until the final K.OS logo and fonts).

Creates, for every tile, the four images Steam uses:
  portrait.png  600x900   (library grid)
  wide.png      920x430   (Home screen / recent row)
  hero.png      1920x620  (big banner on the tile's own page)
  icon.png      256x256   (small icon)

Output goes to system_files/usr/share/kos/artwork/<key>/
Run:  python3 art/make_tile_art.py [path/to/BoldFont.ttf] [path/to/RegularFont.ttf]

Design rules: our own K.OS look only. No Netflix, HBO, Xbox or Microsoft logos.
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "system_files", "usr", "share", "kos", "artwork")

BOLD = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"
REG = sys.argv[2] if len(sys.argv) > 2 else "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"

BG = (11, 13, 18)
SS = 2  # draw at 2x, then shrink for smooth edges

# key, title, subtitle, accent colour A, accent colour B, symbol
TILES = [
    ("windows", "Windows'a Geç", "Valorant, LoL ve daha fazlası", (64, 120, 255), (20, 40, 110), "swap"),
    ("xcloud", "Xbox Bulut Oyun", "Game Pass oyunlarını bulutta oyna", (40, 200, 120), (10, 70, 45), "cloud"),
    ("netflix", "Netflix", "Film ve diziler", (230, 70, 70), (90, 15, 25), "play"),
    ("hbomax", "HBO Max", "Film ve diziler", (150, 90, 255), (45, 20, 100), "play"),
    ("browser", "İnternet", "Web'de gezin", (40, 190, 230), (10, 60, 90), "globe"),
]


def font(path, size):
    return ImageFont.truetype(path, size * SS)


def gradient(w, h, a, b):
    """Dark base with a soft diagonal glow from colour a fading into colour b, then into the background."""
    img = Image.new("RGB", (w, h), BG)
    glow = Image.new("RGB", (w, h), BG)
    gd = ImageDraw.Draw(glow)
    steps = 60
    for i in range(steps):
        t = i / steps
        r = int(max(w, h) * (1.1 - t))
        col = tuple(int(BG[c] + (a[c] * (1 - t) + b[c] * t - BG[c]) * (0.35 + 0.65 * t)) for c in range(3))
        cx, cy = int(w * 0.85), int(h * 0.15)
        gd.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(w, h) // 12))
    img = Image.blend(img, glow, 0.9)
    # subtle diagonal lines for texture
    d = ImageDraw.Draw(img, "RGBA")
    gap = 28 * SS
    for x in range(-h, w, gap):
        d.line([(x, h), (x + h, 0)], fill=(255, 255, 255, 6), width=SS)
    return img


def draw_symbol(d, kind, cx, cy, s, col):
    """Simple geometric symbols drawn from shapes (our own, not brand logos)."""
    lw = max(2, int(s * 0.09))
    white = (255, 255, 255, 255)
    if kind == "play":
        r = s * 0.5
        d.rounded_rectangle([cx - r, cy - r * 0.72, cx + r, cy + r * 0.72], radius=r * 0.22, outline=white, width=lw)
        t = r * 0.34
        d.polygon([(cx - t * 0.7, cy - t), (cx - t * 0.7, cy + t), (cx + t, cy)], fill=white)
    elif kind == "cloud":
        r = s * 0.2
        for ox, oy, rr in [(-0.22, 0.05, 1.0), (0.05, -0.12, 1.35), (0.3, 0.06, 0.95)]:
            x, y, k = cx + ox * s, cy + oy * s, r * rr
            d.ellipse([x - k, y - k, x + k, y + k], fill=white)
        d.rounded_rectangle([cx - s * 0.42, cy + s * 0.02, cx + s * 0.5, cy + s * 0.25], radius=s * 0.11, fill=white)
        # small gamepad cut-out
        g = s * 0.13
        d.rounded_rectangle([cx - g * 1.6, cy - g * 0.25, cx + g * 1.6, cy + g * 0.95], radius=g * 0.5, fill=col)
        d.ellipse([cx + g * 0.6, cy + g * 0.15, cx + g * 1.0, cy + g * 0.55], fill=white)
        d.rectangle([cx - g * 1.05, cy + g * 0.28, cx - g * 0.45, cy + g * 0.42], fill=white)
        d.rectangle([cx - g * 0.82, cy + g * 0.05, cx - g * 0.68, cy + g * 0.65], fill=white)
    elif kind == "globe":
        r = s * 0.45
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=white, width=lw)
        d.ellipse([cx - r * 0.45, cy - r, cx + r * 0.45, cy + r], outline=white, width=lw)
        d.line([(cx - r, cy), (cx + r, cy)], fill=white, width=lw)
        d.line([(cx, cy - r), (cx, cy + r)], fill=white, width=lw)
        for f in (-0.5, 0.5):
            y = cy + r * f
            half = math.sqrt(max(0.0, 1 - f * f)) * r
            d.line([(cx - half, y), (cx + half, y)], fill=white, width=max(1, lw // 2))
    elif kind == "swap":
        r = s * 0.42
        # two arrows: right on top, left on bottom
        y1, y2 = cy - r * 0.38, cy + r * 0.38
        d.line([(cx - r, y1), (cx + r * 0.6, y1)], fill=white, width=lw)
        d.polygon([(cx + r, y1), (cx + r * 0.55, y1 - r * 0.3), (cx + r * 0.55, y1 + r * 0.3)], fill=white)
        d.line([(cx + r, y2), (cx - r * 0.6, y2)], fill=white, width=lw)
        d.polygon([(cx - r, y2), (cx - r * 0.55, y2 - r * 0.3), (cx - r * 0.55, y2 + r * 0.3)], fill=white)


def wordmark(d, x, y, size, anchor="ls"):
    d.text((x, y), "K.OS", font=font(BOLD, size), fill=(255, 255, 255, 150), anchor=anchor)


def fit_font(d, text, path, size, max_w):
    while size > 10:
        f = font(path, size)
        if d.textlength(text, font=f) <= max_w:
            return f
        size -= 2
    return font(path, size)


def make(key, title, sub, a, b, sym):
    os.makedirs(os.path.join(OUT, key), exist_ok=True)

    # Portrait 600x900
    W, H = 600 * SS, 900 * SS
    img = gradient(W, H, a, b)
    d = ImageDraw.Draw(img, "RGBA")
    draw_symbol(d, sym, W * 0.5, H * 0.38, W * 0.42, b)
    f = fit_font(d, title, BOLD, 64, W * 0.86)
    d.text((W * 0.5, H * 0.68), title, font=f, fill=(255, 255, 255), anchor="mm")
    fs = fit_font(d, sub, REG, 26, W * 0.86)
    d.text((W * 0.5, H * 0.75), sub, font=fs, fill=(255, 255, 255, 190), anchor="mm")
    wordmark(d, W * 0.5, H * 0.94, 26, "mm")
    img.resize((600, 900), Image.LANCZOS).save(os.path.join(OUT, key, "portrait.png"), optimize=True)

    # Wide 920x430
    W, H = 920 * SS, 430 * SS
    img = gradient(W, H, a, b)
    d = ImageDraw.Draw(img, "RGBA")
    draw_symbol(d, sym, W * 0.22, H * 0.5, H * 0.5, b)
    f = fit_font(d, title, BOLD, 70, W * 0.55)
    d.text((W * 0.42, H * 0.47), title, font=f, fill=(255, 255, 255), anchor="ls")
    fs = fit_font(d, sub, REG, 28, W * 0.55)
    d.text((W * 0.42, H * 0.62), sub, font=fs, fill=(255, 255, 255, 190), anchor="ls")
    wordmark(d, W * 0.95, H * 0.9, 24, "rs")
    img.resize((920, 430), Image.LANCZOS).save(os.path.join(OUT, key, "wide.png"), optimize=True)

    # Hero 1920x620 (no text: Steam shows the tile name on top of it)
    W, H = 1920 * SS, 620 * SS
    img = gradient(W, H, a, b)
    d = ImageDraw.Draw(img, "RGBA")
    big = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(big)
    draw_symbol(bd, sym, W * 0.8, H * 0.5, H * 0.9, b)
    alpha = big.getchannel("A").point(lambda v: int(v * 0.18))
    big.putalpha(alpha)
    img.paste(big, (0, 0), big)
    img.resize((1920, 620), Image.LANCZOS).save(os.path.join(OUT, key, "hero.png"), optimize=True)

    # Icon 256x256
    W = 256 * SS
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    base = gradient(W, W, a, b)
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, W - 1], radius=W * 0.22, fill=255)
    img.paste(base, (0, 0), mask)
    d = ImageDraw.Draw(img, "RGBA")
    draw_symbol(d, sym, W * 0.5, W * 0.5, W * 0.62, b)
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, key, "icon.png"), optimize=True)


if __name__ == "__main__":
    for t in TILES:
        make(*t)
    print("Artwork written to", OUT)
