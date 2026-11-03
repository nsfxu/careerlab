"""Where the game, its saves and the database dump live, so an installed CareerLab works
on any PC. Settings are kept in %LOCALAPPDATA%\\CareerLab\\config.json, one block per game:

    {"game": "fl27",
     "games": {"fl26": {"gameDir": "E:\\FL2026", "saveDir": "...\\2026\\save"},
               "fl27": {"gameDir": "E:\\SP Football Life 2027", "keyFile": "..."}}}

(Before FL27 support the FL26 paths sat at the top level; `load` moves them.)

The database dump comes from the DBDump.lua Sider module (shipped with CareerLab in
fl26/assets): it writes <name>.copyN.raw into SiderAddons\\dbdump each time the game
starts. The highest copy is the patched database the game really uses.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import string
import sys
import time
from pathlib import Path

from . import crypto, i18n
from .games import GAMES, FL26
from .i18n import tr

# CAREERLAB_HOME: a sandbox for UI tests (LOCALAPPDATA can't be moved: Python lives there)
HOME = Path(os.environ.get("CAREERLAB_HOME") or Path(os.environ.get("LOCALAPPDATA", ".")) / "CareerLab")
CONFIG = HOME / "config.json"
TABLES = ("player", "team", "playerassignment", "playerappearance")
MODULE = "DBDump.lua"


def load():
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    legacy = {k: cfg.pop(k) for k in ("gameDir", "saveDir") if k in cfg}
    if legacy:
        cfg.setdefault("games", {}).setdefault("fl26", {}).update(legacy)
    return cfg


def save(cfg):
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=1), encoding="utf-8")


def _game_cfg(g, cfg=None):
    return (cfg or load()).get("games", {}).get(g.id, {})


def _set(g, **values):
    cfg = load()
    cfg.setdefault("games", {}).setdefault(g.id, {}).update(values)
    save(cfg)


# ------------------------------------------------------------------ the active game

_game = None                 # the answer of game(), until set_game changes it


def game():
    """The game being edited: the one chosen in settings; else FL26 for a CareerLab set up
    before FL27 support, while FL26 is still installed; else the newest game installed."""
    global _game
    if _game is None:
        cfg = load()
        if cfg.get("game") in GAMES:
            _game = GAMES[cfg["game"]]
        elif _game_cfg(FL26, cfg) and detect_game_dir(FL26):
            _game = FL26
        else:
            newest = list(GAMES.values())[::-1]
            _game = next((g for g in newest if detect_game_dir(g)), FL26 if _game_cfg(FL26, cfg) else newest[0])
        i18n.GAME = _game.short
    return _game


def set_game(gid):
    global _game
    if gid not in GAMES:
        raise ValueError(f"unknown game {gid}")
    cfg = load()
    cfg["game"] = gid
    save(cfg)
    _game = None
    return game()


def data_dir(g=None):
    """Install-wide files CareerLab keeps per game (image cache, spare IDs). FL26 keeps the
    top folder, where they were before FL27 support."""
    g = g or game()
    return HOME if g is FL26 else HOME / g.id


# ------------------------------------------------------------------ folders

def is_game_dir(p, g=None):
    return bool(p) and (Path(p) / (g or game()).exe).is_file()


def detect_game_dir(g=None):
    """The configured folder, else the usual install places on every drive."""
    g = g or game()
    cfg = _game_cfg(g).get("gameDir")
    if is_game_dir(cfg, g):
        return Path(cfg)
    for d in string.ascii_uppercase:
        root = Path(f"{d}:\\")
        if not root.exists():
            continue
        for n in g.folders:
            if is_game_dir(root / n, g):
                return root / n
    return None


def game_dir(g=None):
    return detect_game_dir(g)


def set_game_dir(p):
    g = game()
    if not is_game_dir(p, g):
        raise ValueError(tr("err.noExe", exe=g.exe))
    _set(g, gameDir=str(Path(p)))
    return Path(p)


def save_dir(g=None):
    g = g or game()
    p = _game_cfg(g).get("saveDir")
    return Path(p) if p and Path(p).is_dir() else g.save_dir


def set_save_dir(p):
    if not Path(p).is_dir():
        raise ValueError(tr("err.noFolder"))
    _set(game(), saveDir=str(Path(p)))


def dump_dir():
    g = game_dir()
    return g / "SiderAddons" / "dbdump" if g else None


# ------------------------------------------------------------------ save keys

def _key_opens(key, folder):
    """True if `key` opens a save in `folder`, None if the folder has no save to try."""
    tried = False
    for f in sorted(Path(folder).glob("*0000000*")) if Path(folder).is_dir() else []:
        try:
            with open(f, "rb") as fh:
                head = fh.read(crypto.ENC_HEADER_SIZE + crypto.FILE_HEADER_SIZE)
            crypto._open_headers(head, [key])
            return True
        except crypto.UnknownKey:
            tried = True
        except OSError:
            continue
    return False if tried else None


def _key_candidates(g):
    own = _game_cfg(g).get("keyFile")
    gd = game_dir(g)
    home = Path(os.path.expanduser("~"))
    places = [own, data_dir(g) / g.key_file, HOME / g.key_file]
    if gd:
        places += [gd / g.key_file, gd / "Data" / g.key_file]
    places += [home / "Downloads" / g.key_file, home / "Desktop" / g.key_file]
    return [Path(p) for p in places if p]


def find_key(g=None):
    """Path of a usable key file for `g` (None if it needs none or none was found). A
    candidate must be 64 bytes and, when the save folder has saves, open one of them."""
    g = g or game()
    if not g.key_file:
        return None
    for p in _key_candidates(g):
        try:
            key = p.read_bytes()
        except OSError:
            continue
        if len(key) == 64 and key not in crypto.KNOWN_KEYS[:1] and _key_opens(key, save_dir(g)) is not False:
            return p
    return None


def register_keys():
    """Teach crypto every game's key we can find, so any save in any game opens."""
    found = {}
    for g in GAMES.values():
        if g.key_file:
            p = find_key(g)
            if p:
                crypto.add_key(p.read_bytes())
            found[g.id] = str(p) if p else None
    return found


