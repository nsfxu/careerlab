"""The game's reference database (names, teams, base assignments) as dumped by Sider.

Dumps come from `SiderAddons/modules/DBDump.lua` (`<name>.raw` files). Layouts:

    player.raw            stride 312    +0x08 playerID  +0x44 name (UTF-8)
                          +0x33 low 6 bits = age - 16 (the database's season; matched
                          efootballdb's age for 221 of 228 players, the rest off by one)
    team.raw              stride 0x5FC  +0x00 coachID   +0x08 teamID  +0x170 name
                          +0x47 bit 7 = national team; +0x37C Portuguese name (nationals)
    playerassignment.raw  stride 16     +0x04 playerID  +0x08 teamID  +0x0C order<<10|shirt
    competitionentry.raw  stride 12     +0x00 teamID    +0x04 entryID +0x08 u8 competitionID
                          (21 = Brasileirão, 9 = Premier League; the ID also names the
                          competition's emblem file, see images.py)

The option file overrides names (its edited-player table), so EDIT00000000 is read too.
"""
from __future__ import annotations

import collections
import struct
from pathlib import Path

from . import config, i18n
from .crypto import Save

DEFAULT_DUMP = None          # None = the configured game folder's dump (see config.py)


def _text(b):
    return bytes(b).split(bytes(1))[0].decode("utf8", "replace")


