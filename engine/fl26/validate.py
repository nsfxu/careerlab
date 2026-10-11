"""Invariants a healthy career save satisfies, checked without the game.

Calibrated against untouched saves: every ERROR check reads zero on them. A write is
accepted only if it introduces no new ERROR (`new_problems`), so old damage cannot hide
a fresh mistake.
"""
from __future__ import annotations

import collections
import dataclasses

from .career import CREATED_ID_MIN, PLAUSIBLE_PID_MAX, Career


@dataclasses.dataclass(frozen=True)
class Problem:
    level: str      # "ERROR" | "NOTE"
    code: str
    where: str
    detail: str

    def __str__(self):
        return f"{self.level:5} {self.code:20} {self.where:14} {self.detail}"


def check(c: Career):
    out = []
    clubs = c.clubs()
    members = {(h, p) for club in clubs for h, p in club.members}
    bind = c.bindings(h for h, _ in members)
    owner = collections.defaultdict(list)
    for club in clubs:
        w = f"block {club.index}"
        if not club.consistent:
            out.append(Problem("ERROR", "length-mismatch", w,
                               f"count {len(club.members)}, terminator {club.terminator}, "
                               f"shirts {club.shirt_len}"))
        for pid, n in collections.Counter(club.pids).items():
            if n > 1:
                out.append(Problem("ERROR", "duplicate-in-squad", w, f"player {pid} x{n}"))
        shirts = [s for s in club.shirts if s]
        if len(shirts) != len(set(shirts)):
            out.append(Problem("NOTE", "shirt-clash", w, "two players share a number"))
        if club.pids:
            owner_ok = [p for p in club.pids if p < CREATED_ID_MIN]
            for p in owner_ok:
                owner[p].append(club.index)
    # Every squad handle must bind to exactly one player across the whole file. A handle
    # followed by different players is the identity clash that renders as a blank slot.
    # Only real playerIDs count: handles are also stored in bare-handle lists, so the
    # word after a handle is often another handle, which is not a clash.
    for h, pid in sorted(members):
        if pid >= CREATED_ID_MIN:
            continue
        others = {p for p in bind[h] if p != pid and 1 <= p <= PLAUSIBLE_PID_MAX and p != 0xFFFF}
        if others:
            out.append(Problem("ERROR", "handle-clash", f"{h:08X}",
                               f"squad says {pid}, file also binds {sorted(others)[:4]}"))
    for pid, blocks in owner.items():
        if len(blocks) > 1:
            out.append(Problem("NOTE", "multi-squad", f"player {pid}", f"blocks {blocks}"))
    return out


def summary(problems):
    return collections.Counter((p.level, p.code) for p in problems)


def new_problems(before, after):
    key = lambda p: (p.code, p.where, p.detail)
    old = {key(p) for p in before}
    return [p for p in after if p.level == "ERROR" and key(p) not in old]
