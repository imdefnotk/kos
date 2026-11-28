// K.OS Home shell.
//
// K.OS Home is not a browser window. This small program (built on Electron,
// the same Chromium engine that Steam's own interface uses) shows the K.OS
// Home screens full screen with no browser parts at all: no address bar, no
// tabs, no browser pop-ups, no browser name. It cannot be closed or zoomed
// from the keyboard. In the K.OS session it is the whole interface.
//
// Started by /usr/bin/kos-home. Options (after the app folder):
//   --kos-url=<address>   K.OS Home address (default http://127.0.0.1:47800/)
//   --kos-intro           play the K.OS startup video first (first start after power on)
// Developer: start with the environment variable KOS_DEV=1 to allow F12
// (developer tools), F5 (reload) and Ctrl+Q (quit).
//
// Quick Menu (PS5 style): a second, see-through window that sits on top of the
// game or app in front. The game keeps running behind it. The controller layer
// (/usr/libexec/kos-input) talks to this program over a small socket in
// $XDG_RUNTIME_DIR/kos-home.sock, one command per line:
//   from kos-input:  menu  (Xbox button tap: open or close the Quick Menu)
//                    home  (Xbox button hold: K.OS Home)
//                    close (close the Quick Menu)
//   to kos-input:    menu-open / menu-closed (while open, the controller drives
//                    only the menu, the game gets nothing)
//                    key <KEY_A+KEY_B> (press keys in the app in front, for
//                    example Shift+Tab for the Steam overlay)
'use strict';

const { app, BrowserWindow, Menu, ipcMain, screen } = require('electron');
const { execFile } = require('child_process');
const fs = require('fs');
const http = require('http');
const net = require('net');
const path = require('path');

function argValue(name, fallback) {
  const prefix = '--' + name + '=';
  const found = process.argv.find((a) => a.startsWith(prefix));
  return found ? found.slice(prefix.length) : fallback;
}

const HOME_URL = argValue('kos-url', 'http://127.0.0.1:47800/');
const INTRO_VIDEO = '/usr/share/kos/boot/kos-startup.webm';
const WANT_INTRO = process.argv.includes('--kos-intro') && fs.existsSync(INTRO_VIDEO);
const DEV = process.env.KOS_DEV === '1';
const INTRO_MAX_MS = 15000; // never wait longer than this for the intro

// Sound may start without a button press (home music, intro video)
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');
// Own settings folder (~/.config/kos-home), separate from any browser
app.setName('K.OS Home');
app.setPath('userData', path.join(app.getPath('appData'), 'kos-home'));

const MENU_TITLE = 'K.OS Hızlı Menü';
const SOCKET = path.join(process.env.XDG_RUNTIME_DIR || '/tmp', 'kos-home.sock');

let win = null;
let menuWin = null;
let menuOpen = false;
let menuShownAt = 0;
let menuReady = false;
const linkClients = new Set();
let quitting = false;
let introDone = !WANT_INTRO;
let helperUp = false;
let homeLoaded = false;
let showingWaiting = false;

function quitNow() {
  quitting = true;
  try { fs.unlinkSync(SOCKET); } catch (e) { /* already gone */ }
  app.exit(0);
}

// kos-home --quit and the session end send SIGTERM. Electron's Chromium part
// handles SIGTERM itself (the handlers below usually never run): it asks every
// window to close, which K.OS Home refuses unless "quitting" is set. Without
// before-quit the first SIGTERM did nothing and only a second one closed K.OS
// Home ("Masaüstüne geç" had to be chosen twice).
app.on('before-quit', () => { quitting = true; });
process.on('SIGTERM', quitNow);
process.on('SIGINT', quitNow);

if (!app.requestSingleInstanceLock()) {
  app.exit(0);
}

app.on('second-instance', () => {
  // Someone started K.OS Home again: bring the existing one to the front
  if (win) {
    win.show();
    win.focus();
  }
});

function isAllowedUrl(url) {
  const shellFiles = 'file://' + __dirname + '/';
  return url.startsWith(HOME_URL) || url.startsWith(shellFiles);
}

function isBlockedKey(input) {
  if (DEV || input.type !== 'keyDown') {
    return false;
  }
  const key = (input.key || '').toLowerCase();
  // Reload, full screen toggle, developer tools
  if (['f5', 'f11', 'f12', 'browserback', 'browserforward', 'browserrefresh'].includes(key)) {
    return true;
  }
  if (input.alt && (key === 'f4' || key === 'arrowleft' || key === 'arrowright')) {
    return true;
  }
  if (input.control || input.meta) {
    // Ctrl+R reload, Ctrl+W close, Ctrl+Q quit, Ctrl+N new window, Ctrl+P print,
    // Ctrl+S save, Ctrl+O open, Ctrl+plus/minus/0 zoom, Ctrl+Shift+I/J/C dev tools
    return ['r', 'w', 'q', 'n', 'p', 's', 'o', 'u', '+', '-', '=', '0', 'i', 'j', 'c'].includes(key);
  }
  return false;
}

