/*
  K.OS Console (KWin script).
  While K.OS Home is open, every new game or app window:
    1. moves to the screen K.OS Home is on (no more windows between two monitors)
    2. goes full screen (games only; K.OS web apps are already full screen)
    3. comes to the front
  When K.OS Home is not open, the normal KDE desktop is left alone.
*/

// Windows that must never be touched (matched against class, name and desktop file)
var SKIP = [
    /^steam$/, /^steamwebhelper$/, /^org\.kde\./, /^kdialog$/, /^zenity$/, /konsole/,
    /plasmashell/, /krunner/, /xwaylandvideobridge/, /polkit/, /^kwin/, /systemsettings/,
    /dolphin/, /spectacle/, /discover/
];
var BROWSER = /chrome|chromium/;

function names(w) {
    return [w.resourceClass, w.resourceName, w.desktopFileName].map(function (n) {
        return String(n || "").toLowerCase();
    });
}

function matches(w, list) {
    var n = names(w);
    for (var i = 0; i < n.length; i++) {
        for (var j = 0; j < list.length; j++) {
            if (n[i] && list[j].test(n[i])) { return true; }
        }
    }
    return false;
}

function isBrowser(w) { return matches(w, [BROWSER]); }

function isHome(w) {
    return isBrowser(w) && String(w.caption || "").indexOf("K.OS") === 0;
}

function findHome() {
    var list = workspace.windowList();
    for (var i = 0; i < list.length; i++) {
        if (isHome(list[i])) { return list[i]; }
    }
    return null;
}

function handle(w) {
    if (!w || !w.normalWindow || w.transient || isHome(w) || matches(w, SKIP)) { return; }
    var home = findHome();
    if (!home) { return; }
    var g = w.frameGeometry;
    if (g && g.width < 200 && g.height < 200) { return; } // splash screens and tiny helpers

    if (home.output && w.output !== home.output) {
        workspace.sendClientToScreen(w, home.output);
    }
    if (!isBrowser(w) && w.fullScreenable && !w.fullScreen) {
        w.fullScreen = true;
    }
    workspace.activeWindow = w;
}

workspace.windowAdded.connect(handle);
