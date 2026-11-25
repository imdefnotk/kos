#!/usr/bin/env bash
set -ouex pipefail

echo "Building K.OS target: ${KOS_TARGET} (${KOS_SESSION_MODE})"

# Ensure executable permissions on K.OS binaries and helpers
chmod +x /usr/bin/kos-*
chmod +x /usr/libexec/kos-*

# Install python3-vdf or ensure python3 is present for Steam shortcuts injection
rpm-ostree install python3 || true

# Hide GRUB menu for instant console boot
if [ -f /etc/default/grub ]; then
    sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=0/' /etc/default/grub
    if ! grep -q "^GRUB_TIMEOUT_STYLE=" /etc/default/grub; then
        echo "GRUB_TIMEOUT_STYLE=hidden" >> /etc/default/grub
    fi
fi

# Set OS branding identity
if [ -f /usr/lib/os-release ]; then
    sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="K.OS (Konsol OS)"/' /usr/lib/os-release
    sed -i 's/^NAME=.*/NAME="K.OS"/' /usr/lib/os-release
fi

# Enable first-boot user setup service globally
systemctl enable --global kos-firstboot.service

# Regenerate initramfs to pick up boot config changes
QUALIFIED_KERNEL="$(rpm -qa | grep -P 'kernel-(|'"$KERNEL_FLAVOR"'-)(\d+\.\d+\.\d+)' | sed -E 's/kernel-(|'"$KERNEL_FLAVOR"'-)//' | head -n 1)"
if [ -n "${QUALIFIED_KERNEL}" ]; then
    /usr/bin/dracut --no-hostonly --kver "${QUALIFIED_KERNEL}" --reproducible -v --add ostree -f "/lib/modules/${QUALIFIED_KERNEL}/initramfs.img"
fi