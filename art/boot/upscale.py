"""Upscale the Operator cut-out for 4K with Real-ESRGAN's anime model
(realesr-animevideov3, SRVGGNetCompact, BSD-3 licence). Color goes through the
network; the transparency mask is upscaled separately with Lanczos.
Usage: python3 upscale.py in_rgba.png out_rgba.png model.pth [final_scale]
"""
import sys
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image


class SRVGGNetCompact(nn.Module):
    def __init__(self, num_feat=64, num_conv=16, upscale=4):
        super().__init__()
        self.upscale = upscale
        body = [nn.Conv2d(3, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        for _ in range(num_conv):
            body += [nn.Conv2d(num_feat, num_feat, 3, 1, 1), nn.PReLU(num_parameters=num_feat)]
        body += [nn.Conv2d(num_feat, 3 * upscale * upscale, 3, 1, 1)]
        self.body = nn.ModuleList(body)
        self.upsampler = nn.PixelShuffle(upscale)

    def forward(self, x):
        out = x
        for m in self.body:
            out = m(out)
        out = self.upsampler(out)
        return out + F.interpolate(x, scale_factor=self.upscale, mode="nearest")


def run(rgb, net, tile=384, pad=12, s=4):
    h, w, _ = rgb.shape
    out = np.zeros((h * s, w * s, 3), np.float32)
    x = torch.from_numpy(rgb.transpose(2, 0, 1)).float().unsqueeze(0) / 255.0
    with torch.no_grad():
        for y0 in range(0, h, tile):
            for x0 in range(0, w, tile):
                y1, x1 = min(y0 + tile, h), min(x0 + tile, w)
                py0, px0 = max(0, y0 - pad), max(0, x0 - pad)
                py1, px1 = min(h, y1 + pad), min(w, x1 + pad)
                o = net(x[:, :, py0:py1, px0:px1])[0].clamp(0, 1).numpy().transpose(1, 2, 0)
                oy, ox = (y0 - py0) * s, (x0 - px0) * s
                out[y0 * s:y1 * s, x0 * s:x1 * s] = o[oy:oy + (y1 - y0) * s, ox:ox + (x1 - x0) * s]
    return (out * 255 + 0.5).astype(np.uint8)


if __name__ == "__main__":
    src, dst, model = sys.argv[1], sys.argv[2], sys.argv[3]
    final = float(sys.argv[4]) if len(sys.argv) > 4 else 2.0
    torch.set_num_threads(2)
    net = SRVGGNetCompact()
    net.load_state_dict(torch.load(model, map_location="cpu")["params"])
    net.eval()
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im)
    rgb = (a[..., :3].astype(np.float32) * (a[..., 3:] / 255.0)).astype(np.uint8)  # on black
    up = Image.fromarray(run(rgb, net))
    W, H = int(im.width * final), int(im.height * final)
    up = up.resize((W, H), Image.LANCZOS)
    alpha = im.getchannel("A").resize((W, H), Image.LANCZOS)
    up.putalpha(alpha)
    up.save(dst)
    print("saved", dst, up.size)
