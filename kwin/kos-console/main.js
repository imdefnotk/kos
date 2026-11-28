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
//  4. Steam is only ever seen in Big Picture: Steam's desktop window (the big
//     "Steam" library window, shown for example after "Exit Big Picture" or
//     after a game) is hidden at once and K.OS Home comes back. Small Steam
//     windows (sign-in, Steam Guard, launch questions, updates) stay visible.
//  5. Window actions for the rest of K.OS (run by the K.OS Home helper and by
//     kos-input through KDE's shortcut service, no keys needed):
//       KOS Show Home    K.OS Home to the front (a game keeps running behind it)
//       KOS Resume Game  the game or app behind K.OS Home back to the front
//       KOS Toggle Home  K.OS Home, or back to the game if K.OS Home is in front
//                        (used by kos-input only when the K.OS Home shell is not running)
//  6. The Quick Menu ("K.OS Hızlı Menü", Xbox button tap) stays on top of
//     everything; when it closes, the game or app it covered is in front again.
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

var MENU_TITLE = "K.OS Hızlı Menü";

// The Quick Menu (Xbox button): a see-through window on top of the game
function isMenu(w) {
    return !!w && String(w.caption || "") === MENU_TITLE;
}

function isHome(w) {
    return !!w && !w.deleted && !isMenu(w) && String(w.caption || "").indexOf("K.OS") === 0;
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
    if (!w || w.deleted || isHome(w) || isMenu(w)) {
        return false;
    }
    if (!w.normalWindow || w.dialog || w.transient || w.specialWindow || w.popupWindow) {
        return false;
    }
    var c = cls(w);
    if (c === "steam" && /big picture/i.test(String(w.caption || ""))) {
        return true; // Steam Big Picture counts as an app (Alt+Tab, back to it)
    }
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
    // K.OS Home opening (at power on) comes to the front, unless a game is open
    if (!topApp(null)) {
        workspace.activeWindow = w;
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

// Steam's big desktop window (library, store pages). Sign-in and other small
// Steam windows are not matched.
function isSteamDesktop(w) {
    if (!w || w.deleted || cls(w) !== "steam" || !w.normalWindow) {
        return false;
    }
    var cap = String(w.caption || "");
    if (/big picture/i.test(cap) || /sign in|giri|guard|login|update|güncelle/i.test(cap)) {
        return false;
    }
    var g = w.frameGeometry;
    return !!g && g.width >= 900 && g.height >= 500;
}

function hideSteamDesktop(w) {
    var home = homeWindow();
    if (!home || !isSteamDesktop(w)) {
        return;
    }
    w.minimized = true;
    if (!topApp(null)) {
        workspace.activeWindow = home;
    }
}

// The game or app nearest the top, or null
function topApp(except) {
    var list = workspace.stackingOrder;
    for (var i = list.length - 1; i >= 0; i--) {
        var w = list[i];
        if (w !== except && isApp(w) && !w.minimized) {
            return w;
        }
    }
    return null;
}

function showHome() {
    var home = homeWindow();
    // Going to K.OS Home on purpose: the Quick Menu closing must not give the
    // focus back to the game or app it covered
    menuPrev = null;
    if (home) {
        if (home.minimized) {
            home.minimized = false;
        }
        workspace.activeWindow = home;
    }
}

function resumeGame() {
    var w = topApp(null);
    if (w) {
        workspace.activeWindow = w;
        return true;
    }
    return false;
}

function toggleHome() {
    var home = homeWindow();
    if (home && workspace.activeWindow === home && resumeGame()) {
        return;
    }
    showHome();
}

// Quick Menu: always on top of everything, on K.OS Home's screen, in front.
// When it goes away, the game or app that was in front gets the focus back.
var menuPrev = null;

function setupMenu(w) {
    var prev = workspace.activeWindow;
    if (prev && prev !== w && !isMenu(prev)) {
        menuPrev = prev;
    }
    w.keepAbove = true;
    w.skipSwitcher = true;
    w.skipTaskbar = true;
    w.skipPager = true;
    w.noBorder = true;
    var home = homeWindow();
    if (home && w.output !== home.output) {
        workspace.sendClientToScreen(w, home.output);
    }
    w.fullScreen = true;
    workspace.activeWindow = w;
}

function leaveMenu() {
    var back = menuPrev;
    menuPrev = null;
    if (back && !back.deleted && !back.minimized) {
        workspace.activeWindow = back;
    }
}

function onWindowAdded(w) {
    if (!w) {
        return;
    }
    if (isMenu(w)) {
        setupMenu(w);
        w.minimizedChanged.connect(function () {
            if (w.minimized) {
                leaveMenu();
            }
        });
        return;
    }
    if (isHome(w)) {
        setupHome(w);
        return;
    }
    if (cls(w) === "steam") {
        hideSteamDesktop(w);
        // Steam shows its window first and gives it its real size a moment later
        w.frameGeometryChanged.connect(function () { hideSteamDesktop(w); });
        w.captionChanged.connect(function () { hideSteamDesktop(w); });
        w.minimizedChanged.connect(function () {
            if (!w.minimized) {
                hideSteamDesktop(w);
            }
        });
        return;
    }
    // Some programs set their real title a moment after the window appears
    w.captionChanged.connect(function () {
        if (isMenu(w)) {
            setupMenu(w);
        } else if (isHome(w)) {
            setupHome(w);
        }
    });
    if (isApp(w)) {
        handleApp(w);
    }
}

function onWindowRemoved(w) {
    if (isMenu(w)) {
        leaveMenu();
        return;
    }
    if (w === menuPrev) {
        menuPrev = null;
    }
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
    if (topApp(w)) {
        return; // another game or app is still open
    }
    workspace.activeWindow = home;
}

workspace.windowAdded.connect(onWindowAdded);
registerShortcut("KOS Show Home", "K.OS: K.OS Home'u öne getir", "", showHome);
registerShortcut("KOS Resume Game", "K.OS: Oyuna dön", "", resumeGame);
registerShortcut("KOS Toggle Home", "K.OS: K.OS Home / oyun", "", toggleHome);
workspace.windowRemoved.connect(onWindowRemoved);

// Windows that were already open when the script started (for example after an update)
var existing = workspace.stackingOrder;
for (var j = 0; j < existing.length; j++) {
    if (isHome(existing[j])) {
        setupHome(existing[j]);
    } else if (cls(existing[j]) === "steam") {
        hideSteamDesktop(existing[j]);
    }
}

// Trace: which window is in front (shows up in ~/.local/state/kos/session.log
// and in kos-diag). Helps find what takes focus while a game is starting.
workspace.windowActivated.connect(function (w) {
    if (!w) {
        print("kos-console: active window: none");
        return;
    }
    print("kos-console: active window: " + cls(w) + " \"" + String(w.caption || "").slice(0, 60) + "\" " +
          Math.round(w.width) + "x" + Math.round(w.height));
});
