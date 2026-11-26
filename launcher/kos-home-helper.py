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
  - tells the launcher which games are controller friendly (from Steam's own
    game info cache, or the Steam store when that is missing)
  - on K.OS: knows which game is running, closes it on request, brings K.OS
    Home back when it ends, and keeps the controller button layouts
    (used by /usr/libexec/kos-input)

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

VERSION = 2
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
        self.traits = GameTraits()

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
        downloads = []
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
                want = to_int(iget(st, "BytesToDownload"))
                have = to_int(iget(st, "BytesDownloaded"))
                if want > 0 and have < want:
                    downloads.append({"appid": appid, "name": name, "percent": int(have * 100 / want),
                                      "bytes": want})
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
        traits = self.traits.get(root, list(games)) if games else {}
        for appid, g in games.items():
            t = traits.get(appid) or {}
            g["controller"] = t.get("controller")
            g["deck"] = t.get("deck")
        ordered = sorted(games.values(), key=lambda g: (-g["lastPlayed"], g["name"].lower()))
        return {"steamFound": True, "root": root, "userDir": user_dir, "user": persona, "games": ordered,
                "downloads": downloads}

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



# ---------------------------------------------------------------- game traits
# "Controller friendly" and Steam Deck status for each installed game, read from
# Steam's own game info cache on the drive (appcache/appinfo.vdf, or the newer
# appcache/appinfo/appinfo_XX.vdf shard files), so no internet is needed.
# controller: "full" | "partial" | "none" | None (unknown)
# deck: 3 = Verified, 2 = Playable, 1 = Unsupported, 0 or None = unknown

def _cstr(buf, pos):
    end = buf.find(b"\x00", pos)
    if end < 0:
        raise ValueError("unterminated string")
    return buf[pos:end].decode("utf-8", "replace"), end + 1


def parse_binary_kv(buf, pos, strings=None, want=None):
    """Valve's binary KeyValues. Returns (dict, new position). Keys are indexes
    into `strings` when the file has a string table. `want` limits which top
    level branches are kept (others are skipped while reading)."""
    out = {}
    while True:
        t = buf[pos]
        pos += 1
        if t in (0x08, 0x0B):
            return out, pos
        if strings is not None:
            idx = int.from_bytes(buf[pos:pos + 4], "little")
            pos += 4
            key = strings[idx] if idx < len(strings) else ""
        else:
            key, pos = _cstr(buf, pos)
        if t == 0x00:
            child, pos = parse_binary_kv(buf, pos, strings)
            if want is None or key in want:
                out[key] = child
        elif t == 0x01:
            out[key], pos = _cstr(buf, pos)
        elif t in (0x02, 0x04, 0x06):
            out[key] = int.from_bytes(buf[pos:pos + 4], "little", signed=True)
            pos += 4
        elif t == 0x03:
            import struct
            out[key] = struct.unpack_from("<f", buf, pos)[0]
            pos += 4
        elif t in (0x07, 0x0A):
            out[key] = int.from_bytes(buf[pos:pos + 8], "little", signed=(t == 0x0A))
            pos += 8
        elif t == 0x05:  # wide string, never used in appinfo; skip to the double zero
            end = pos
            while buf[end:end + 2] != b"\x00\x00":
                end += 2
            out[key] = ""
            pos = end + 2
        else:
            raise ValueError("unknown KeyValues type %d" % t)


def _traits_from(data):
    common = iget(data, "appinfo", "common") or {}
    ctl = iget(common, "controller_support")
    ctl = str(ctl).strip().lower() if ctl not in (None, "") else None
    deck = iget(common, "steam_deck_compatibility", "category")
    deck = to_int(deck, None) if deck is not None else None
    return {"controller": ctl, "deck": deck}


def _shard_of(appid):
    h = appid & 0xFFFFFFFF
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h & 0xFF


