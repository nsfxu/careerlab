"""The career's displayed managers: one 0x258-byte record per club block.

    +0x00 u32 club block index   +0x04 u32 coach ID   +0x08 name (UTF-8, NUL padded)
    the rest: not decoded (tactics/preferences, kept as-is when writing)

`block+0x144` in the club squad table mirrors the coach ID and is written alongside, but
the screen reads the name here (E11, 2026-10-11).
"""
from __future__ import annotations

import struct

STRIDE = 0x258
NAME_OFF, NAME_LEN = 0x08, 0x36


def locate(career):
    """Base of the table: the offset where records 0, 1, 2 carry their own index."""
    d, n = career.d, len(career.clubs())
    probe = struct.pack("<I", 1)
    i = 0
    while (j := d.find(probe, i)) >= 0:
        i = j + 1
        base = j - STRIDE
        if base < 0 or base % 2:
            continue
        if all(struct.unpack_from("<I", d, base + k * STRIDE)[0] == k for k in (0, 2, 3, n - 1)):
            if _text(d, base + NAME_OFF):
                return base
    raise LookupError("manager table not found")


def _text(d, o):
    raw = bytes(d[o:o + NAME_LEN]).split(bytes(1))[0]
    try:
        return raw.decode("utf8") if raw else ""
    except UnicodeDecodeError:
        return ""


class Managers:
    def __init__(self, career):
        self.c = career
        self.base = locate(career)

    def _o(self, k):
        o = self.base + k * STRIDE
        if struct.unpack_from("<I", self.c.d, o)[0] != k:
            raise LookupError(f"manager record {k} does not carry its index")
        return o

    def get(self, k):
        o = self._o(k)
        return struct.unpack_from("<I", self.c.d, o + 4)[0], _text(self.c.d, o + NAME_OFF)

    def set(self, k, coach_id, name):
        raw = name.encode("utf8")
        if len(raw) >= NAME_LEN:
            raise ValueError("name too long")
        o = self._o(k)
        struct.pack_into("<I", self.c.d, o + 4, coach_id)
        self.c.d[o + NAME_OFF:o + NAME_OFF + NAME_LEN] = raw + bytes(NAME_LEN - len(raw))
        struct.pack_into("<I", self.c.d, self.c.club(k).offset + 0x144, coach_id)

    # Squad-slot references in the record: the stored lineup (+0x220, 40 slots, 0xFF
    # padded) and the role bytes (+0x248..+0x251). Captain is +0x24E -- the one role the
    # game honours in Become a Legend (E21/E22); set-piece takers are re-picked by the AI.
    LINEUP, ROLES, CAPTAIN = 0x220, range(0x248, 0x252), 0x24E

    def captain(self, k):
        v = self.c.d[self._o(k) + self.CAPTAIN]
        return None if v == 0xFF else v

    def set_captain(self, k, slot):
        self.c.d[self._o(k) + self.CAPTAIN] = slot

    def slot_removed(self, k, slot):
        """Keep slot references valid after squad slot `slot` was compacted away."""
        o, d = self._o(k), self.c.d
        lineup = [x for x in d[o + self.LINEUP:o + self.LINEUP + 40] if x != 0xFF]
        lineup = [x - 1 if x > slot else x for x in lineup if x != slot]
        d[o + self.LINEUP:o + self.LINEUP + 40] = bytes(lineup + [0xFF] * (40 - len(lineup)))
        for r in self.ROLES:
            v = d[o + r]
            if v != 0xFF and v < 40:
                d[o + r] = 0xFF if v == slot else (v - 1 if v > slot else v)

    def slot_added(self, k, slot):
        """List a newly appended squad slot at the end of the stored lineup."""
        o, d = self._o(k), self.c.d
        lineup = [x for x in d[o + self.LINEUP:o + self.LINEUP + 40] if x != 0xFF]
        if slot not in lineup and len(lineup) < 40:
            lineup.append(slot)
        d[o + self.LINEUP:o + self.LINEUP + 40] = bytes(lineup + [0xFF] * (40 - len(lineup)))

    # the three formation/tactics presets (option-file game plan layout, 0xA0 each)
    TACTICS = (0x40, 0x220)

    def copy_tactics(self, dst, src):
        """Give club `dst` the formations and tactics of `src`'s manager, keeping dst's own
        manager, lineup and roles (E16 showed the presets are what the game plays)."""
        a, b = self.TACTICS
        od, os_ = self._o(dst), self._o(src)
        self.c.d[od + a:od + b] = bytes(self.c.d[os_ + a:os_ + b])

    def swap(self, a, b):
        oa, ob = self._o(a), self._o(b)
        ra, rb = bytes(self.c.d[oa + 4:oa + STRIDE]), bytes(self.c.d[ob + 4:ob + STRIDE])
        self.c.d[oa + 4:oa + STRIDE], self.c.d[ob + 4:ob + STRIDE] = rb, ra
        ca, cb = self.c.club(a), self.c.club(b)
        struct.pack_into("<I", self.c.d, ca.offset + 0x144, cb.field_144)
        struct.pack_into("<I", self.c.d, cb.offset + 0x144, ca.field_144)
