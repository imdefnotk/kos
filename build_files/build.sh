#!/usr/bin/env bash
# K.OS build script. Runs once inside GitHub Actions while the image is being built.
# It does NOT run on your PC.
set -euxo pipefail

KOS_TARGET="${KOS_TARGET:-kos-nvidia}"
KOS_SESSION_MODE="${KOS_SESSION_MODE:-nvidia-desktop}"

echo "Building K.OS target: ${KOS_TARGET} (${KOS_SESSION_MODE})"

# 0. Extra packages: python3-evdev lets kos-remote turn the controller into a TV remote
dnf5 -y install python3-evdev || dnf -y install python3-evdev
python3 -c "import evdev; from evdev import ff, UInput"
command -v gdbus

# 0b. Electron runs the K.OS Home shell (/usr/share/kos/shell) full screen with no
#     browser parts. Downloaded from Electron's official GitHub releases and checked
#     against its published SHA-256 checksum. To update: change both lines below
#     (checksum from SHASUMS256.txt of that release, file electron-v<version>-linux-x64.zip).
ELECTRON_VERSION="45.5.0"
ELECTRON_SHA256="36b44cd0c3d355ee74557bea2353e4539f96e1a09733a52a052bd093134a6142"
# Libraries Electron needs (already in Bazzite; listed so a base change cannot break it)
dnf5 -y install --skip-unavailable unzip nss atk at-spi2-atk cups-libs libdrm gtk3 \
    mesa-libgbm alsa-lib libxkbcommon libXScrnSaver libXtst
curl -fL --retry 5 --retry-delay 5 -o /tmp/electron.zip \
    "https://github.com/electron/electron/releases/download/v${ELECTRON_VERSION}/electron-v${ELECTRON_VERSION}-linux-x64.zip"
echo "${ELECTRON_SHA256}  /tmp/electron.zip" | sha256sum -c -
rm -rf /usr/lib/kos-electron
install -d -m 0755 /usr/lib/kos-electron
unzip -q /tmp/electron.zip -d /usr/lib/kos-electron
rm -f /tmp/electron.zip
chmod 0755 /usr/lib/kos-electron/electron
# Chromium's sandbox helper must belong to root with the setuid bit (used only
# when the kernel's own sandbox is not available)
chown root:root /usr/lib/kos-electron/chrome-sandbox
chmod 4755 /usr/lib/kos-electron/chrome-sandbox
find /usr/share/kos/shell -type d -exec chmod 0755 {} +
find /usr/share/kos/shell -type f -exec chmod 0644 {} +
if ldd /usr/lib/kos-electron/electron | grep "not found"; then
    echo "Electron is missing the libraries listed above" >&2
    exit 1
fi

# 1. Make every K.OS program runnable (Git on Windows does not keep this setting)
chmod 0755 /usr/bin/kos-* /usr/libexec/kos-*

# 2. Remove placeholder files that only exist so Git keeps empty folders
rm -f /etc/.gitkeep /usr/.gitkeep

# 3. Move the "Switch to Windows" permission rule into the read-only system area,
#    so every update replaces it cleanly
install -d -m 0755 /usr/share/polkit-1/rules.d
mv /etc/polkit-1/rules.d/49-kos-windows-boot.rules /usr/share/polkit-1/rules.d/49-kos-windows-boot.rules
chmod 0644 /usr/share/polkit-1/rules.d/49-kos-windows-boot.rules

# 4. Record which K.OS flavor this is, so scripts on the PC can check it
install -d -m 0755 /usr/share/kos
cat > /usr/share/kos/kos-release << EOF
KOS_TARGET=${KOS_TARGET}
KOS_SESSION_MODE=${KOS_SESSION_MODE}
KOS_BUILD_DATE=$(date -u +%Y-%m-%d)
EOF

# 5. OS name shown in system info screens (the internal ID stays Bazzite so Bazzite tools keep working)
sed -i 's/^PRETTY_NAME=.*/PRETTY_NAME="K.OS (Konsol OS)"/' /usr/lib/os-release
sed -i 's/^NAME=.*/NAME="K.OS"/' /usr/lib/os-release

# 6. Background services that run as the system on every boot:
#    kos-system-setup  = automatic login + Windows-friendly clock
#    kos-flatpak-setup = installs Google Chrome for the web tiles, retries until it succeeds
systemctl enable kos-system-setup.service
systemctl enable kos-flatpak-setup.service
#    kos-input         = K.OS controller layer (Xbox button opens K.OS Home, button layouts)
systemctl enable kos-input.service

# 7. K.OS Home launcher files: readable by everyone, no Windows-only or private demo files
rm -rf /usr/share/kos/home/demo-art "/usr/share/kos/home/K.OS Launcher.cmd"
find /usr/share/kos/home -type d -exec chmod 0755 {} +
find /usr/share/kos/home -type f -exec chmod 0644 {} +
chmod 0755 /usr/share/kos/home/kos-home-helper.py
python3 -m py_compile /usr/share/kos/home/kos-home-helper.py
rm -rf /usr/share/kos/home/__pycache__

# 8. Flavor specific startup
#    K.OS session flavors (kos-nvidia, kos-amd): the login screen starts the
#    "K.OS" session (/usr/share/wayland-sessions/kos.desktop): KWin with only
#    K.OS Home, no desktop. The Plasma desktop stays installed as developer desktop mode.
#    Old Gaming Mode test flavors end in "-deck".
case "${KOS_SESSION_MODE}" in
    *-deck) IS_DECK=1 ;;
    *) IS_DECK=0 ;;
esac
# KWin script files must be readable by everyone
find /usr/share/kwin/scripts/kos-console -type d -exec chmod 0755 {} +
find /usr/share/kwin/scripts/kos-console -type f -exec chmod 0644 {} +
chmod 0644 /usr/share/wayland-sessions/kos.desktop

if [ "${IS_DECK}" = "0" ]; then
    test -f /etc/xdg/autostart/kos-session.desktop
    test -x /usr/bin/kos-start-session
    test -x /usr/libexec/kos-shell
    command -v kwin_wayland
else
    # Gaming Mode test image: Steam Gaming Mode already starts Steam, so no K.OS
    # session and no KDE autostart.
    # The per-user setup runs as a user service instead.
    rm -f /etc/xdg/autostart/kos-session.desktop /usr/share/wayland-sessions/kos.desktop
    systemctl --global enable kos-firstboot.service
fi

# 9. K.OS boot screen (Plymouth theme "kos": the K. logo with a breathing red dot).
#    The boot screen lives inside the early boot files (initramfs), so they are
#    rebuilt here for the image's kernel. If that fails, the build keeps the
#    original boot files (Bazzite's boot screen) instead of failing.
chmod 0755 /usr/share/plymouth/themes/kos
chmod 0644 /usr/share/plymouth/themes/kos/*
if command -v plymouth-set-default-theme >/dev/null 2>&1 && command -v dracut >/dev/null 2>&1; then
    plymouth-set-default-theme kos
    KVER="$(ls /usr/lib/modules | sort -V | tail -n 1)"
    if TMPDIR=/tmp dracut --no-hostonly --kver "${KVER}" --reproducible --add ostree \
            -f "/tmp/initramfs-kos.img"; then
        install -m 0600 /tmp/initramfs-kos.img "/usr/lib/modules/${KVER}/initramfs.img"
        rm -f /tmp/initramfs-kos.img
        echo "K.OS boot screen built into the boot files for ${KVER}"
    else
        echo "WARNING: could not rebuild the boot files, keeping the old boot screen" >&2
    fi
else
    echo "WARNING: plymouth or dracut missing, keeping the old boot screen" >&2
fi