def _read_appinfo_single(path, appids):
    """appinfo.vdf versions 39 to 41 (one big file)."""
    import mmap
    with open(path, "rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as buf:
        return _scan_appinfo_single(buf, appids)


def _scan_appinfo_single(buf, appids):
    found = {}
    magic = int.from_bytes(buf[0:4], "little")
    version = magic & 0xFF
    if magic >> 8 != 0x075644 or version < 39 or version > 41:
        raise ValueError("unsupported appinfo version %x" % magic)
    pos = 8
    strings = None
    if version >= 41:
        table = int.from_bytes(buf[pos:pos + 8], "little")
        pos += 8
        count = int.from_bytes(buf[table:table + 4], "little")
        strings = []
        p = table + 4
        for _ in range(count):
            s, p = _cstr(buf, p)
            strings.append(s)
    while pos + 8 <= len(buf):
        appid = int.from_bytes(buf[pos:pos + 4], "little")
        if appid == 0:
            break
        size = int.from_bytes(buf[pos + 4:pos + 8], "little")
        start = pos + 8
        end = start + size
        if appid in appids:
            p = start + 4 + 4 + 8 + 20 + 4  # info state, updated, token, sha1, change number
            if version >= 40:
                p += 20
            try:
                data, _ = parse_binary_kv(buf, p, strings, want={"appinfo"})
                found[appid] = _traits_from(data)
            except (ValueError, IndexError):
                pass
        pos = end
    return found


def _read_appinfo_shard(path, appids):
    """appinfo shard files (version 42, appcache/appinfo/appinfo_XX.vdf)."""
    found = {}
    with open(path, "rb") as f:
        buf = f.read()
    magic = int.from_bytes(buf[0:4], "little")
    if magic >> 8 != 0x075644 or (magic & 0xFF) < 42:
        raise ValueError("not an appinfo shard")
    h = [int.from_bytes(buf[i:i + 4], "little") for i in range(8, 44, 4)]
    _shard, _shards, app_count, index_size, string_count, string_size = h[:6]
    index = 44
    table = index + index_size
    data_start = table + string_size
    strings = []
    p = table
    for _ in range(string_count):
        s, p = _cstr(buf, p)
        strings.append(s)
    p = index
    for _ in range(app_count):
        appid, off, size, summary = (int.from_bytes(buf[p + i:p + i + 4], "little") for i in (0, 4, 8, 12))
        p += 16 + summary
        if appid in appids:
            try:
                data, _ = parse_binary_kv(buf, data_start + off + 20, strings, want={"appinfo"})
                found[appid] = _traits_from(data)
            except (ValueError, IndexError):
                pass
    return found


class GameTraits:
    """Controller support and Steam Deck status, cached until Steam's files change."""

    def __init__(self):
        self.lock = threading.Lock()
        self.cache = {}
        self.stamp = None
        self.read_at = 0.0
        self.store = StoreTraits()

    def get(self, root, appids):
        appids = set(appids)
        single = os.path.join(root, "appcache", "appinfo.vdf")
        shard_dir = os.path.join(root, "appcache", "appinfo")
        try:
            if os.path.isdir(shard_dir):
                stamp = ("shards", os.path.getmtime(shard_dir), tuple(sorted(appids)))
            else:
                stamp = ("single", os.path.getmtime(single), tuple(sorted(appids)))
        except OSError:
            stamp = None
        with self.lock:
            # Steam rewrites its cache often while it runs: re-read it when the list
            # of games changes, or at most every 10 minutes
            same_games = bool(stamp and self.stamp and stamp[0] == self.stamp[0] and stamp[2] == self.stamp[2])
            if stamp != self.stamp and not (same_games and time.time() - self.read_at < 600):
                self.read_at = time.time()
                found = {}
                try:
                    if stamp and stamp[0] == "shards":
                        by_shard = {}
                        for a in appids:
                            by_shard.setdefault(_shard_of(a), set()).add(a)
                        for shard, ids in by_shard.items():
                            f = os.path.join(shard_dir, "appinfo_%02x.vdf" % shard)
                            if not os.path.isfile(f):
                                f = os.path.join(shard_dir, "appinfo_%02X.vdf" % shard)
                            if os.path.isfile(f):
                                found.update(_read_appinfo_shard(f, ids))
                    elif stamp:
                        found = _read_appinfo_single(single, appids)
                except (OSError, ValueError, IndexError) as err:
                    log.warning("cannot read Steam game info: %s", err)
                self.cache = found
                self.stamp = stamp
            result = dict(self.cache)
        # Unknown here: ask the Steam store once (in the background, cached on disk)
        missing = [a for a in appids if not (result.get(a) or {}).get("controller")]
        for a in missing:
            s = self.store.get(a)
            if s:
                merged = dict(result.get(a) or {"controller": None, "deck": None})
                if not merged.get("controller"):
                    merged["controller"] = s.get("controller")
                result[a] = merged
        return result


class StoreTraits:
    """Fallback: controller support from the Steam store (internet), remembered on disk."""

    def __init__(self):
        base = os.environ.get("LOCALAPPDATA") if IS_WINDOWS else os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        self.path = os.path.join(base or os.path.expanduser("~"), "kos", "store-traits.json")
        self.lock = threading.Lock()
        self.data = {}
        self.pending = set()
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (OSError, ValueError):
            self.data = {}

    def get(self, appid):
        key = str(appid)
        with self.lock:
            entry = self.data.get(key)
            if entry and time.time() - entry.get("t", 0) < 30 * 86400:
                return entry
            if key in self.pending:
                return entry
            self.pending.add(key)
        threading.Thread(target=self._fetch, args=(appid,), daemon=True).start()
        return entry

    def _fetch(self, appid):
        from urllib.request import Request, urlopen
        key = str(appid)
        ctl = None
        try:
            req = Request("https://store.steampowered.com/api/appdetails?appids=%d&l=english" % appid,
                          headers={"User-Agent": "K.OS Home"})
            with urlopen(req, timeout=8) as r:
                body = json.loads(r.read().decode("utf-8", "replace"))
            d = (body.get(key) or {}).get("data") or {}
            ctl = d.get("controller_support")
            if not ctl:
                cats = {c.get("id") for c in d.get("categories") or []}
                ctl = "full" if 28 in cats else "partial" if 18 in cats else "none"
            ok = True
        except Exception as e:  # noqa: BLE001 (offline, blocked, odd answer: try again later)
            log.info("store info for %d not available: %s", appid, e)
            ok = False
        with self.lock:
            self.pending.discard(key)
            if ok:
                self.data[key] = {"controller": ctl, "t": int(time.time())}
                try:
                    os.makedirs(os.path.dirname(self.path), exist_ok=True)
                    tmp = self.path + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(self.data, f)
                    os.replace(tmp, self.path)
                except OSError:
                    pass


# ---------------------------------------------------------------- running game (K.OS only)

def _proc_cmdline(pid):
    try:
        with open("/proc/%s/cmdline" % pid, "rb") as f:
            return f.read().split(b"\x00")
    except OSError:
        return []


def running_steam_games():
    """{appid: [reaper pids]} for games Steam is running right now. Every game Steam
    starts on Linux runs under a small 'reaper SteamLaunch AppId=<id>' process."""
    found = {}
    if IS_WINDOWS:
        return found
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return found
    for pid in pids:
        args = _proc_cmdline(pid)
        if b"SteamLaunch" not in args:
            continue
        for a in args:
            if a.startswith(b"AppId="):
                appid = to_int(a[6:].decode("ascii", "ignore"))
                if appid > 0 and appid not in TOOL_APPIDS:
                    found.setdefault(appid, []).append(int(pid))
                break
    return found


def _children_map():
    kids = {}
    try:
        for p in os.listdir("/proc"):
            if not p.isdigit():
                continue
            try:
                with open("/proc/%s/stat" % p, "r") as f:
                    stat = f.read()
                ppid = int(stat[stat.rindex(")") + 2:].split()[1])
                kids.setdefault(ppid, []).append(int(p))
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return kids


def close_steam_game(appid):
    """Ends a running Steam game: asks every process of the game to close, then
    forces whatever is still running after 6 seconds."""
    import signal
    reapers = running_steam_games().get(appid) or []
    if not reapers:
        return False
    kids = _children_map()
    tree = []
    todo = list(reapers)
    while todo:
        p = todo.pop()
        if p in tree:
            continue
        tree.append(p)
        todo.extend(kids.get(p, []))
    me = os.getpid()
    victims = [p for p in tree if p != me]
    # Children first, the reaper last, so Steam sees a normal game end
    for p in reversed(victims):
        try:
            os.kill(p, signal.SIGTERM)
        except OSError:
            pass

    def finish():
        time.sleep(6)
        for p in reversed(victims):
            try:
                os.kill(p, signal.SIGKILL)
            except OSError:
                pass
    threading.Thread(target=finish, daemon=True).start()
    return True


def kwin_shortcut(name):
    """Runs one of the K.OS window actions in the K.OS Console KWin script
    (KOS Show Home, KOS Toggle Home, KOS Resume Game). K.OS only."""
    if IS_WINDOWS or not shutil.which("gdbus"):
        return False
    base = ["gdbus", "call", "--session", "--dest", "org.kde.kglobalaccel",
            "--object-path", "/component/kwin",
            "--method", "org.kde.kglobalaccel.Component.invokeShortcut", "'%s'" % name]
    for extra in ([], ["'default'"]):
        try:
            r = subprocess.run(base + extra, capture_output=True, timeout=5)
            if r.returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass
    log.info("window action %s failed", name)
    return False


# ---------------------------------------------------------------- controller layouts
# K.OS owns the controller (/usr/libexec/kos-input): every button can send a
# controller button, a keyboard key or a mouse click, per game. The helper keeps
# the layouts and tells kos-input which one to use right now.

PAD_BUTTONS = ["A", "B", "X", "Y", "LB", "RB", "LT", "RT", "VIEW", "MENU", "LS", "RS", "UP", "DOWN", "LEFT", "RIGHT"]
PAD_TARGETS = ["A", "B", "X", "Y", "LB", "RB", "VIEW", "MENU", "LS", "RS"]
KEY_TARGETS = [
    "KEY_ESC", "KEY_ENTER", "KEY_SPACE", "KEY_TAB", "KEY_BACKSPACE", "KEY_LEFTSHIFT", "KEY_LEFTCTRL",
    "KEY_LEFTALT", "KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "KEY_W", "KEY_A", "KEY_S", "KEY_D",
    "KEY_Q", "KEY_E", "KEY_R", "KEY_F", "KEY_Z", "KEY_X", "KEY_C", "KEY_V", "KEY_I", "KEY_M", "KEY_P",
    "KEY_1", "KEY_2", "KEY_3", "KEY_4", "KEY_F1", "KEY_F5", "KEY_F9", "KEY_PAGEUP", "KEY_PAGEDOWN",
]
MOUSE_TARGETS = ["left", "right", "middle"]
STICK_LEFT = ["pad", "arrows", "wasd"]
STICK_RIGHT = ["pad", "mouse"]


def valid_target(t, allow_empty=True):
    if t is None or t == "":
        return allow_empty
    if t == "none":
        return True
    kind, _, val = str(t).partition(":")
    return ((kind == "pad" and val in PAD_TARGETS) or (kind == "key" and val in KEY_TARGETS)
            or (kind == "mouse" and val in MOUSE_TARGETS))


def preset_standard():
    """Every button does what it says. (Xbox button + View = Escape always works,
    see kos-input.)"""
    b = {n: {"tap": "", "hold": None} for n in PAD_BUTTONS}
    return {"buttons": b, "leftStick": "pad", "rightStick": "pad"}


def preset_keyboard():
    """For games made for keyboard and mouse."""
    m = {
        "A": "key:KEY_ENTER", "B": "key:KEY_ESC", "X": "key:KEY_Z", "Y": "key:KEY_X",
        "LB": "key:KEY_Q", "RB": "key:KEY_E", "LT": "key:KEY_LEFTSHIFT", "RT": "key:KEY_LEFTCTRL",
        "VIEW": "key:KEY_TAB", "MENU": "key:KEY_ESC", "LS": "key:KEY_LEFTSHIFT", "RS": "mouse:left",
        "UP": "key:KEY_UP", "DOWN": "key:KEY_DOWN", "LEFT": "key:KEY_LEFT", "RIGHT": "key:KEY_RIGHT",
    }
    b = {n: {"tap": m.get(n, ""), "hold": None} for n in PAD_BUTTONS}
    return {"buttons": b, "leftStick": "arrows", "rightStick": "mouse"}


def clean_layout(raw, fallback):
    """Keeps only known buttons and allowed actions; anything else uses the fallback."""
    out = json.loads(json.dumps(fallback))
    if not isinstance(raw, dict):
        return out
    btns = raw.get("buttons") if isinstance(raw.get("buttons"), dict) else {}
    for n in PAD_BUTTONS:
        v = btns.get(n)
        if isinstance(v, dict):
            if valid_target(v.get("tap")):
                out["buttons"][n]["tap"] = v.get("tap") or ""
            if v.get("hold") is None or valid_target(v.get("hold"), allow_empty=False):
                out["buttons"][n]["hold"] = v.get("hold")
    if raw.get("leftStick") in STICK_LEFT:
        out["leftStick"] = raw["leftStick"]
    if raw.get("rightStick") in STICK_RIGHT:
        out["rightStick"] = raw["rightStick"]
    return out


class Controller:
    MODES = ("auto", "standard", "keyboard", "custom")

    def __init__(self):
        base = os.environ.get("APPDATA") if IS_WINDOWS else os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        self.dir = os.path.join(base or os.path.expanduser("~"), "kos")
        self.path = os.path.join(self.dir, "controller.json")
        self.active_path = os.path.join(self.dir, "controller-active.json")
        self.lock = threading.Lock()
        self.active_key = None

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            raw = {}
        cfg = {
            "enabled": raw.get("enabled", True) is not False,
            "standard": clean_layout(raw.get("standard"), preset_standard()),
            "keyboard": clean_layout(raw.get("keyboard"), preset_keyboard()),
            "games": {},
        }
        games = raw.get("games") if isinstance(raw.get("games"), dict) else {}
        for k, v in games.items():
            if not str(k).isdigit() or not isinstance(v, dict):
                continue
            mode = v.get("mode") if v.get("mode") in self.MODES else "auto"
            entry = {"mode": mode}
            if isinstance(v.get("layout"), dict):
                entry["layout"] = clean_layout(v["layout"], preset_standard())
            cfg["games"][str(k)] = entry
        return cfg

    def save(self, raw):
        cur = self.load()
        if isinstance(raw, dict):
            if "enabled" in raw:
                cur["enabled"] = raw["enabled"] is not False
            for name in ("standard", "keyboard"):
                if isinstance(raw.get(name), dict):
                    cur[name] = clean_layout(raw[name], preset_standard() if name == "standard" else preset_keyboard())
            if isinstance(raw.get("games"), dict):
                for k, v in raw["games"].items():
                    if not str(k).isdigit():
                        continue
                    if v is None:
                        cur["games"].pop(str(k), None)
                        continue
                    if not isinstance(v, dict):
                        continue
                    entry = {"mode": v.get("mode") if v.get("mode") in self.MODES else "auto"}
                    if isinstance(v.get("layout"), dict):
                        entry["layout"] = clean_layout(v["layout"], preset_standard())
                    elif isinstance((cur["games"].get(str(k)) or {}).get("layout"), dict):
                        entry["layout"] = cur["games"][str(k)]["layout"]
                    cur["games"][str(k)] = entry
            if raw.get("reset") in ("standard", "keyboard"):
                cur[raw["reset"]] = preset_standard() if raw["reset"] == "standard" else preset_keyboard()
        self._write(self.path, cur)
        return cur

    def resolve(self, appid, traits):
        """Layout to use while `appid` runs (None = no game)."""
        cfg = self.load()
        if not appid:
            return cfg, "standard", cfg["standard"]
        g = cfg["games"].get(str(appid)) or {"mode": "auto"}
        mode = g["mode"]
        if mode == "custom" and isinstance(g.get("layout"), dict):
            return cfg, "game", g["layout"]
        if mode == "auto":
            mode = "keyboard" if (traits or {}).get("controller") == "none" else "standard"
        if mode == "keyboard":
            return cfg, "keyboard", cfg["keyboard"]
        return cfg, "standard", cfg["standard"]

    def apply(self, appid, traits, force=False):
        with self.lock:
            cfg, source, layout = self.resolve(appid, traits)
            active = {"enabled": cfg["enabled"], "appid": appid or None, "source": source, "layout": layout}
            key = json.dumps(active, sort_keys=True)
            if key == self.active_key and not force:
                return active
            self._write(self.active_path, active)
            self.active_key = key
            log.info("controller layout: %s (game %s)", source, appid or "-")
            return active

    def _write(self, path, data):
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, path)
        except OSError as e:
            log.warning("cannot save %s: %s", path, e)


