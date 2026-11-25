# K.OS Launcher (phase 1 prototype)

This is the K.OS home screen as a real app you can drive with a controller. It is built with web technology (HTML, CSS and JavaScript), so the same code runs in Chrome on Windows today and on K.OS later.

## How to open it

**Full screen, like a console (recommended):** double-click `K.OS Launcher.cmd` in this folder. It opens the launcher full screen in Google Chrome (or Microsoft Edge if Chrome is missing). Close it with **Alt+F4**.

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

On the Home screen, the selected game's official Steam artwork (its "library hero" picture) fades into the background, like on a PS5. Games need a Steam app id for this, and it needs internet the first time (after that the browser keeps a copy). Games without artwork keep the theme background. Turn it off in **Ayarlar, Ekran, Oyun görselleri**.

For offline demos, put a picture named `<game id>-hero.jpg` in `demo-art`. It is used before the Steam artwork.

## Sound

The launcher plays calm background music made live by the launcher itself (original, no music files, a different key for each theme color) plus soft sounds when you move, select and go back. Music fades out when a game or app opens and comes back when you return.

Change it in **Ayarlar, Ses**: music on/off, music level, navigation sounds on/off.

To use your own music, put a file named `ambient.mp3` in the `audio` folder. It loops instead of the generated music.

## What is real and what is demo

Real now:
- All five sections, controller navigation, the raised active tab, the moving background.
- Theme color (Ayarlar, Ekran, Tema rengi), moving background on/off and the other Ekran switches. Your choices are remembered.
- App tiles open the real websites in their own window.
- Offline detection, clock, controller detection.

Demo for now:
- The games are made-up examples. Pressing Oyna shows a launch screen only. Real games come in phase 2.
- Store installs are a pretend progress bar.
- Power buttons and Windows'a Geç show a message instead of acting.
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
| `K.OS Launcher.cmd` | Windows starter for full-screen mode |
| `demo-art/` | Private logo folder (ignored by Git) |
