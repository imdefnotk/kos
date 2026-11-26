"""Remove the red light painted into the Operator artwork, so the video can draw
its own light (off, flickering, on) in exactly the same spot.
Usage: python3 make_nolight.py in.png out.png scale
scale = 1 for the 2080x1500 art, 2 for the 4160x3000 (4K) art.
"""
import sys
import numpy as np
from PIL import Image

EYE = (1197.72, 660.75)  # light center in the 2080x1500 art
RADIUS = 48              # area cleaned around it, in 2080x1500 pixels

src, dst, s = sys.argv[1], sys.argv[2], float(sys.argv[3])
a = np.asarray(Image.open(src).convert("RGBA")).astype(np.int16).copy()
yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
d = np.sqrt((yy - EYE[1] * s) ** 2 + (xx - EYE[0] * s) ** 2)
r, g, b = a[..., 0], a[..., 1], a[..., 2]
reddish = (r - np.maximum(g, b)) > 12
w = np.clip((RADIUS * s - d) / (12 * s), 0, 1)
m = (d < RADIUS * s) & reddish
a[..., 0] = np.where(m, (r * (1 - w) + np.maximum(g, b) * w).astype(np.int16), r)
Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA").save(dst)
print("saved", dst, "pixels cleaned:", int(m.sum()))
