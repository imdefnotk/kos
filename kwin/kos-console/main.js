// K.OS Console: window rules for the K.OS console (KWin script).
//
// Only acts while a K.OS Home window exists (window title starting with "K.OS").
// On a normal KDE desktop without K.OS Home it does nothing.
//
//  1. K.OS Home itself: always full screen, no border, can never be minimized.
//  2. A new game or app window: moves to the K.OS Home screen, goes full
//     screen (browsers handle full screen themselves, so they only move)
//     and comes to the front.
//  3. When the last game or app window closes, K.OS Home comes back to the
//     front, like closing a game on a console.
//
// Left alone: the Steam client, KDE tools and dialogs, Konsole, pop-ups,
// tiny windows (launchers, splash screens).
//
// The build copies this file into /usr/share/kwin/scripts/kos-console/contents/code/main.js

var LEAVE_ALONE = [
    "steam", "steamwebhelper", "konsole", "kdialog", "zenity", "systemsettings",
    "dolphin", "plasmashell", "krunner", "kwrite", "kate", "spectacle",
    "xdg-desktop-portal-kde", "polkit-kde-authentication-agent-1", "org.kde.polkit-kde-authentication-agent-1"
];
var BROWSERS = ["chrome", "chromium", "firefox", "brave", "opera", "vivaldi", "microsoft-edge"];

function cls(w) {
    return String(w.resourceClass || "").toLowerCase();
}

function isHome(w) {
    return !!w && !w.deleted && String(w.caption || "").indexOf("K.OS") === 0;
}

function isBrowser(w) {
    var c = cls(w);
    for (var i = 0; i < BROWSERS.length; i++) {
        if (c.indexOf(BROWSERS[i]) !== -1) {
            return true;
        }
    }
    return false;
}

// True for windows K.OS should manage: real game and app windows
function isApp(w) {
    if (!w || w.deleted || isHome(w)) {
        return false;
    }
    if (!w.normalWindow || w.dialog || w.transient || w.specialWindow || w.popupWindow) {
        return false;
    }
    var c = cls(w);
    if (c.indexOf("org.kde.") === 0 || LEAVE_ALONE.indexOf(c) !== -1) {
        return false;
    }
    var g = w.frameGeometry;
    if (g && (g.width < 400 || g.height < 300)) {
        return false;
    }
    return true;
}

function homeWindow() {
    var list = workspace.stackingOrder;
    for (var i = list.length - 1; i >= 0; i--) {
        if (isHome(list[i])) {
            return list[i];
        }
    }
    return null;
}

var readyHomes = [];

function setupHome(w) {
    if (readyHomes.indexOf(w) !== -1) {
        return;
    }
    readyHomes.push(w);
    w.noBorder = true;
    w.fullScreen = true;
    if (w.minimized) {
        w.minimized = false;
    }
    w.minimizedChanged.connect(function () {
        if (w.minimized) {
            w.minimized = false;
        }
    });
    w.fullScreenChanged.connect(function () {
        if (!w.fullScreen && !w.deleted) {
            w.fullScreen = true;
        }
    });
}

function handleApp(w) {
    var home = homeWindow();
    if (!home) {
        return;
    }
    if (w.output !== home.output) {
        workspace.sendClientToScreen(w, home.output);
    }
    if (!isBrowser(w)) {
        w.noBorder = true;
        w.fullScreen = true;
    }
    if (w.minimized) {
        w.minimized = false;
    }
    workspace.activeWindow = w;
}

function onWindowAdded(w) {
    if (!w) {
        return;
    }
    if (isHome(w)) {
        setupHome(w);
        return;
    }
    // Some programs set their real title a moment after the window appears
    w.captionChanged.connect(function () {
        if (isHome(w)) {
            setupHome(w);
        }
    });
    if (isApp(w)) {
        handleApp(w);
    }
}

function onWindowRemoved(w) {
    var k = readyHomes.indexOf(w);
    if (k !== -1) {
        readyHomes.splice(k, 1);
        return;
    }
    if (!w || isHome(w)) {
        return;
    }
    var home = homeWindow();
    if (!home) {
        return;
    }
    var list = workspace.stackingOrder;
    for (var i = 0; i < list.length; i++) {
        var other = list[i];
        if (other !== w && isApp(other) && !other.minimized) {
            return; // another game or app is still open
        }
    }
    workspace.activeWindow = home;
}

workspace.windowAdded.connect(onWindowAdded);
workspace.windowRemoved.connect(onWindowRemoved);

// Windows that were already open when the script started (for example after an update)
var existing = workspace.stackingOrder;
for (var j = 0; j < existing.length; j++) {
    if (isHome(existing[j])) {
        setupHome(existing[j]);
    }
}