def input_layer_status():
    """What /usr/libexec/kos-input reports (K.OS only)."""
    try:
        with open("/run/kos-input/status.json", "r", encoding="utf-8") as f:
            st = json.load(f)
        st["fresh"] = time.time() - float(st.get("time", 0)) < 15
        return st
    except (OSError, ValueError):
        return {"running": False, "fresh": False, "pads": []}


class GameWatcher:
    """K.OS only: notices when a Steam game starts or ends. While a game runs its
    controller layout is active; when it ends, K.OS Home comes back to the front."""

    def __init__(self, server):
        self.server = server
        self.current = None
        self.lock = threading.Lock()

    def running(self):
        with self.lock:
            return self.current

    def loop(self):
        while True:
            try:
                games = running_steam_games()
                appid = next(iter(sorted(games)), None) if games else None
                with self.lock:
                    before = self.current
                    self.current = appid
                if appid != before:
                    traits = self.server.traits_for(appid) if appid else None
                    self.server.controller.apply(appid, traits)
                    if before and not appid:
                        log.info("game %s ended, back to K.OS Home", before)
                        kwin_shortcut("KOS Show Home")
                    elif appid:
                        log.info("game %s running", appid)
            except Exception as e:  # noqa: BLE001 (never let the watcher die)
                log.warning("game watcher: %s", e)
            time.sleep(1.0)