def set_key_file(path):
    """Keep a copy of the user's key file in CareerLab's folder for this game."""
    g = game()
    key = Path(path).read_bytes()
    if len(key) != 64 or _key_opens(key, save_dir(g)) is False:
        raise ValueError(tr("err.badKey", game=g.name))
    dest = data_dir(g) / g.key_file
    dest.parent.mkdir(parents=True, exist_ok=True)
    if Path(path).resolve() != dest.resolve():
        shutil.copyfile(path, dest)
    _set(g, keyFile=str(dest))
    crypto.add_key(key)
    return dest


# ------------------------------------------------------------------ database dump

def table_file(name, d=None):
    """Newest dump of a table: highest <name>.copyN.raw, else the plain <name>.raw."""
    d = Path(d) if d else dump_dir()
    if d is None:
        raise FileNotFoundError(f"the {game().name} game folder is not set")
    copies = []
    for f in d.glob(f"{name}.copy*.raw"):
        m = re.fullmatch(rf"{re.escape(name)}\.copy(\d+)\.raw", f.name)
        if m:
            copies.append((int(m.group(1)), f))
    if copies:
        return max(copies)[1]
    f = d / f"{name}.raw"
    if not f.exists():
        raise FileNotFoundError(f"database dump {name} not found in {d}")
    return f


def dump_ok(d=None):
    try:
        return all(table_file(t, d).stat().st_size > 0 for t in TABLES)
    except (FileNotFoundError, OSError):
        return False


def asset(name):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    for p in (base / "fl26" / "assets" / name, Path(__file__).parent / "assets" / name):
        if p.exists():
            return p
    raise FileNotFoundError(name)


def module_installed(g=None):
    g = Path(g) if g else game_dir()
    if not g:
        return False
    ini = g / "SiderAddons" / "sider.ini"
    try:
        text = ini.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    active = any(re.match(rf'\s*lua\.module\s*=\s*"{MODULE}"', line) for line in text.splitlines())
    return active and (g / "SiderAddons" / "modules" / MODULE).exists()


def install_module(g=None):
    """Copy DBDump.lua into SiderAddons\\modules and enable it in sider.ini (a backup of
    sider.ini is kept beside it). The module only reads; it never changes game files."""
    g = Path(g) if g else game_dir()
    if not g:
        raise FileNotFoundError(f"the {game().name} game folder is not set")
    sider = g / "SiderAddons"
    ini = sider / "sider.ini"
    if not ini.exists():
        raise FileNotFoundError("Sider is not installed in this game folder (SiderAddons\\sider.ini missing)")
    (sider / "modules").mkdir(exist_ok=True)
    (sider / "dbdump").mkdir(exist_ok=True)      # Sider's Lua can't create it: io.open just fails
    shutil.copyfile(asset(MODULE), sider / "modules" / MODULE)
    if not module_installed(g):
        raw = ini.read_bytes()                   # bytes: the ini's own encoding is kept
        shutil.copyfile(ini, ini.with_name(f"sider.ini.careerlab-{time.strftime('%Y%m%d-%H%M%S')}"))
        nl = b"\r\n" if b"\r\n" in raw else b"\n"
        lines = raw.splitlines()
        # after the last active lua.module line, so it loads with the others
        last = max((i for i, l in enumerate(lines)
                    if b"lua.module" in l and not l.lstrip().startswith(b";")),
                   default=len(lines) - 1)
        lines.insert(last + 1, f'\tlua.module = "{MODULE}"'.encode())
        ini.write_bytes(nl.join(lines) + nl)
    return module_installed(g)


def status():
    cur = game()
    g = game_dir()
    keys = register_keys()
    if g and module_installed(g) and not (g / "SiderAddons" / "dbdump").exists():
        (g / "SiderAddons" / "dbdump").mkdir()   # installed before install_module made it
    return {"game": cur.id, "gameName": cur.name, "exe": cur.exe,
            "games": [{"id": x.id, "name": x.name, "short": x.short, "installed": bool(detect_game_dir(x))}
                      for x in GAMES.values()],
            "gameDir": str(g) if g else None, "saveDir": str(save_dir()),
            "saveDirOk": save_dir().is_dir(), "dumpOk": dump_ok() if g else False,
            "moduleInstalled": module_installed(g) if g else False,
            "siderInstalled": bool(g) and (g / "SiderAddons" / "sider.ini").exists(),
            "keyNeeded": bool(cur.key_file), "keyFile": keys.get(cur.id), "keyName": cur.key_file,
            "keyOk": not cur.key_file or bool(keys.get(cur.id))}
