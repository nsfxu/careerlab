"""Where the game, its saves and the database dump live, so an installed CareerLab works
on any PC. Settings are kept in %LOCALAPPDATA%\\CareerLab\\config.json:

    {"gameDir": "E:\\FL2026", "saveDir": "...\\2026\\save"}

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

from .i18n import tr

HOME = Path(os.environ.get("LOCALAPPDATA", ".")) / "CareerLab"
CONFIG = HOME / "config.json"
GAME_EXE = "FL_2026.exe"
DEFAULT_SAVE_DIR = Path(os.path.expanduser(
    r"~\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save"))
TABLES = ("player", "team", "playerassignment", "playerappearance")
MODULE = "DBDump.lua"


def load():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(cfg):
    HOME.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg, indent=1), encoding="utf-8")


def is_game_dir(p):
    return bool(p) and (Path(p) / GAME_EXE).is_file()


def detect_game_dir():
    """The configured folder, else the usual install places on every drive."""
    cfg = load().get("gameDir")
    if is_game_dir(cfg):
        return Path(cfg)
    names = ("FL2026", "FL 2026", "Football Life 2026", r"Games\FL2026", r"Games\Football Life 2026")
    for d in string.ascii_uppercase:
        root = Path(f"{d}:\\")
        if not root.exists():
            continue
        for n in names:
            if is_game_dir(root / n):
                return root / n
    return None


def game_dir():
    return detect_game_dir()


def set_game_dir(p):
    if not is_game_dir(p):
        raise ValueError(tr("err.noExe", exe=GAME_EXE))
    cfg = load()
    cfg["gameDir"] = str(Path(p))
    save(cfg)
    return Path(p)


def save_dir():
    p = load().get("saveDir")
    return Path(p) if p and Path(p).is_dir() else DEFAULT_SAVE_DIR


def dump_dir():
    g = game_dir()
    return g / "SiderAddons" / "dbdump" if g else None


def table_file(name, d=None):
    """Newest dump of a table: highest <name>.copyN.raw, else the plain <name>.raw."""
    d = Path(d) if d else dump_dir()
    if d is None:
        raise FileNotFoundError("the FL2026 game folder is not set")
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
        raise FileNotFoundError("the FL2026 game folder is not set")
    sider = g / "SiderAddons"
    ini = sider / "sider.ini"
    if not ini.exists():
        raise FileNotFoundError("Sider is not installed in this game folder (SiderAddons\\sider.ini missing)")
    (sider / "modules").mkdir(exist_ok=True)
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
    g = game_dir()
    return {"gameDir": str(g) if g else None, "saveDir": str(save_dir()),
            "saveDirOk": save_dir().is_dir(), "dumpOk": dump_ok() if g else False,
            "moduleInstalled": module_installed(g) if g else False,
            "siderInstalled": bool(g) and (g / "SiderAddons" / "sider.ini").exists()}
