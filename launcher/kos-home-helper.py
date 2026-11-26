#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K.OS Home helper (phase 2).

A small local program that sits next to the K.OS Home launcher and gives it
what a web page cannot do on its own:

  - serves the launcher files on http://127.0.0.1:47800/ (this computer only)
  - reads the installed Steam games, play time and "last played" from Steam's
    own files on the drive
  - hands out Steam's cover art from the drive (falls back to Steam's web
    servers when a picture is missing)
  - starts a Steam game when you press Oyna
  - on K.OS: opens the K.OS apps (Netflix, HBO Max, Xbox Bulut Oyun,
    Internet, Steam, Windows'a Gec)

It only listens on 127.0.0.1, so other devices on the network cannot reach it.
It uses only Python's built-in parts, so nothing needs to be installed on K.OS.
The same file runs on Windows for testing (needs Python 3.8 or newer).

Usage:
  python3 kos-home-helper.py [--port 47800] [--root <launcher folder>]
                             [--idle-exit <seconds>] [--log <file>]
"""

import argparse
import json
import logging
import mimetypes
import os
import re
import shutil
import socket
import socketserver
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlparse

VERSION = 1
DEFAULT_PORT = 47800
IS_WINDOWS = os.name == "nt"
STEAMID64_BASE = 76561197960265728

# Steam items that are tools, not games (Proton, runtimes, redistributables)
TOOL_APPIDS = {228980, 1070560, 1391110, 1628350, 1826330, 2180100, 1161040, 1007020}
TOOL_NAME = re.compile(
    r"^(Proton|Steam Linux Runtime|Steamworks Common|SteamVR|Steam Audio|Steamworks SDK)",
    re.IGNORECASE,
)

# Apps the launcher may open on K.OS. Fixed list: the page can only ask for an id.
LINUX_APPS = {
    "netflix": ["/usr/bin/kos-webapp", "app", "https://www.netflix.com", "netflix"],
    "hbomax": ["/usr/bin/kos-webapp", "app", "https://www.hbomax.com", "hbomax"],
    "xcloud": ["/usr/bin/kos-webapp", "app", "https://www.xbox.com/play", "gamepass"],
    "browser": ["/usr/bin/kos-webapp", "browser", "https://www.google.com", "browser"],
    "steam": ["steam", "steam://open/bigpicture"],
    "windows": ["/usr/bin/kos-boot-windows"],
}

# Picture kinds: (custom art in userdata/<id>/config/grid, file names in Steam's
# library cache, name on Steam's web server)
ART_KINDS = {
    "portrait": ("{a}p", ["library_600x900_2x.jpg", "library_600x900.jpg"], "library_600x900_2x.jpg"),
    "hero": ("{a}_hero", ["library_hero_2x.jpg", "library_hero.jpg"], "library_hero.jpg"),
    "logo": ("{a}_logo", ["logo_2x.png", "logo.png"], "logo.png"),
    "header": ("{a}", ["header_2x.jpg", "header.jpg", "library_header.jpg"], "header.jpg"),
}
CDN = "https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/{a}/{name}"

mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")

log = logging.getLogger("kos-home")


# ---------------------------------------------------------------- Steam files

def parse_vdf(text):
    """Reads Valve's text format (KeyValues) into nested dictionaries."""
    root = {}
    stack = [root]
    key = None
    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"|([{}])|(//[^\n]*)', text):
        value, brace, comment = m.groups()
        if comment is not None:
            continue
        if brace == "{":
            child = {}
            if key is not None:
                stack[-1][key] = child
            stack.append(child)
            key = None
        elif brace == "}":
            if len(stack) > 1:
                stack.pop()
            key = None
        else:
            value = re.sub(r'\\(["\\])', r"\1", value)
            if key is None:
                key = value
            else:
                stack[-1][key] = value
                key = None
    return root


def read_vdf(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return parse_vdf(f.read())
    except OSError:
        return {}


def iget(d, *keys):
    """Case-insensitive nested lookup (Steam is not consistent about case)."""
    for k in keys:
        if not isinstance(d, dict):
            return None
        hit = None
        kl = k.lower()
        for dk, dv in d.items():
            if dk.lower() == kl:
                hit = dv
                break
        d = hit
    return d


def to_int(v, default=0):
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return default


def steam_roots():
    """Places where Steam may be installed, best guess first."""
    found = []
    if IS_WINDOWS:
        try:
            import winreg  # only exists on Windows
            for hive, sub, name in (
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath"),
            ):
                try:
                    with winreg.OpenKey(hive, sub) as k:
                        found.append(winreg.QueryValueEx(k, name)[0])
                except OSError:
                    pass
        except ImportError:
            pass
        for env in ("ProgramFiles(x86)", "ProgramFiles"):
            if os.environ.get(env):
                found.append(os.path.join(os.environ[env], "Steam"))
    else:
        home = os.path.expanduser("~")
        found += [
            os.path.join(home, ".local/share/Steam"),
            os.path.join(home, ".steam/steam"),
            os.path.join(home, ".steam/root"),
            os.path.join(home, ".var/app/com.valvesoftware.Steam/.local/share/Steam"),
        ]
    roots = []
    seen = set()
    for p in found:
        p = os.path.normpath(p.replace("/", os.sep))
        real = os.path.realpath(p)
        if real in seen or not os.path.isdir(os.path.join(p, "steamapps")):
            continue
        seen.add(real)
        roots.append(p)
    return roots


def library_folders(root):
    folders = [root]
    data = read_vdf(os.path.join(root, "steamapps", "libraryfolders.vdf"))
    libs = iget(data, "libraryfolders") or {}
    for v in libs.values():
        path = iget(v, "path") if isinstance(v, dict) else v
        if isinstance(path, str) and path:
            folders.append(os.path.normpath(path))
    out = []
    seen = set()
    for f in folders:
        real = os.path.realpath(f)
        if real not in seen and os.path.isdir(os.path.join(f, "steamapps")):
            seen.add(real)
            out.append(f)
    return out


def current_user_dir(root):
    """userdata/<id> of the account that signed in last."""
    userdata = os.path.join(root, "userdata")
    users = iget(read_vdf(os.path.join(root, "config", "loginusers.vdf")), "users") or {}
    best = None
    for id64, info in users.items():
        if not isinstance(info, dict):
            continue
        acc = to_int(id64) - STEAMID64_BASE
        path = os.path.join(userdata, str(acc))
        if acc > 0 and os.path.isdir(path):
            recent = str(iget(info, "MostRecent") or "0") == "1"
            stamp = to_int(iget(info, "Timestamp"))
            score = (recent, stamp)
            if best is None or score > best[0]:
                best = (score, path, iget(info, "PersonaName") or "")
    if best:
        return best[1], best[2]
    # Fallback: the user folder whose settings changed last
    newest = None
    try:
        for name in os.listdir(userdata):
            cfg = os.path.join(userdata, name, "config", "localconfig.vdf")
            if name.isdigit() and name != "0" and os.path.isfile(cfg):
                m = os.path.getmtime(cfg)
                if newest is None or m > newest[0]:
                    newest = (m, os.path.join(userdata, name))
    except OSError:
        pass
    return (newest[1], "") if newest else (None, "")


class Steam:
    """Everything the launcher needs from Steam, re-read at most every few seconds."""

    def __init__(self):
        self.lock = threading.Lock()
        self.cache = None
        self.cache_time = 0.0

    def snapshot(self):
        with self.lock:
            if self.cache is None or time.time() - self.cache_time > 5:
                self.cache = self._read()
                self.cache_time = time.time()
            return self.cache

    def _read(self):
        roots = steam_roots()
        if not roots:
            return {"steamFound": False, "root": None, "userDir": None, "user": "", "games": []}
        root = roots[0]
        user_dir, persona = current_user_dir(root)
        apps_cfg = {}
        if user_dir:
            cfg = read_vdf(os.path.join(user_dir, "config", "localconfig.vdf"))
            apps_cfg = iget(cfg, "UserLocalConfigStore", "Software", "Valve", "Steam", "apps") or {}
        games = {}
        for lib in library_folders(root):
            sa = os.path.join(lib, "steamapps")
            try:
                names = os.listdir(sa)
            except OSError:
                continue
            for fn in names:
                if not (fn.startswith("appmanifest_") and fn.endswith(".acf")):
                    continue
                st = iget(read_vdf(os.path.join(sa, fn)), "AppState") or {}
                appid = to_int(iget(st, "appid"))
                name = (iget(st, "name") or "").strip()
                flags = to_int(iget(st, "StateFlags"))
                if appid <= 0 or not name or appid in TOOL_APPIDS or TOOL_NAME.match(name):
                    continue
                if not flags & 4:  # 4 = fully installed
                    continue
                info = iget(apps_cfg, str(appid)) or {}
                games[appid] = {
                    "appid": appid,
                    "name": name,
                    "lastPlayed": to_int(iget(info, "LastPlayed")),
                    "playtimeMin": to_int(iget(info, "Playtime")),
                    "sizeBytes": to_int(iget(st, "SizeOnDisk")),
                    "updating": flags != 4,
                }
        ordered = sorted(games.values(), key=lambda g: (-g["lastPlayed"], g["name"].lower()))
        return {"steamFound": True, "root": root, "userDir": user_dir, "user": persona, "games": ordered}

    def art_file(self, appid, kind):
        """Path of a picture on the drive, or None."""
        snap = self.snapshot()
        root = snap.get("root")
        if not root or kind not in ART_KINDS:
            return None
        grid_name, cache_names, _ = ART_KINDS[kind]
        # 1. Art the user picked themselves in Steam
        if snap.get("userDir"):
            base = os.path.join(snap["userDir"], "config", "grid", grid_name.format(a=appid))
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                if os.path.isfile(base + ext):
                    return base + ext
        cache = os.path.join(root, "appcache", "librarycache")
        # 2. Steam's library cache, new layout: librarycache/<appid>/(<hash>/)<file>
        folder = os.path.join(cache, str(appid))
        if os.path.isdir(folder):
            for want in cache_names:
                for dirpath, dirnames, filenames in os.walk(folder):
                    if dirpath[len(folder):].count(os.sep) > 2:
                        dirnames[:] = []
                        continue
                    if want in filenames:
                        return os.path.join(dirpath, want)
        # 3. Older layout: librarycache/<appid>_<file>
        for want in cache_names:
            old = os.path.join(cache, "{}_{}".format(appid, want))
            if os.path.isfile(old):
                return old
        return None


# ---------------------------------------------------------------- actions

def run_detached(cmd):
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if IS_WINDOWS:
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(cmd, **kwargs)


def open_steam_url(url):
    if IS_WINDOWS:
        os.startfile(url)  # Windows hands steam:// links to Steam
        return
    if shutil.which("steam"):
        run_detached(["steam", url])
    else:
        run_detached(["xdg-open", url])


def desktop_mode():
    """K.OS only: developer desktop mode. Stops K.OS Home from coming back,
    turns all displays back on and closes K.OS Home, which switches the
    K.OS session over to the normal Plasma desktop."""
    if IS_WINDOWS:
        return False
    cfg = os.path.join(os.path.expanduser("~"), ".config")
    os.makedirs(cfg, exist_ok=True)
    open(os.path.join(cfg, "kos-desktop-mode"), "w").close()
    steps = ["sleep 1"]
    try:
        out = subprocess.run(["kscreen-doctor", "--json"], capture_output=True, text=True, timeout=10).stdout
        for o in json.loads(out or "{}").get("outputs", []):
            name = str(o.get("name", ""))
            if o.get("connected") and not o.get("enabled") and re.match(r"^[A-Za-z0-9_.-]+$", name):
                steps.append("kscreen-doctor output.%s.enable" % name)
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    # Closing K.OS Home ends the K.OS session, and the session start then opens
    # the Plasma desktop (see /usr/bin/kos-start-session)
    steps.append("/usr/bin/kos-home --quit")
    run_detached(["bash", "-c", "; ".join(steps)])
    return True


def open_app(app_id):
    """Returns (handled, error). On Windows the launcher opens apps itself."""
    if IS_WINDOWS:
        return False, None
    cmd = LINUX_APPS.get(app_id)
    if not cmd:
        return True, "unknown"
    exe = cmd[0] if os.path.isabs(cmd[0]) else shutil.which(cmd[0])
    if not exe or not os.path.exists(exe):
        return True, "missing"
    run_detached([exe] + cmd[1:])
    return True, None


# ---------------------------------------------------------------- web server

class Handler(BaseHTTPRequestHandler):
    server_version = "KOSHome/1"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        log.debug("%s %s", self.address_string(), fmt % args)

    # Only answer pages opened from this computer at our own address
    def allowed(self):
        port = self.server.server_address[1]
        hosts = {"127.0.0.1:%d" % port, "localhost:%d" % port}
        if (self.headers.get("Host") or "").lower() not in hosts:
            return False
        origin = self.headers.get("Origin")
        if origin and origin.lower() not in {"http://" + h for h in hosts}:
            return False
        return True

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_file(self, path, cache_seconds=0):
        try:
            with open(path, "rb") as f:
                body = f.read()
        except OSError:
            self.send_json({"ok": False, "error": "not found"}, 404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json", "image/svg+xml"):
            ctype += "; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "max-age=%d" % cache_seconds if cache_seconds else "no-cache")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        self.server.touch()
        if not self.allowed():
            self.send_json({"ok": False, "error": "forbidden"}, 403)
            return
        path = unquote(urlparse(self.path).path)

        if path == "/api/ping":
            self.send_json({"ok": True, "app": "kos-home", "version": VERSION,
                            "platform": "windows" if IS_WINDOWS else "linux"})
            return

        if path == "/api/library":
            snap = self.server.steam.snapshot()
            self.send_json({"ok": True, "steamFound": snap["steamFound"], "user": snap["user"],
                            "games": snap["games"]})
            return

        m = re.match(r"^/api/art/(\d{1,10})/(portrait|hero|logo|header)$", path)
        if m:
            appid, kind = int(m.group(1)), m.group(2)
            local = self.server.steam.art_file(appid, kind)
            if local:
                self.send_file(local, cache_seconds=3600)
            else:
                self.send_response(302)
                self.send_header("Location", CDN.format(a=appid, name=ART_KINDS[kind][2]))
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "max-age=600")
                self.end_headers()
            return

        if path.startswith("/api/"):
            self.send_json({"ok": False, "error": "not found"}, 404)
            return

        # Launcher files
        rel = "index.html" if path in ("", "/") else path.lstrip("/")
        root = self.server.root
        full = os.path.realpath(os.path.join(root, rel.replace("/", os.sep)))
        if not (full == root or full.startswith(root + os.sep)) or not os.path.isfile(full):
            self.send_json({"ok": False, "error": "not found"}, 404)
            return
        self.send_file(full)

    def do_POST(self):
        self.server.touch()
        length = to_int(self.headers.get("Content-Length"))
        if length:
            self.rfile.read(min(length, 65536))
        # The custom header stops other web sites from sending these requests
        if not self.allowed() or self.headers.get("X-KOS") != "1":
            self.send_json({"ok": False, "error": "forbidden"}, 403)
            return
        path = urlparse(self.path).path

        m = re.match(r"^/api/launch/(\d{1,10})$", path)
        if m:
            appid = int(m.group(1))
            try:
                open_steam_url("steam://rungameid/%d" % appid)
                log.info("launch %d", appid)
                self.send_json({"ok": True})
            except Exception as e:  # noqa: BLE001 (report any failure to the launcher)
                log.warning("launch %d failed: %s", appid, e)
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path == "/api/desktop":
            ok = desktop_mode()
            self.send_json({"ok": ok, "handled": not IS_WINDOWS})
            return

        m = re.match(r"^/api/open/([a-z]{1,20})$", path)
        if m:
            try:
                handled, err = open_app(m.group(1))
                self.send_json({"ok": err is None, "handled": handled, "error": err})
            except Exception as e:  # noqa: BLE001
                self.send_json({"ok": False, "handled": True, "error": str(e)}, 500)
            return

        self.send_json({"ok": False, "error": "not found"}, 404)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows "reuse" would let two helpers share the port, so it stays off there
    allow_reuse_address = not IS_WINDOWS

    def __init__(self, addr, root, idle_exit):
        self.root = os.path.realpath(root)
        self.steam = Steam()
        self.idle_exit = idle_exit
        self.last_seen = time.time()
        super().__init__(addr, Handler)

    def server_bind(self):
        if IS_WINDOWS and hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        # Skip HTTPServer's slow name lookup
        socketserver.TCPServer.server_bind(self)
        self.server_name = "127.0.0.1"
        self.server_port = self.server_address[1]

    def touch(self):
        self.last_seen = time.time()


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="K.OS Home helper")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--root", default=here, help="launcher folder (index.html)")
    ap.add_argument("--idle-exit", type=int, default=0,
                    help="quit after this many seconds without the launcher (0 = never)")
    ap.add_argument("--log", default=None, help="write a log file here")
    ap.add_argument("--list", action="store_true", help="print the games found and quit")
    args = ap.parse_args()

    # pythonw on Windows has no console: never write to a missing one
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    handlers = [logging.StreamHandler()]
    if args.log:
        try:
            handlers.append(logging.FileHandler(args.log, encoding="utf-8"))
        except OSError:
            pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", handlers=handlers)

    if args.list:
        snap = Steam().snapshot()
        if not snap["steamFound"]:
            print("Steam was not found on this computer.")
            return 1
        print("Steam: %s" % snap["root"])
        print("Account folder: %s" % (snap["userDir"] or "not found"))
        print("Installed games: %d" % len(snap["games"]))
        for g in snap["games"]:
            print("  %-10d %-40s %5d min played" % (g["appid"], g["name"][:40], g["playtimeMin"]))
        return 0

    if not os.path.isfile(os.path.join(args.root, "index.html")):
        log.error("index.html not found in %s", args.root)
        return 1

    try:
        server = Server(("127.0.0.1", args.port), args.root, args.idle_exit)
    except OSError:
        log.info("Port %d is busy: K.OS Home helper is probably already running.", args.port)
        return 0

    if args.idle_exit > 0:
        def watchdog():
            while True:
                time.sleep(15)
                if time.time() - server.last_seen > server.idle_exit:
                    log.info("Launcher closed, helper stopping.")
                    server.shutdown()
                    return
        threading.Thread(target=watchdog, daemon=True).start()

    log.info("K.OS Home helper running on http://127.0.0.1:%d/ (root %s)", args.port, server.root)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