# ---------------------------------------------------------------- Quick Menu (K.OS only)
# Sound, microphone, internet, controller batteries, downloads, K.OS updates,
# screenshots and power, for the Quick Menu (Xbox button) and K.OS Home.

def _run(cmd, timeout=3):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (OSError, subprocess.SubprocessError):
        return 1, ""


def _volume(target):
    code, out = _run(["wpctl", "get-volume", target])
    m = re.search(r"Volume:\s*([0-9.]+)", out or "")
    if code != 0 or not m:
        return None
    return {"volume": round(float(m.group(1)), 2), "muted": "[MUTED]" in out}


def sound_outputs():
    """Speakers, TV and headphones PipeWire knows about (wpctl status, Audio > Sinks)."""
    code, out = _run(["wpctl", "status"])
    outs = []
    section = None
    in_audio = False
    for line in (out or "").splitlines():
        clean = line.replace("│", " ").replace("├", " ").replace("└", " ").replace("─", " ").rstrip()
        if not clean.strip():
            continue
        if not line.startswith((" ", "│", "├", "└")):
            in_audio = clean.strip() == "Audio"
            continue
        head = clean.strip()
        if head.endswith(":"):
            section = head[:-1]
            continue
        if in_audio and section == "Sinks":
            m = re.match(r"^\s*(\*)?\s*(\d+)\.\s+(.*?)\s*(\[vol:[^\]]*\])?\s*$", clean)
            if m:
                outs.append({"id": int(m.group(2)), "name": m.group(3).strip(), "default": bool(m.group(1))})
    return outs