function pingHelper() {
  return new Promise((resolve) => {
    const req = http.get(HOME_URL + 'api/ping', { timeout: 1000 }, (res) => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { body += chunk; });
      res.on('end', () => resolve(res.statusCode === 200 && body.includes('"kos-home"')));
    });
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.on('error', () => resolve(false));
  });
}

function showWaiting() {
  if (win && !showingWaiting && !homeLoaded) {
    showingWaiting = true;
    win.loadFile(path.join(__dirname, 'waiting.html'));
  }
}

function loadHome() {
  if (!win) {
    return;
  }
  homeLoaded = true;
  showingWaiting = false;
  win.loadURL(HOME_URL);
}

function maybeLoadHome() {
  if (homeLoaded || !introDone) {
    return;
  }
  if (helperUp) {
    loadHome();
  } else {
    showWaiting();
  }
}

async function watchHelper() {
  // Waits for the K.OS Home helper (started by kos-home) to answer
  for (;;) {
    if (await pingHelper()) {
      helperUp = true;
      maybeLoadHome();
      return;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
}

function finishIntro() {
  if (!introDone) {
    introDone = true;
    maybeLoadHome();
  }
}

function createWindow() {
  Menu.setApplicationMenu(null);
  win = new BrowserWindow({
    title: 'K.OS Home',
    show: false,
    fullscreen: true,
    kiosk: true,
    frame: false,
    autoHideMenuBar: true,
    backgroundColor: '#0A0A0C',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
    },
  });

  // The window title always stays "K.OS Home" (the K.OS window rules look for it)
  win.on('page-title-updated', (e) => e.preventDefault());
  win.once('ready-to-show', () => {
    win.show();
    win.focus();
  });
  // Nothing may close K.OS Home except K.OS itself
  win.on('close', (e) => {
    if (!quitting) {
      e.preventDefault();
    }
  });
  win.on('leave-full-screen', () => {
    if (!quitting) {
      win.setFullScreen(true);
    }
  });

  const wc = win.webContents;
  wc.setVisualZoomLevelLimits(1, 1).catch(() => {});
  wc.setWindowOpenHandler(() => ({ action: 'deny' }));
  wc.on('will-navigate', (e, url) => {
    if (!isAllowedUrl(url)) {
      e.preventDefault();
    }
  });
  wc.on('before-input-event', (e, input) => {
    if (DEV && input.type === 'keyDown') {
      const key = (input.key || '').toLowerCase();
      if (key === 'f12') { wc.toggleDevTools(); }
      if (key === 'f5') { wc.reload(); }
      if ((input.control || input.meta) && key === 'q') { quitNow(); }
      return;
    }
    if (isBlockedKey(input)) {
      e.preventDefault();
    }
  });
  wc.on('context-menu', (e) => e.preventDefault());
  wc.on('did-fail-load', (e, code, desc, url, isMainFrame) => {
    if (isMainFrame && url.startsWith(HOME_URL) && code !== -3) {
      // The helper went away: show the waiting screen and wait for it again
      homeLoaded = false;
      helperUp = false;
      showWaiting();
      watchHelper();
    }
  });
  wc.on('render-process-gone', () => {
    // The page crashed: start it again
    setTimeout(() => {
      if (homeLoaded) {
        loadHome();
      } else {
        showingWaiting = false;
        maybeLoadHome();
      }
    }, 1000);
  });

  if (!introDone) {
    win.loadFile(path.join(__dirname, 'intro.html'));
    setTimeout(finishIntro, INTRO_MAX_MS);
  } else {
    showWaiting();
  }
  watchHelper();
}

ipcMain.on('kos-intro-done', (e) => {
  if (e.senderFrame && String(e.senderFrame.url).startsWith('file://')) {
    finishIntro();
  }
});

/* ---------- Quick Menu ---------- */

function kwinAction(name) {
  // K.OS window actions from the K.OS Console KWin script
  const args = ['call', '--session', '--dest', 'org.kde.kglobalaccel', '--object-path', '/component/kwin',
    '--method', 'org.kde.kglobalaccel.Component.invokeShortcut', "'" + name + "'"];
  execFile('gdbus', args, { timeout: 5000 }, (err) => {
    if (err) { execFile('gdbus', args.concat(["'default'"]), { timeout: 5000 }, () => {}); }
  });
}

function tellInput(line) {
  for (const c of linkClients) {
    try { c.write(line + '\n'); } catch (e) { /* client gone */ }
  }
}

function createMenuWindow() {
  // Full screen over the game. It must be resizable: a fixed-size window is
  // not made full screen on Wayland, and stayed a small box in the corner.
  const area = screen.getPrimaryDisplay().bounds;
  menuWin = new BrowserWindow({
    title: MENU_TITLE,
    show: false,
    x: area.x,
    y: area.y,
    width: area.width,
    height: area.height,
    fullscreen: true,
    frame: false,
    transparent: true,
    backgroundColor: '#00000000',
    alwaysOnTop: true,
    skipTaskbar: true,
    resizable: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
      backgroundThrottling: false,
    },
  });
  menuWin.on('page-title-updated', (e) => e.preventDefault());
  menuWin.on('close', (e) => {
    if (!quitting) {
      e.preventDefault();
      hideMenu();
    }
  });
  // Clicking or Alt+Tab to another window closes the menu
  menuWin.on('blur', () => {
    if (menuOpen && Date.now() - menuShownAt > 400) { hideMenu(); }
  });
  const wc = menuWin.webContents;
  wc.setWindowOpenHandler(() => ({ action: 'deny' }));
  wc.on('will-navigate', (e, url) => { if (!url.startsWith(HOME_URL)) { e.preventDefault(); } });
  wc.on('context-menu', (e) => e.preventDefault());
  wc.on('before-input-event', (e, input) => { if (isBlockedKey(input)) { e.preventDefault(); } });
  wc.on('did-finish-load', () => { menuReady = true; });
  wc.on('did-fail-load', (e, code, desc, url, isMainFrame) => {
    if (isMainFrame && code !== -3) {
      menuReady = false;
      setTimeout(() => { if (menuWin) { menuWin.loadURL(HOME_URL + 'menu.html'); } }, 3000);
    }
  });
  wc.on('render-process-gone', () => {
    menuReady = false;
    setTimeout(() => { if (menuWin) { menuWin.loadURL(HOME_URL + 'menu.html'); } }, 1000);
  });
  menuWin.loadURL(HOME_URL + 'menu.html');
}

