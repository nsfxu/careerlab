"""Build a career player profile (registry record) from efootballdb data.

The record's first 32 bytes decide the player in the career (position, abilities, skills,
style, age); the rest carries club context, which is taken from a teammate at the
destination club (the E07 recipe). Unknown bits start from the template's values.
"""
from __future__ import annotations

import statistics
import struct

from . import attributes as A
from .registry import REC
from .i18n import tr

# registry ability -> efootballdb field (correlation-matched over 285 players, r 0.77-0.99)
ABILITY_SOURCE = {
    "offensive_awareness": "attacking_prowess", "defensive_awareness": "defensive_prowess",
    "gk_awareness": "goalkeeping", "dribbling": "dribbling", "ball_control": "ball_control",
    "finishing": "finishing", "low_pass": "low_pass", "lofted_pass": "lofted_pass",
    "heading": "header", "ball_winning": "ball_winning", "place_kicking": "place_kicking",
    "curl": "swerve", "gk_catching": "catching", "gk_clearing": "clearing",
    "gk_reflexes": "reflexes", "gk_reach": "coverage", "speed": "speed",
    "physical_contact": "physical_contact", "balance": "body_control",
    "kicking_power": "kicking_power", "acceleration": "explosive_power", "jump": "jump",
    "stamina": "stamina", "tight_possession": "tight_possession", "aggression": "aggression",
}
SKILL_SOURCE = {k: k for k in A.SKILLS}
SKILL_SOURCE["gk_low_punt"] = "low_punt_trajectory"
SKILL_SOURCE["heading_skill"] = "heading"
POSITIONS = ["gk", "cb", "lb", "rb", "dmf", "cmf", "lmf", "rmf", "amf", "lwf", "rwf", "ss", "cf"]


def clamp(v, lo, hi):
    return max(lo, min(hi, int(v)))


def season_gap(registry, rec_of, efdb_players):
    """Years between efootballdb's ages and the career's: median over shared players."""
    gaps = []
    for p in efdb_players:
        i = rec_of.get(p["pes_id"])
        if i is not None and p.get("age"):
            gaps.append(A.get(registry.record(i), "age") - p["age"])
    return int(statistics.median(gaps)) if gaps else 0


def block_from_efdb(p, template_rec, gap=0):
    """The 32-byte profile block for efootballdb player `p`."""
    rec = bytearray(template_rec)
    for ab, src in ABILITY_SOURCE.items():
        if isinstance(p.get(src), int):
            A.set(rec, ab, clamp(p[src], 40, 99))
    for pos in POSITIONS:
        if isinstance(p.get(pos), int):
            A.set(rec, "pos_" + pos, clamp(p[pos], 0, 2))
    for sk, src in SKILL_SOURCE.items():
        A.set(rec, sk, 1 if p.get(src) else 0)
    if isinstance(p.get("main_position"), int):
        A.set(rec, "registered_position", clamp(p["main_position"], 0, 12))
    A.set(rec, "playing_style", A.style_from_efootballdb(p.get("playing_style"),
                                                         p.get("main_position") == 0))
    if p.get("age"):
        A.set(rec, "age", clamp(p["age"] + gap, 15, 63))
    for f in ("weak_foot_usage", "weak_foot_accuracy"):
        if isinstance(p.get(f), int):
            A.set(rec, f, clamp(p[f], 1, 4))
    if isinstance(p.get("form"), int):
        A.set(rec, "form", clamp(p["form"], 1, 8))
    return bytes(rec[:32])


def record_from_efdb(p, teammate_rec, gap=0):
    """A whole registry record: efdb profile + teammate's club context + nationality."""
    rec = bytearray(teammate_rec)
    rec[:32] = block_from_efdb(p, teammate_rec, gap)
    nat = (p.get("nationality_a") or {}).get("country_id")
    if isinstance(nat, int):
        struct.pack_into("<H", rec, 0x90, nat)
    return bytes(rec)


def pick_spare(career, registry, db, edit_pids, exclude=()):
    """A database player to lend his ID to a player FL26 lacks (E19: the game ignores
    option-file records whose ID is not in its base database). Chosen to be invisible:
    no database club, no career squad, no option-file edit, no career history (his pair
    appears only once, in the registry), and the weakest such player."""
    in_squad = {p for cl in career.clubs() for _, p in cl.members}
    idx = career.index()
    best = None
    for i in range(1, registry.count):
        pid = registry.pid(i)
        if (pid >= 0x100000 or pid in in_squad or pid in edit_pids or pid in exclude
                or pid in db.player_teams or pid not in db.player_names):
            continue
        if sum(idx.get(pid, {}).values()) > 1:
            continue
        rec = registry.record(i)
        score = sum(A.get(rec, k) for k in A.ABILITIES)
        if best is None or score < best[0]:
            best = (score, pid, i)
    if best is None:
        raise ValueError(tr("err.noSpare"))
    return best[1], best[2]


def mate_index(career, registry, block):
    """Registry index of a player in `block` whose record carries that club's context."""
    return next((h & 0xFFFF for h, q in career.club(block).members
                 if (h & 0xFFFF) < registry.count and registry.pid(h & 0xFFFF) == q
                 and q < 0x100000), None)


def adopt_spare(career, registry, spare_index, block, efdb_player, gap, mate=None):
    """Turn the spare's own registry record into the new player (profile from efdb, club
    context from a teammate at `block`, or `mate` when the squad is empty right now).
    Returns his handle. Caller commits."""
    m = mate_index(career, registry, block)
    mates = [m if m is not None else mate]
    if mates[0] is None:
        raise ValueError(tr("err.noMate"))
    i = spare_index
    old = registry.record(i)
    rec = bytearray(record_from_efdb(efdb_player, registry.record(mates[0]), gap))
    rec[0x20:0x28] = old[0x20:0x28]                  # keep the spare's handle and ID
    registry.blob[i * REC:(i + 1) * REC] = rec
    return registry.handle(i)


def build_new_player(career, registry, pid, block, efdb_player, gap, tag=None, mate=None):
    """Append a registry record for `pid` built from efootballdb, using a teammate at
    `block` (or `mate`) as template. Returns the new handle. Caller commits the registry."""
    m = mate_index(career, registry, block)
    mates = [x for x in (m if m is not None else mate,) if x is not None]
    if not mates:
        raise ValueError(tr("err.noMate"))
    template = registry.record(mates[0])
    tag = tag if tag is not None else (registry.handle(registry.count - 1) >> 16)
    h = registry.append(mates[0], pid, tag)
    i = h & 0xFFFF
    rec = bytearray(record_from_efdb(efdb_player, template, gap))
    struct.pack_into("<I", rec, 0x20, h)
    struct.pack_into("<I", rec, 0x24, pid)
    registry.blob[i * REC:(i + 1) * REC] = rec
    return h


def db_nationality(db_record):
    """Nationality of a database (Sider dump) player record: 9 bits at bit 233."""
    return int.from_bytes(db_record[29:32], "little") >> 1 & 0x1FF


def face_donor(players, faces, db, nationality, seed, exclude=(), fallback=169270):
    """A face for a player FL26 lacks: an obscure (clubless) database player of the same
    nationality, chosen by `seed` so new players don't all share one face."""
    pool = sorted(pid for pid, r in players.items()
                  if pid in faces and pid not in db.player_teams and pid not in exclude
                  and pid < 0x100000 and db_nationality(r) == nationality)
    return pool[seed % len(pool)] if pool else fallback
