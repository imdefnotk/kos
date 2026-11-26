# K.OS startup video

The video Steam plays when it opens on K.OS. Final file (approved 2026-11-26):
`system_files/usr/share/kos/boot/kos-startup.webm`
10 seconds, 3840x2160, 60 fps, VP9 video + Opus audio, about 8.5 MB.

K.OS installs it for every user as Steam's startup movie
(`/usr/libexec/kos-startup-movie`, called by `kos-system-setup` before login and
`kos-firstboot-setup` at login). It never replaces a startup movie the user chose.

## What happens (seconds)

| Time | Picture | Sound |
| --- | --- | --- |
| 0.0 to 0.7 | Signal locks on: the K. flickers in as broken slices with red/cyan split and corruption blocks, then snaps clean | Corruption bursts and skips on every flicker, latch click on the snap |
| 0.7 to 1.1 | Calm hold on the logo, red dot breathing (time for the console to finish loading) | 50 Hz power hum, sparks, low bass bed |
| 1.1 | Thin light streak takes the logo into darkness | Electric arc that skips |
| 1.6, 2.1, 2.6 | Three close-ups of the K with light sweeps | Glitchy sword slashes sweeping across the speakers |
| 3.1 | The Operator emerges in side profile, slow push-in | Dark distorted bass swell, hydraulics, mechanical pulses |
| 4.2 | Its red light flickers on | Arc and corruption burst, then rising noise and ratchet |
| 5.0 to 5.2 | The Operator dissolves, the K forms; the light never moves | Accelerating skip glitch into the reveal |
| 5.2 | K revealed by a light sweep | Huge bass hit, mechanical slam, big slash |
| 5.7 | The light becomes the K.OS dot | K.OS motif: two notes rising (A to D) on a gritty synth |
| 6.7 onward | The dot blinks like a camera recording light; the K fades; the dot blinks alone, then black | Latch click and static, quiet hum, a static tick on each blink |

Timing lives in `timeline3.py` (the `KOS_LONG=1` values). Picture and sound both read it, so changing a time there moves both.

## Files

| File | What it is |
| --- | --- |
| `rebuild.sh` | Builds everything and writes the final WebM into `system_files` |
| `timeline3.py` | All timings (10 s version with `KOS_LONG=1`, older 7 s version without) |
| `render5.py` | The final picture. Uses `render4.py`, `render2.py`, `render.py` for shared parts |
| `render.py` | Logo layout (Space Grotesk Bold, K white #F4F4F5, dot red #E5322D, background #0A0A0C) |
| `render2.py` | K close-ups, light sweeps, vignette, the light streak |
| `render4.py` | The red light (flicker, power-on, recording blink) and the overall frame flow |
| `kos_operator_side.py` | Old code-drawn placeholder Operator (still imported, not shown) |
| `sound_glitch2.py` | The final sound. Builds on `sound_glitch.py`, `sound_cyber.py`, `sound.py` |
| `audio/kos-startup-sound.wav` | Final sound master (48 kHz, 24-bit, -16 LUFS) |
| `upscale.py` | AI upscale of the Operator for 4K (Real-ESRGAN anime model) |
| `make_nolight.py` | Removes the red light painted into the Operator art so the video controls it |
| `fonts/` | Space Grotesk Bold and Medium (SIL Open Font License, see `OFL-SpaceGrotesk.txt`) |
| `timeline.py`, `render.py` (first parts) | Remains of the first (Persona-style) version; `render.py` still provides the logo layout |

The Operator artwork is in `art/operator/` (see its README).

## Rebuild

Needs Python 3 with `numpy scipy pillow skia-python`, and ffmpeg with VP9 and Opus.

```bash
pip install numpy scipy pillow skia-python
bash art/boot/rebuild.sh
```

Quick check of single frames (saved to `art/boot/out/`, which Git ignores):

```bash
KOS_LONG=1 KOS_4K=1 python3 art/boot/render5.py frames 0.3 4.5 7.0
```

## Rules for changes

- Never leave silent gaps or let a sound stop abruptly: it is heard as a glitch. Every sound layer has a short fade-out.
- No pitched beeps or rising whines on the close-ups; the owner found them annoying ("bliips"). Glitches should be noise-based.
- The red light must stay on the exact K.OS dot position from the moment it switches on.
- Keep loudness at -16 LUFS (rebuild.sh does this) so the console never startles anyone at night.
- All sound is synthesized here from scratch, and all artwork is ours. Never add music or sounds from games, trailers or other consoles: K.OS is sold.