def sound_state():
    if IS_WINDOWS or not shutil.which("wpctl"):
        return None
    st = _volume("@DEFAULT_AUDIO_SINK@") or {"volume": None, "muted": False}
    st["outputs"] = sound_outputs()
    mic = _volume("@DEFAULT_AUDIO_SOURCE@")
    st["mic"] = mic
    return st


def sound_change(body):
    if IS_WINDOWS or not shutil.which("wpctl"):
        return False
    ok = True
    if "volume" in body:
        try:
            v = max(0.0, min(1.0, float(body["volume"])))
        except (TypeError, ValueError):
            return False
        ok = _run(["wpctl", "set-volume", "-l", "1.0", "@DEFAULT_AUDIO_SINK@", "%.2f" % v])[0] == 0 and ok
    if body.get("mute") in ("toggle", True, False):
        val = "toggle" if body["mute"] == "toggle" else ("1" if body["mute"] else "0")
        ok = _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", val])[0] == 0 and ok
    if body.get("micMute") in ("toggle", True, False):
        val = "toggle" if body["micMute"] == "toggle" else ("1" if body["micMute"] else "0")
        ok = _run(["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", val])[0] == 0 and ok
    if "output" in body:
        out_id = to_int(body["output"])
        if out_id <= 0 or out_id not in {o["id"] for o in sound_outputs()}:
            return False
        ok = _run(["wpctl", "set-default", str(out_id)])[0] == 0 and ok
    return ok


