# K.OS Home launcher (phase 2)

This is the K.OS home screen as a real app you can drive with a controller. It is built with web technology (HTML, CSS and JavaScript), so the same code runs in Chrome on Windows today and on K.OS.

**New in phase 2:** a small helper program, `kos-home-helper.py`, runs next to the launcher. It reads your installed Steam games, play time and cover art straight from Steam's folder, and starts a game when you press Oyna. Without the helper, the launcher still opens, with the sample games.

## How to open it

**Full screen, like a console (recommended):** double-click `K.OS Launcher.cmd` in this folder. It starts the helper (if Python is installed), then opens the launcher full screen in Google Chrome (or Microsoft Edge if Chrome is missing). Close it with **Alt+F4**. The helper stops by itself about 5 minutes after you close the launcher.

**Real Steam games on Windows need Python (one time setup):**
1. Open the Start menu, type `terminal`, open **Terminal**.
2. Paste this and press Enter: `winget install -e --id Python.Python.3.13`
3. When it finishes, close Terminal and double-click `K.OS Launcher.cmd` again.

To check it worked: the Oyunlar page says "Steam'deki yüklü oyunların: N" and shows your games with their Steam covers. If it says "Örnek kütüphane", the helper is not running (see the log file `%TEMP%\kos-home-helper.log`).

Note: the first time you open it through the helper, your launcher settings (theme color, sound) start fresh once, because the launcher now runs from a different address.

**On K.OS:** K.OS Home is the whole interface. The K.OS session starts it at power on (after the startup video) and opens it again if it ever closes. It runs in the K.OS Home shell (`shell/` in the repo), not in a browser. To see which games the helper finds without opening anything: `kos-home --list` (in Konsole on the developer desktop).

**Use Chrome or Edge, not Brave.** Brave blocks controllers by default for privacy, so the controller does nothing there.

**In a normal window:** double-click `index.html`. Good for quick checks. In this mode, Chrome may block Netflix and the other apps from opening when you press A on a controller. The `.cmd` file avoids that.

Works without internet. Only the app tiles (Netflix, HBO Max, Xbox Bulut Oyun, İnternet) and Store installs need a connection, and they show a Turkish message when you are offline.

## Controls

| Action | Controller | Keyboard |
| --- | --- | --- |
| Move | D-pad or left stick | Arrow keys |
| Select | A | Enter |
| Back | B | Escape or Backspace |
| Previous / next section | LB / RB | Q / E |
| Power menu | Menu (Start) button | P |

A mouse also works: click anything to select it.

If the controller does nothing at first, press any button once while the launcher window is in front. Chrome only starts reading a controller after its first button press. The controller icon at the top right turns bright when it is connected.

**Controller still not working?** Press **F2** on the keyboard. A test panel shows every controller Chrome can see and which buttons it receives. Press buttons on the controller and watch the panel. Press F2 again to close it.

## Game artwork

Real games use the pictures Steam already keeps on the drive: the tall cover on the tiles, and the wide "library hero" picture behind the Home screen when a game is selected, like on a PS5. Pictures you picked yourself in Steam (custom artwork) win. If Steam has no copy on the drive, the helper asks Steam's web servers instead (needs internet). Games without any picture keep the K.OS tile design. Turn the background picture off in **Ayarlar, Ekran, Oyun görselleri**.

The Home row shows your 5 most recently played games first, then the apps.

For offline demos, put a picture named `<game id>-hero.jpg` in `demo-art`. It is used before the Steam artwork.

## Sound

The launcher plays calm background music made live by the launcher itself (original, no music files, a different key for each theme color) plus soft sounds when you move, select and go back. Music fades out when a game or app opens and comes back when you return.

Change it in **Ayarlar, Ses**: music on/off, music level, navigation sounds on/off.

To use your own music, put a file named `ambient.mp3` in the `audio` folder. It loops instead of the generated music.

## What is real and what is demo

Real now:
- All five sections, controller navigation, the raised active tab, the moving background.
- Theme color (Ayarlar, Ekran, Tema rengi), moving background on/off and the other Ekran switches. Your choices are remembered.
- Your installed Steam games (with the helper): covers, background art, play time, last played, size, and Oyna starts the game through Steam. When you come back from a game, the order updates.
- App tiles open the real websites in their own window. On K.OS they open as K.OS apps (full screen Chrome, Steam Big Picture, Windows'a Geç asks first, then restarts into Windows).
- Offline detection, clock, controller detection.

Demo for now:
- Without the helper, the games are made-up examples and Oyna shows a launch screen only.
- Oyun Sayfası (game page) and the "..." button come in a later step.
- Store installs are a pretend progress bar.
- Power buttons (sleep, restart, off) show a message instead of acting. Windows'a Geç already works on K.OS.
- Settings pages other than Ekran list what they will hold. They connect to the system in phase 4.

## Real logos for demos

See `demo-art/README.txt`. Logos you put there show on the tiles but are never uploaded to GitHub.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The page structure |
| `css/kos.css` | All the looks |
| `css/fonts.css`, `fonts/` | Inter and Space Grotesk, stored locally with Turkish characters (SIL Open Font License) |
| `js/data.js` | Games, apps, store items and settings lists |
| `js/app.js` | Navigation, controller, theme and everything that moves |
| `kos-home-helper.py` | The helper: Steam library, pictures, starting games and K.OS apps. Only reachable from this computer (127.0.0.1:47800) |
| `K.OS Launcher.cmd` | Windows starter: helper + full-screen mode |
| `/usr/bin/kos-home` (in the K.OS image) | K.OS starter: helper + K.OS Home shell (Electron, full screen, no browser parts) |
| `demo-art/` | Private logo folder (ignored by Git) |
