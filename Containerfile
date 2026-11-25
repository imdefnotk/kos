ARG BASE_IMAGE=ghcr.io/ublue-os/bazzite-nvidia-open:stable
FROM ${BASE_IMAGE}

ARG KOS_TARGET=kos-nvidia
ARG KOS_SESSION_MODE=nvidia-desktop

ENV KOS_TARGET=${KOS_TARGET}
ENV KOS_SESSION_MODE=${KOS_SESSION_MODE}

COPY system_files /
COPY build_files /tmp/build_files

RUN chmod +x /tmp/build_files/build.sh && /tmp/build_files/build.sh && rm -rf /tmp/build_files

RUN ostree container commit