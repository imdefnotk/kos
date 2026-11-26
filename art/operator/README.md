# The Operator (K.OS mascot), version 1

Approved 2026-11-26. A sleek cyberpunk corporate agent: faceless glossy black helmet,
one red light on the visor (the light IS the K.OS dot), tall red-lined collar,
segmented black armor with thin red lines. 2D anime illustration style, bold ink
lines, flat cel shading, red rim light. Side profile facing right.

## Files (each step from the one above)

| File | Size | How it was made |
| --- | --- | --- |
| `operator_v1_canva_original.png` | 1920x1080 | Generated with Canva AI (`generate-image`), exported from a one-page Canva design |
| `operator_v1_expanded.png` | 2080x1500 | Adobe generative expand: 420 px added on top, 160 px on the right (finishes the helmet) |
| `operator_v1_cutout.png` | 2080x1500 | Adobe background removal: transparent PNG, character only |
| `operator_v1_cutout_4k.png` | 4160x3000 | `art/boot/upscale.py` (Real-ESRGAN realesr-animevideov3, BSD-3 licence) |
| `*_nolight.png` | same | `art/boot/make_nolight.py`: the painted red light removed, so the video draws its own |

The red light's center is at (1197.7, 660.7) in the 2080x1500 files (double it for the 4K file).
In the video this point sits exactly on the K.OS dot.

## Generation prompt (Canva)

> 2D anime-style character illustration of an original mascot called the Operator, a sleek elite cyberpunk corporate security agent. Side profile facing right, chest up. Faceless, glossy black tactical helmet with sharp angular panel lines and a dark visor; one single small glowing red light on the visor like a camera recording light. Tall dramatic stand-up collar with deep red inner lining, rising behind the head. Fitted black armored suit with segmented shoulder plates, thin red tech lines and subtle circuitry seams. Cool, menacing, elegant. Bold cel shading, thick expressive black ink linework, flat color blocks, sharp graphic shadows, neon red rim light, stylish dramatic angles. Near-black background. Palette only black, white and red (#E5322D). No text, no logos, no watermark.

## Before selling anything with it

Check Canva's terms for commercial use of AI-generated images on the account's plan
(box art, website, ads). This was not verified when the image was made.

## Upscaler weights

`upscale.py` needs `realesr-animevideov3.pth` (about 2.5 MB, not stored in Git):
https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
python3 art/boot/upscale.py art/operator/operator_v1_cutout.png art/operator/operator_v1_cutout_4k.png realesr-animevideov3.pth 2
python3 art/boot/make_nolight.py art/operator/operator_v1_cutout_4k.png art/operator/operator_v1_cutout_4k_nolight.png 2
```