function showMenu() {
  if (!homeLoaded) { return; }
  if (!menuWin) { createMenuWindow(); }
  if (!menuReady) {
    menuWin.webContents.once('did-finish-load', () => showMenu());
    return;
  }
  menuOpen = true;
  menuShownAt = Date.now();
  menuWin.webContents.send('kos-menu-show');
  menuWin.show();
  if (!menuWin.isFullScreen()) { menuWin.setFullScreen(true); }
  menuWin.focus();
  tellInput('menu-open');
}

function hideMenu() {
  if (!menuOpen) { return; }
  menuOpen = false;
  if (menuWin) {
    menuWin.webContents.send('kos-menu-hide');
    menuWin.hide();
  }
  tellInput('menu-closed');
}

function goHome() {
  hideMenu();
  // Give the window manager a moment to put the game back first
  setTimeout(() => kwinAction('KOS Show Home'), 150);
}

function pressKeys(combo) {
  hideMenu();
  if (/^KEY_[A-Z0-9_]+(\+KEY_[A-Z0-9_]+){0,3}$/.test(combo)) {
    setTimeout(() => tellInput('key ' + combo), 350);
  }
}

function handleLink(line) {
  const cmd = line.trim();
  if (cmd === 'menu') { if (menuOpen) { hideMenu(); } else { showMenu(); } }
  else if (cmd === 'home') { goHome(); }
  else if (cmd === 'close') { hideMenu(); }
}

function startLink() {
  try { fs.unlinkSync(SOCKET); } catch (e) { /* no old socket */ }
  const server = net.createServer((c) => {
    linkClients.add(c);
    c.setEncoding('utf8');
    c.write((menuOpen ? 'menu-open' : 'menu-closed') + '\n');
    let buf = '';
    c.on('data', (d) => {
      buf += d;
      if (buf.length > 4096) { buf = ''; }
      let i;
      while ((i = buf.indexOf('\n')) >= 0) {
        handleLink(buf.slice(0, i));
        buf = buf.slice(i + 1);
      }
    });
    c.on('close', () => linkClients.delete(c));
    c.on('error', () => linkClients.delete(c));
  });
  server.on('error', (err) => console.error('K.OS link:', err.message));
  server.listen(SOCKET, () => { try { fs.chmodSync(SOCKET, 0o600); } catch (e) { /* fine */ } });
}

ipcMain.on('kos-menu', (e, action, arg) => {
  if (!menuWin || e.sender !== menuWin.webContents) { return; }
  if (action === 'close' || action === 'resume') { hideMenu(); }
  else if (action === 'home') { goHome(); }
  else if (action === 'keys') { pressKeys(String(arg || '')); }
});

app.whenReady().then(() => {
  createWindow();
  startLink();
  // Load the Quick Menu in the background, so the Xbox button opens it at once
  setTimeout(() => { if (!menuWin && homeLoaded) { createMenuWindow(); } }, 4000);
  setInterval(() => { if (!menuWin && homeLoaded) { createMenuWindow(); } }, 10000);
});
app.on('window-all-closed', () => app.quit());
