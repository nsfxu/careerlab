"""Bring a Football Life 2026 career into Football Life 2027 (nsfxu/careerlab#1, E25).

FL27 reads FL26's career data as it is; three things stand in the way, all proven in game
on the user's 2030 career (2026-11-02):

* the save key: FL27 has its own (crypto.KNOWN_KEYS, config.find_key);
* the 320-byte encryption header: FL27 lists a file with FL26's as "dados corrompidos",
  even re-keyed. There is no known way to make one, so the header and FileHeader are
  borrowed from a career FL27 wrote itself (the "wrapper");
* the version stamp at data[12:24] (three u32): FL26 writes 260203,200,200 and FL27
  270100,100,100, else "os dados são de uma versão diferente". Copied from the wrapper, so a
  later FL27 patch's stamp follows along.

The FL26 description (player / club / date) and thumbnail are kept; the slot number in
its title follows the new slot. The FL26 file is only read. The new file goes into a free
slot only, so nothing is overwritten and no backup is needed.
"""
from __future__ import annotations

import re
from pathlib import Path

from . import safewrite
from .crypto import Save
from .games import FL26, FL27
from .i18n import tr

STAMP = slice(12, 24)
SLOTS = 8                    # Become a Legend slots looked at for a free one


def careers(folder, g):
    """[(path, peek info)] for the Become a Legend saves `g` wrote in `folder`."""
    out = []
    for p in sorted(Path(folder).glob("BL*")) if folder and Path(folder).is_dir() else []:
        try:
            info = Save.peek(p)
        except (OSError, ValueError):
            continue
        if info["kind"] == "BL" and info["game"] == g.header:
            out.append((p, info))
    return out


def wrapper(folder, target=FL27):
    """The most recently saved career `target` wrote in `folder`."""
    found = careers(folder, target)
    if not found:
        raise ValueError(tr("err.upgradeNoWrapper"))
    return Save.load(max(found, key=lambda c: c[0].stat().st_mtime)[0])


def free_slot(folder):
    for i in range(SLOTS):
        p = Path(folder) / f"BL{i:08d}"
        if not p.exists():
            return p
    raise ValueError(tr("err.upgradeNoSlot"))


def retitle(description, slot_path):
    """'Rumo ao Estrelato 02' -> the new slot's number, same width."""
    n = int(Path(slot_path).name[2:]) + 1
    title = bytes(description[:128]).split(b"\0")[0].decode("utf-8", "replace")
    new = re.sub(r"\d+\s*$", lambda m: f"{n:0{len(m.group().strip())}d}", title)
    return new.encode("utf-8")[:127].ljust(128, b"\0") + bytes(description[128:])


def build(src: Save, wrap: Save, dest) -> Save:
    data = bytearray(src.data)
    data[STAMP] = bytes(wrap.data)[STAMP]
    return Save(wrap.enc_header, wrap.file_header, retitle(src.description, dest), src.logo,
                bytes(data), wrap.serial, master=wrap.master)


def upgrade(src_path, folder, source=FL26, target=FL27):
    """Write `src_path` (an FL26 career) as a new FL27 career in `folder`. Returns its path."""
    if safewrite.game_running():
        raise safewrite.WriteRefused(tr("err.gameRunning"))
    try:
        src = Save.load(src_path)
    except ValueError:
        raise ValueError(tr("err.upgradeNotBl"))
    if src.kind != "BL" or src.game != source.header:
        raise ValueError(tr("err.upgradeNotBl"))
    wrap = wrapper(folder, target)
    dest = free_slot(folder)
    out = build(src, wrap, dest)
    dest.write_bytes(out.encrypt())
    back = Save.load(dest)
    if back.data != out.data or back.game != target.header:
        dest.unlink()
        raise safewrite.WriteRefused(tr("err.notVerified", name=dest.name))
    return dest
