#!/usr/bin/env bash
# K.OS build script. Runs once inside GitHub Actions while the image is being built.
# It does NOT run on your PC.
set -euxo pipefail

KOS_TARGET="${KOS_TARGET:-kos-nvidia}"
KOS_SESSION_MODE="${KOS_SESSION_MODE:-nvidia-desktop}"

echo "Building K.OS target: ${KOS_TARGET} (${KOS_SESSION_MODE})"

# 0. Extra packages: python3-evdev lets kos-remote turn the controller into a TV remote
dnf5 -y install python3-evdev || dnf -y install python3-evdev
python3 -c "import evdev"

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

# 7. K.OS Home launcher files: readable by everyone, no Windows-only or private demo files
rm -rf /usr/share/kos/home/demo-art "/usr/share/kos/home/K.OS Launcher.cmd"
find /usr/share/kos/home -type d -exec chmod 0755 {} +
find /usr/share/kos/home -type f -exec chmod 0644 {} +
chmod 0755 /usr/share/kos/home/kos-home-helper.py
python3 -m py_compile /usr/share/kos/home/kos-home-helper.py
rm -rf /usr/share/kos/home/__pycache__

# 8. Flavor specific startup
if [ "${KOS_SESSION_MODE}" = "nvidia-desktop" ]; then
    # NVIDIA: KDE starts, then kos-session opens Steam Big Picture
    test -f /etc/xdg/autostart/kos-session.desktop
else
    # AMD: Bazzite Gaming Mode already starts Steam, so no KDE autostart.
    # The per-user setup runs as a user service instead.
    rm -f /etc/xdg/autostart/kos-session.desktop
    systemctl --global enable kos-firstboot.service
fi