def net_state():
    if IS_WINDOWS or not shutil.which("nmcli"):
        return None
    st = {"type": None, "name": "", "signal": None, "online": None}
    _, out = _run(["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "device"])
    for line in (out or "").splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3 and parts[1] == "connected" and parts[0] in ("ethernet", "wifi"):
            if st["type"] != "ethernet":  # cable wins
                st["type"], st["name"] = parts[0], parts[2].replace("\\:", ":")
    if st["type"] == "wifi":
        _, out = _run(["nmcli", "-t", "-f", "IN-USE,SIGNAL", "device", "wifi", "list", "--rescan", "no"])
        for line in (out or "").splitlines():
            if line.startswith("*:"):
                st["signal"] = to_int(line.split(":")[1], None)
    _, out = _run(["nmcli", "-t", "-f", "CONNECTIVITY", "general"])
    st["online"] = (out or "").strip() or None
    return st


def controller_batteries():
    """Battery of controllers (and other wireless devices) the system reports."""
    found = []
    base = "/sys/class/power_supply"
    if IS_WINDOWS or not os.path.isdir(base):
        return found
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)

        def rd(f):
            try:
                with open(os.path.join(d, f), "r") as fh:
                    return fh.read().strip()
            except OSError:
                return ""
        if rd("scope").lower() != "device":
            continue
        cap = rd("capacity")
        found.append({"name": rd("model_name") or name, "percent": to_int(cap, None) if cap else None,
                      "level": rd("capacity_level"), "status": rd("status")})
    return found


_update_cache = {"t": 0.0, "v": None}


def kos_update_state():
    """Is a K.OS update downloaded and waiting for a restart? (rpm-ostree)"""
    if IS_WINDOWS or not shutil.which("rpm-ostree"):
        return None
    if time.time() - _update_cache["t"] < 120:
        return _update_cache["v"]
    code, out = _run(["rpm-ostree", "status", "--json"], timeout=8)
    v = None
    if code == 0:
        try:
            deps = json.loads(out).get("deployments", [])
            booted = next((d for d in deps if d.get("booted")), {})
            staged = next((d for d in deps if d.get("staged")), None)
            v = {"version": booted.get("version") or "", "ready": bool(staged),
                 "readyVersion": (staged or {}).get("version") or ""}
        except ValueError:
            v = None
    _update_cache.update(t=time.time(), v=v)
    return v


def pictures_dir():
    code, out = _run(["xdg-user-dir", "PICTURES"])
    base = out.strip() if code == 0 and out.strip() else os.path.expanduser("~/Pictures")
    return os.path.join(base, "K.OS")


def take_screenshot(delay=0.8):
    """Saves a picture of the screen (after the Quick Menu has closed)."""
    if IS_WINDOWS or not shutil.which("spectacle"):
        return None
    folder = pictures_dir()
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, time.strftime("K.OS %Y-%m-%d %H-%M-%S.png"))

    def shoot():
        time.sleep(delay)
        _run(["spectacle", "--background", "--nonotify", "--fullscreen", "--output", path], timeout=15)
        log.info("screenshot %s", path if os.path.exists(path) else "failed")
    threading.Thread(target=shoot, daemon=True).start()
    return path


