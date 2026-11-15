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


# ------------------------------------------------------------------ players FL27 lacks
#
# FL27's database dropped ~3,100 of FL26's players (retired, lower leagues). A career
# brought over still lists them; with no database entry their name renders as "Jogadores"
# (as in E19). The registry record decides who a player is (registry.py), so each one is
# re-pointed at an ID FL27 has, keeping his own record (ratings, career history):
#
# * re-ID: FL27 kept him under a new ID (same name and nationality, age within 2 years,
#   one candidate, no record of that ID in this career);
# * spare: else an ID FL27 lists as clubless (a free agent in every FL27 career) that no
#   squad here or in `other_squads` uses, renamed in the option file to his FL26 identity
#   (database record and appearance: E20's spare mechanism). The option file is shared by
#   every career of the game, which is why spares are clubless nobodies.

def _norm(name):
    import unicodedata
    return unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower().strip()


def missing_players(career, db):
    """Squad players (created character aside) whose ID `db` (the target game's) lacks."""
    from .career import CREATED_ID_MIN
    return sorted({p for cl in career.clubs() for _, p in cl.members
                   if p < CREATED_ID_MIN and p not in db.player_names})


def plan_repair(career, registry, db, src_db, other_squads=()):
    """{"reid": {old: new}, "spare": {old: spare}} for every squad player `db` lacks."""
    import collections
    from .career import CREATED_ID_MIN
    rec_of = {registry.pid(i): i for i in range(registry.count)}
    in_squad = {p for cl in career.clubs() for _, p in cl.members}
    idx = career.index()
    by_key = collections.defaultdict(list)
    for p, n in db.player_names.items():
        by_key[(_norm(n), db.player_nat.get(p))].append(p)
    reid, rest = {}, []
    for m in missing_players(career, db):
        cands = [q for q in by_key.get((_norm(src_db.player_names.get(m)), src_db.player_nat.get(m)), [])
                 if 0 <= db.player_age.get(q, 0) - src_db.player_age.get(m, 0) <= 2]
        if len(cands) == 1 and cands[0] not in rec_of and cands[0] not in reid.values():
            reid[m] = cands[0]
        else:
            rest.append(m)
    busy = in_squad | set(other_squads) | set(reid.values())
    pool = [p for p in db.player_names
            if p < CREATED_ID_MIN and p not in db.player_teams and p not in busy
            and sum(idx.get(p, {}).values()) <= 1]
    # IDs without a record here first: no record of this career has to give his ID up
    pool.sort(key=lambda p: (p in rec_of, p))
    if len(pool) < len(rest):
        raise ValueError(tr("err.noSpare"))
    return {"reid": reid, "spare": dict(zip(rest, pool))}


def apply_repair(career, registry, edit, plan, src_db, src_players, src_faces):
    """Carry out `plan_repair`'s plan on the career (registry and handle pairs) and the
    option file. Caller validates and writes both. Returns the number of pairs rewritten."""
    from .registry import OFF_PID, REC
    import struct
    rec_of = {registry.pid(i): i for i in range(registry.count)}
    idx = career.index()
    mapping = {}

    def repoint(old, new):
        i = rec_of[old]
        struct.pack_into("<I", registry.blob, i * REC + OFF_PID, new)
        for h in idx.get(old, {}):
            mapping[(h, old)] = (h, new)

    for old, new in plan["reid"].items():
        repoint(old, new)
    for old, spare in plan["spare"].items():
        if spare in rec_of:                      # the spare's own record takes the old ID
            repoint(spare, old)
        repoint(old, spare)
        rec = src_players[old]
        name = src_db.player_names[old]
        printed = bytes(rec[0x81:0x81 + 61]).split(b"\0")[0].decode("utf-8", "replace") or name.upper()
        edit.add_player(spare, name, printed, rec, src_faces[old])
    registry.commit()
    return career.swap_identity(mapping)
