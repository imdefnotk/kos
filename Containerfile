# K.OS image recipe.
# The GitHub Actions workflow builds this file twice:
#   kos-nvidia  (base: bazzite-nvidia-open, KDE desktop that opens Steam Big Picture)
#   kos-amd     (base: bazzite-deck, native Steam Gaming Mode)

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

RUN --mount=type=bind,from=ctx,source=/,target=/ctx \
    --mount=type=tmpfs,dst=/tmp \
    KOS_TARGET="${KOS_TARGET}" KOS_SESSION_MODE="${KOS_SESSION_MODE}" bash /ctx/build.sh

# Final safety check that the image is a valid bootable image
RUN bootc container lint
