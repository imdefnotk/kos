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
'use strict';

const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const fs = require('fs');
const http = require('http');
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

let win = null;
let quitting = false;
let introDone = !WANT_INTRO;
let helperUp = false;
let homeLoaded = false;
let showingWaiting = false;

function quitNow() {
  quitting = true;
  app.exit(0);
}

// kos-home --quit and the session end send SIGTERM
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

app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