class Database:
    def __init__(self, dump_dir=DEFAULT_DUMP, edit_file=None):
        pl = config.table_file("player", dump_dir).read_bytes()
        self.player_names = {}
        self.player_nat = {}                  # pid -> nationality (9 bits at bit 233)
        self.player_age = {}                  # pid -> age in the database's season
        for i in range(len(pl) // 312):
            o = i * 312
            pid = struct.unpack_from("<I", pl, o + 8)[0]
            self.player_names[pid] = _text(pl[o + 0x44:o + 0x44 + 61])
            self.player_nat[pid] = int.from_bytes(pl[o + 29:o + 32], "little") >> 1 & 0x1FF
            self.player_age[pid] = (pl[o + 0x33] & 0x3F) + 16
        tm = config.table_file("team", dump_dir).read_bytes()
        self.team_names = {}
        self.national = set()                 # national-team IDs (no fixed ID range)
        self.team_names_pt = {}
        for i in range(len(tm) // 0x5FC):
            o = i * 0x5FC
            tid = struct.unpack_from("<I", tm, o + 8)[0]
            self.team_names[tid] = _text(tm[o + 0x170:o + 0x1B0])
            if tm[o + 0x47] & 0x80:
                self.national.add(tid)
                self.team_names_pt[tid] = _text(tm[o + 0x37C:o + 0x37C + 0x46])
        self._by_nat = None
        pa = config.table_file("playerassignment", dump_dir).read_bytes()
        self.player_teams = collections.defaultdict(list)       # pid -> [teamID]
        for i in range(len(pa) // 16):
            _, pid, tid, _ = struct.unpack_from("<4I", pa, i * 16)
            self.player_teams[pid].append(tid)
        self.coach_names = {}
        if edit_file and Path(edit_file).exists():
            self._read_edit(Path(edit_file))

    def _read_edit(self, path):
        e = Save.load(path).data
        n = struct.unpack_from("<H", e, 0x60)[0]
        for k in range(n):
            o = 0x7C + k * 0x138
            pid = struct.unpack_from("<I", e, o)[0]
            if e[o + 0x1F] & 0x80:                               # name-edited flag
                self.player_names[pid] = _text(e[o + 0x36:o + 0x36 + 61])
        for k in range(struct.unpack_from("<H", e, 0x66)[0]):
            o = 0x958DA4 + k * 0x58
            if e[o + 8] == 0x60:
                self.coach_names[struct.unpack_from("<I", e, o)[0]] = _text(e[o + 9:o + 41])

    def player_name(self, pid):
        return self.player_names.get(pid)

    def team_name(self, tid):
        if i18n.LANG == "pt" and self.team_names_pt.get(tid):
            return self.team_names_pt[tid]
        return self.team_names.get(tid)

    def is_national(self, tid):
        return tid in self.national

    def national_of(self):
        """{nationality: national teamID}: the nationality most of its database players share."""
        if self._by_nat is None:
            votes = collections.defaultdict(collections.Counter)
            for pid, teams in self.player_teams.items():
                nat = self.player_nat.get(pid)
                for t in teams:
                    if t in self.national and nat is not None:
                        votes[t][nat] += 1
            self._by_nat = {}
            for t, c in sorted(votes.items()):
                nat, n = c.most_common(1)[0]
                if n * 2 > sum(c.values()):
                    self._by_nat.setdefault(nat, t)
        return self._by_nat


def identify_nationals(career, registry, db, ids, min_size=15):
    """{block: (national teamID, nationality)} for national-team squads.

    They hold the game's own call-ups (re-picked before every international window), so
    database voting rarely names them; but every member shares one nationality (registry
    +0x90), which names the team. Clubs already identified are left alone (a Brazilian
    club can be all-Brazilian too)."""
    by_nat = db.national_of()
    out = {}
    for cl in career.clubs():
        tid = ids.get(cl.index, (None,))[0]
        if tid and not db.is_national(tid):
            continue
        nats, n = collections.Counter(), 0
        for h, pid in cl.members:
            i = h & 0xFFFF
            if pid < 0x80000000 and i < registry.count and registry.pid(i) == pid:
                nats[struct.unpack_from("<H", registry.blob, i * 156 + 0x90)[0]] += 1
                n += 1
        if n < min_size:
            continue
        nat, k = nats.most_common(1)[0]
        if k >= n - 1 and nat in by_nat:
            out[cl.index] = (by_nat[nat], nat)
    return out


def competition_teams(dump_dir=DEFAULT_DUMP):
    """{FL26 competitionID: {teamID}} from the CompetitionEntry dump; {} if not dumped."""
    try:
        d = config.table_file("competitionentry", dump_dir).read_bytes()
    except (FileNotFoundError, OSError):
        return {}
    out = collections.defaultdict(set)
    for i in range(len(d) // 12):
        tid, _, comp = struct.unpack_from("<IIB", d, i * 12)
        out[comp].add(tid)
    return dict(out)


def match_competition(teams, comps, threshold=0.4):
    """The FL26 competition whose team list is most like `teams` (Jaccard), or None.
    Overlap alone would pick a cup holding the whole league plus the second division; on a
    tie (a cup with exactly the league's clubs) the lower ID wins, which is the league."""
    teams = set(teams)
    best, score = None, threshold
    for comp, tids in sorted(comps.items()):
        s = len(teams & tids) / len(teams | tids) if teams else 0
        if s > score:
            best, score = comp, s
    return best


NO_CLUB = 0x3FFFF


def identify_blocks(career, registry, db):
    """{block index: (teamID or None, confidence)} by voting.

    Each member votes for his career club (registry +0x80 >> 14, kept by the game) and for
    every team the database assigns him to. A club block is carried by both; a national
    team block by the database. Representative squads (World XI etc.) stay unidentified.
    """
    out = {}
    for cl in career.clubs():
        votes = collections.Counter()
        n = 0
        for h, pid in cl.members:
            i = h & 0xFFFF
            cands = set(db.player_teams.get(pid, ()))
            if i < registry.count and registry.pid(i) == pid:
                club = struct.unpack_from("<I", registry.blob, i * 156 + 0x80)[0] >> 14
                if club != NO_CLUB:
                    cands.add(club)
            if cands:
                n += 1
                votes.update(cands)
        if not votes:
            out[cl.index] = (None, 0.0)
            continue
        tid, k = votes.most_common(1)[0]
        conf = k / max(n, 1)
        out[cl.index] = (tid if conf >= 0.5 else None, round(conf, 2))
    return out
