#!/usr/bin/env bash
# Rebuild the K.OS startup video from source.
# Output: system_files/usr/share/kos/boot/kos-startup.webm (10 s, 3840x2160, 60 fps, VP9 + Opus)
# Needs: python3 with numpy, scipy, pillow, skia-python; ffmpeg with libvpx-vp9 and libopus.
# Run from anywhere:  bash art/boot/rebuild.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "${HERE}/../.." && pwd)"
OUT="${HERE}/out"
mkdir -p "${OUT}"
export KOS_LONG=1   # 10 second timeline (timeline3.py)
export KOS_4K=1     # draw at 3840x2160

cd "${HERE}"

echo "1/4 Sound (sound_glitch2.py) and loudness to -16 LUFS"
python3 sound_glitch2.py "${OUT}/raw.wav"
STATS=$(ffmpeg -hide_banner -i "${OUT}/raw.wav" -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
LN=$(echo "${STATS}" | python3 -c "import sys,json;d=json.load(sys.stdin);print(f\"measured_I={d['input_i']}:measured_TP={d['input_tp']}:measured_LRA={d['input_lra']}:measured_thresh={d['input_thresh']}:offset={d['target_offset']}\")")
ffmpeg -v error -y -i "${OUT}/raw.wav" -af "loudnorm=I=-16:TP=-1.5:LRA=11:${LN}:linear=true,aresample=48000" \
    -ar 48000 -c:a pcm_s24le "${HERE}/audio/kos-startup-sound.wav"

echo "2/4 Picture (render5.py), 600 frames"
python3 render5.py video "${OUT}/picture.mp4"

echo "3/4 Encode VP9 (slow on small machines)"
ffmpeg -v error -y -i "${OUT}/picture.mp4" -c:v libvpx-vp9 -b:v 0 -crf 20 -row-mt 1 -tile-columns 2 \
    -deadline good -cpu-used 3 -pix_fmt yuv420p -an "${OUT}/picture.webm"

echo "4/4 Add sound"
ffmpeg -v error -y -i "${OUT}/picture.webm" -i "${HERE}/audio/kos-startup-sound.wav" -map 0:v -map 1:a \
    -c:v copy -c:a libopus -b:a 192k -shortest "${REPO}/system_files/usr/share/kos/boot/kos-startup.webm"

echo "Done: ${REPO}/system_files/usr/share/kos/boot/kos-startup.webm"
