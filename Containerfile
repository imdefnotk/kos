# K.OS image recipe.
# The GitHub Actions workflow builds this file once per K.OS flavor:
#   kos-nvidia       (base: bazzite-nvidia-open) boots into the K.OS session (K.OS Home)
#   kos-amd          (base: bazzite, see COPY-INTO-workflows) boots into the K.OS session
#   kos-nvidia-deck  (base: bazzite-deck-nvidia) old Steam Gaming Mode test image

ARG BASE_IMAGE=ghcr.io/ublue-os/bazzite-nvidia-open:stable

# Small helper stage that only holds the build script, so it never ends up inside the final image
FROM scratch AS ctx
COPY build_files /

FROM ${BASE_IMAGE}

ARG KOS_TARGET=kos-nvidia
ARG KOS_SESSION_MODE=nvidia-desktop

# Copy every K.OS file into the image (system_files/usr/bin/x ends up at /usr/bin/x)
COPY system_files /

# K.OS Home launcher (screens + helper). Private demo logos are never in GitHub, so they never get here.
COPY launcher /usr/share/kos/home

# K.OS Home shell: the full screen K.OS Home program (Electron app, see shell/main.js)
COPY shell /usr/share/kos/shell

# K.OS Console window rules (KWin script). Kept at the top of the repo because the
# real folder is very deep; this replaces any older copy from system_files.
COPY kwin/kos-console/metadata.json /usr/share/kwin/scripts/kos-console/metadata.json
COPY kwin/kos-console/main.js /usr/share/kwin/scripts/kos-console/contents/code/main.js

RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=tmpfs,dst=/tmp \
    KOS_TARGET="${KOS_TARGET}" KOS_SESSION_MODE="${KOS_SESSION_MODE}" bash /ctx/build.sh

# Final safety check that the image is a valid bootable image
RUN bootc container lint