def power_action(kind):
    if IS_WINDOWS:
        return False
    cmd = {"sleep": ["systemctl", "suspend"], "restart": ["systemctl", "reboot"],
           "off": ["systemctl", "poweroff"], "windows": ["/usr/bin/kos-boot-windows"]}.get(kind)
    if not cmd:
        return False
    run_detached(cmd)
    return True

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
    if app_id in WEBAPP_NAMES:
        proc = subprocess.Popen([exe] + cmd[1:], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, start_new_session=True)
        with WEBAPPS_LOCK:
            WEBAPPS[app_id] = proc
    else:
        run_detached([exe] + cmd[1:])
    return True, None


WEBAPP_NAMES = {"netflix": "Netflix", "hbomax": "HBO Max", "xcloud": "Xbox Bulut Oyun", "browser": "İnternet"}
WEBAPPS = {}
WEBAPPS_LOCK = threading.Lock()


def open_webapps():
    """K.OS web apps that are still open, newest first."""
    with WEBAPPS_LOCK:
        for k in [k for k, p in WEBAPPS.items() if p.poll() is not None]:
            WEBAPPS.pop(k)
        return [{"id": k, "name": WEBAPP_NAMES[k]} for k in reversed(list(WEBAPPS))]


def close_webapp(app_id):
    import signal
    with WEBAPPS_LOCK:
        p = WEBAPPS.get(app_id)
    if not p or p.poll() is not None:
        return False
    try:
        os.killpg(p.pid, signal.SIGTERM)
    except OSError:
        p.terminate()
    return True


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

        if path == "/api/running":
            appid = self.server.watcher.running()
            self.send_json({"ok": True, "appid": appid,
                            "name": self.server.game_name(appid) if appid else ""})
            return

        if path == "/api/quick":
            self.send_json(self.server.quick_state())
            return

        if path == "/api/controller":
            ctl = self.server.controller
            self.send_json({"ok": True, "config": ctl.load(), "status": input_layer_status(),
                            "options": {"buttons": PAD_BUTTONS, "pad": PAD_TARGETS, "keys": KEY_TARGETS,
                                        "mouse": MOUSE_TARGETS, "leftStick": STICK_LEFT, "rightStick": STICK_RIGHT},
                            "presets": {"standard": preset_standard(), "keyboard": preset_keyboard()}})
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
        body = self.rfile.read(min(length, 262144)) if length else b""
        # The custom header stops other web sites from sending these requests
        if not self.allowed() or self.headers.get("X-KOS") != "1":
            self.send_json({"ok": False, "error": "forbidden"}, 403)
            return
        path = urlparse(self.path).path

        m = re.match(r"^/api/launch/(\d{1,10})$", path)
        if m:
            appid = int(m.group(1))
            try:
                # The game's controller layout is ready before the game opens
                self.server.controller.apply(appid, self.server.traits_for(appid))
                open_steam_url("steam://rungameid/%d" % appid)
                log.info("launch %d", appid)
                self.send_json({"ok": True})
            except Exception as e:  # noqa: BLE001 (report any failure to the launcher)
                log.warning("launch %d failed: %s", appid, e)
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        if path in ("/api/sound", "/api/webapp/close", "/api/screenshot") or path.startswith("/api/power/"):
            try:
                data = json.loads(body.decode("utf-8") or "{}")
            except ValueError:
                data = {}
            if not isinstance(data, dict):
                data = {}
            if path == "/api/sound":
                self.send_json({"ok": sound_change(data), "sound": sound_state()})
            elif path == "/api/webapp/close":
                self.send_json({"ok": close_webapp(str(data.get("id", "")))})
            elif path == "/api/screenshot":
                shot = take_screenshot()
                self.send_json({"ok": bool(shot), "path": shot})
            else:
                self.send_json({"ok": power_action(path.rsplit("/", 1)[1])})
            return

        if path == "/api/game/resume":
            self.send_json({"ok": kwin_shortcut("KOS Resume Game")})
            return

        if path == "/api/game/close":
            appid = self.server.watcher.running()
            self.send_json({"ok": bool(appid) and close_steam_game(appid)})
            return

        if path == "/api/controller":
            try:
                raw = json.loads(body.decode("utf-8") or "{}")
            except ValueError:
                self.send_json({"ok": False, "error": "bad json"}, 400)
                return
            ctl = self.server.controller
            cfg = ctl.save(raw)
            appid = self.server.watcher.running()
            ctl.apply(appid, self.server.traits_for(appid) if appid else None, force=True)
            self.send_json({"ok": True, "config": cfg})
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
        self.controller = Controller()
        self.watcher = GameWatcher(self)
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

    def traits_for(self, appid):
        for g in self.steam.snapshot().get("games", []):
            if g["appid"] == appid:
                return {"controller": g.get("controller"), "deck": g.get("deck")}
        return None

    def quick_state(self):
        """Everything the Quick Menu shows, in one answer."""
        snap = self.steam.snapshot()
        appid = self.watcher.running()
        game = None
        if appid:
            g = next((x for x in snap.get("games", []) if x["appid"] == appid), None) or {}
            cfg = self.controller.load()
            mode = (cfg["games"].get(str(appid)) or {}).get("mode", "auto")
            game = {"appid": appid, "name": g.get("name") or "Oyun", "controller": g.get("controller"),
                    "deck": g.get("deck"), "playtimeMin": g.get("playtimeMin", 0), "layoutMode": mode}
        layer = input_layer_status()
        return {"ok": True, "platform": "windows" if IS_WINDOWS else "linux", "game": game,
                "webapps": open_webapps(), "sound": sound_state(), "net": net_state(),
                "batteries": controller_batteries(), "pads": layer.get("pads", []) if layer.get("fresh") else [],
                "layer": {"running": bool(layer.get("fresh")), "enabled": layer.get("enabled", True)},
                "downloads": snap.get("downloads", []), "update": kos_update_state(), "time": int(time.time())}

    def game_name(self, appid):
        for g in self.steam.snapshot().get("games", []):
            if g["appid"] == appid:
                return g["name"]
        return ""


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

    if not IS_WINDOWS:
        server.controller.apply(None, None, force=True)
        threading.Thread(target=server.watcher.loop, daemon=True).start()

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
