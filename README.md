# K.OS (Konsol OS)

A console-style operating system built on [Bazzite](https://bazzite.gg). It boots straight into **K.OS Home**, its own console interface (no desktop, no taskbar, no Alt+Tab), with your games, full-screen apps for Xbox Cloud Gaming, Netflix, HBO Max and a web browser, and one-click switching to Windows 11 and back.

## Images

| Image | Base | For |
| --- | --- | --- |
| `ghcr.io/imdefnotk/kos-nvidia:stable` | `bazzite-nvidia-open` | NVIDIA PCs (K.OS session) |
| `ghcr.io/imdefnotk/kos-amd:stable` | `bazzite` | AMD Radeon PCs (K.OS session) |
| `ghcr.io/imdefnotk/kos-nvidia-deck:stable` | `bazzite-deck-nvidia` | Old Steam Gaming Mode test image |

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
| `system_files/usr/share/wayland-sessions/kos.desktop` | The "K.OS" session the login screen starts automatically |
| `system_files/usr/bin/kos-start-session` | Starts the K.OS session (KWin with nothing but K.OS Home, no shortcuts); developer desktop mode and safety net |
| `system_files/usr/libexec/kos-shell` | Runs inside the K.OS session: setup, Steam in the background, K.OS Home (restarted if it closes) |
| `system_files/usr/bin/kos-home` | Starts the helper and the K.OS Home shell (`--list`, `--quit`, `--here`) |
| `shell/` | K.OS Home shell: Electron app that shows K.OS Home full screen with no browser parts, plays the startup video at power on |
| `kwin/kos-console/` | K.OS window rules: K.OS Home always full screen, games full screen in front, back to K.OS Home when they close, Steam only in Big Picture |
| `system_files/usr/libexec/kos-input` (+ `kos-input.service`) | K.OS controller layer: Xbox button tap = Quick Menu, hold = K.OS Home; Xbox + View = Esc; button layouts per game (keys, mouse, other buttons); rumble passed through |
| `launcher/menu.html`, `css/menu.css`, `js/menu.js` | K.OS Quick Menu (PS5 style) over any game or app: game/app actions, downloads and updates, sound, microphone, controller, internet, screenshot, power |
| `system_files/usr/libexec/kos-shortcuts` | Keyboard shortcuts in the K.OS session: only Alt+Tab, Alt+Shift+Tab, Alt+F4; Plasma's own shortcuts come back on the developer desktop |
| `system_files/usr/bin/kos-session` | Developer Plasma desktop only: refreshes K.OS launchers |
| `system_files/usr/bin/kos-webapp` | Full-screen Google Chrome tiles |
| `system_files/usr/bin/kos-boot-windows` | "Switch to Windows" tile (asks first, then one-time restart into Windows) |
| `system_files/usr/libexec/kos-steam-shortcuts` | Adds the K.OS tiles to Steam |
| `system_files/usr/libexec/kos-system-setup` | Automatic login and Windows-friendly clock |
| `system_files/usr/libexec/kos-flatpak-setup` | Installs Google Chrome, retries until online |
| `system_files/usr/share/kos/artwork/` | K.OS tile pictures (made by `art/make_tile_art.py`) |
| `launcher/` | The K.OS Home screens and helper. See `launcher/README.md` |
| `system_files/usr/share/kos/boot/kos-startup.webm` | The K.OS startup video (10 s, 4K). Plays when K.OS Home first opens after power on (and as Steam's startup movie) |
| `system_files/usr/libexec/kos-startup-movie` | Installs the startup video into each user's Steam (never replaces a user's own) |
| `art/boot/` | Source for the startup video: picture and sound scripts, fonts, sound master. See `art/boot/README.md` |
| `art/operator/` | The Operator mascot artwork at every step (original, expanded, cut out, 4K). See `art/operator/README.md` |
| `windows/kos-windows-setup.ps1` | Windows side: "Return to K.OS" shortcut, Fast Startup off |

Based on the [Universal Blue image template](https://github.com/ublue-os/image-template).
