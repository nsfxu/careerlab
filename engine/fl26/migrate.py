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
import struct
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


# ------------------------------------------------------------------ clubs FL27 lacks
#
# FL27 swapped 60 of FL26's clubs for 56 others; a career brought over still has the old
# ones, shown with no name and no crest. The database can't take them back (the game
# crashes loading a career once the team table passes 751 records, E27), so each one
# becomes a club FL27 added, preferably from the same competition: its name, crest, kits
# and stadium come with the ID, its squad and results stay the career's.
#
# Each club record (0x690 bytes from 0x50, the squad sits at +0x14C) starts with the u32
# key teamID << 14 | block. Every reference to the club uses that exact key (112 for
# FCV Dender, its 28 players' records included), so the key is swapped exactly. Plain
# team IDs appear too, in team lists (competition entries): those are swapped where the
# neighbouring words are club IDs as well, and a list that was sorted is sorted again.

CLUB_KEY_AT = 0x50
CLUB_KEY_STRIDE = 0x690
NO_TEAM = 0x3FFFF
NOT_CLUBS = range(900, 911)          # FL27's "Classics" exhibition sides


def club_keys(career):
    return [struct.unpack_from("<I", career.d, CLUB_KEY_AT + k * CLUB_KEY_STRIDE)[0]
            for k in range(len(career.clubs()))]


def plan_club_swap(career, db, src_db, src_comps, dst_comps):
    """{block: (old teamID, new teamID)} for each club `db` (the target game's) lacks.
    National teams are left alone (there is no club to become)."""
    teams = [k >> 14 for k in club_keys(career)]
    used = set(teams)
    free = [t for t in sorted(db.team_names) if t not in used and t not in db.national
            and t not in NOT_CLUBS and not db.team_names[t].startswith("ML Default")]
    gone = [(k, t) for k, t in enumerate(teams)
            if t != NO_TEAM and t not in db.team_names and t not in src_db.national]
    comp_of = lambda comps, t: sorted(c for c, ids in comps.items() if t in ids)
    plan = {}
    by_name = {_norm(db.team_names[f]): f for f in free}
    for k, t in gone:                         # the same club under a new ID
        f = by_name.get(_norm(src_db.team_names.get(t)))
        if f in free:
            plan[k] = (t, f)
            free.remove(f)
    for k, t in gone:                         # else a club of the same competition
        if k in plan:
            continue
        for comp in comp_of(src_comps, t):
            cand = [f for f in free if f in dst_comps.get(comp, ())]
            if cand:
                plan[k] = (t, cand[0])
                free.remove(cand[0])
                break
    for k, t in gone:                         # then any club FL27 added
        if k not in plan:
            if not free:
                raise ValueError("not enough clubs to swap in")
            plan[k] = (t, free.pop(0))
    return plan


def apply_club_swap(career, registry, plan):
    """Swap each planned club's key and team-list entries. Caller validates and writes.
    Returns {"keys": n, "lists": n} rewritten."""
    import numpy as np
    keys = club_keys(career)
    club_ids = {k >> 14 for k in keys} | {new for _, new in plan.values()}
    key_map = {keys[k]: (new << 14) | (keys[k] & 0x3FFF) for k, (old, new) in plan.items()}
    id_map = {old: new for old, new in plan.values()}
    # registry: the players' club fields hold the same keys
    blob = np.frombuffer(bytes(registry.blob), dtype="<u4").copy()
    for old, new in key_map.items():
        blob[blob == old] = new
    registry.blob[:] = blob.tobytes()
    registry.commit()
    a = np.frombuffer(bytes(career.d[:len(career.d) // 4 * 4]), dtype="<u4").copy()
    lo, hi = registry.start // 4, (registry.start + registry.size) // 4
    n_keys = 0
    for old, new in key_map.items():
        hit = np.nonzero(a == old)[0]
        hit = hit[(hit < lo) | (hit >= hi)]
        a[hit] = new
        n_keys += len(hit)
    def is_list(i):
        near = [int(a[j]) for j in (i - 2, i - 1, i + 1, i + 2) if 0 <= j < len(a) and not lo <= j < hi]
        return sum(x in club_ids or x == NO_TEAM for x in near) >= 2
    n_lists, touched = 0, []
    for old, new in id_map.items():
        for i in np.nonzero(a == old)[0].tolist():
            if not lo <= i < hi and is_list(i):
                a[i] = new
                n_lists += 1
                touched.append(i)
    # a team list that was sorted (before the swap) is sorted again
    for i in touched:
        s = i
        while s > 0 and (int(a[s - 1]) in club_ids or int(a[s - 1]) in id_map):
            s -= 1
        e = i
        while e + 1 < len(a) and (int(a[e + 1]) in club_ids or int(a[e + 1]) in id_map):
            e += 1
        run = [int(x) for x in a[s:e + 1]]
        before = [next((o for o, nw in id_map.items() if nw == x), x) for x in run]
        if len(run) >= 4 and before == sorted(before):
            a[s:e + 1] = sorted(run)
    career.d[:len(a) * 4] = a.tobytes()
    career.dirty()
    return {"keys": n_keys, "lists": n_lists}
