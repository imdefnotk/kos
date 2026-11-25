# K.OS (Konsol OS)

A console-style operating system built on [Bazzite](https://bazzite.gg). It boots straight into Steam Big Picture, has full-screen tiles for Xbox Game Pass (cloud), Netflix, HBO Max and a web browser, and switches to Windows 11 and back with one click.

## Images

| Image | Base | For |
| --- | --- | --- |
| `ghcr.io/imdefnotk/kos-nvidia:stable` | `bazzite-nvidia-open` | NVIDIA PCs (KDE that opens Steam Big Picture) |
| `ghcr.io/imdefnotk/kos-amd:stable` | `bazzite-deck` | AMD Radeon PCs (Steam Gaming Mode) |

Images rebuild automatically every day and after every change to `main`. Each build is also kept under a dated tag (`stable-YYYYMMDD`) for rollback.

## Switch an existing Bazzite install to K.OS

```bash
rpm-ostree rebase ostree-unverified-registry:ghcr.io/imdefnotk/kos-nvidia:stable
systemctl reboot
```

## What is in the repo

| Path | What it does |
| --- | --- |
| `Containerfile`, `build_files/build.sh` | Image recipe and build steps |
| `system_files/usr/bin/kos-session` | Opens Steam Big Picture at login (NVIDIA) |
| `system_files/usr/bin/kos-webapp` | Full-screen Google Chrome tiles |
| `system_files/usr/bin/kos-boot-windows` | "Switch to Windows" tile (asks first, then one-time restart into Windows) |
| `system_files/usr/libexec/kos-steam-shortcuts` | Adds the K.OS tiles to Steam |
| `system_files/usr/libexec/kos-system-setup` | Automatic login and Windows-friendly clock |
| `system_files/usr/libexec/kos-flatpak-setup` | Installs Google Chrome, retries until online |
| `system_files/usr/share/kos/artwork/` | K.OS tile pictures (made by `art/make_tile_art.py`) |
| `launcher/` | The K.OS home screen app (phase 1 prototype). See `launcher/README.md` |
| `windows/kos-windows-setup.ps1` | Windows side: "Return to K.OS" shortcut, Fast Startup off |

Based on the [Universal Blue image template](https://github.com/ublue-os/image-template).
