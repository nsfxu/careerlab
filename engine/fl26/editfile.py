"""EDIT00000000 (option file) player table: add a player the game's database lacks.

Layout (header u16 @0x60 = player count, table @0x7C, 312-byte records):
    +0x00 playerID  +0x04 playerID  +0x08 u16 nationality  +0x0A height  +0x0B weight
    +0x1F bit 7 name-edited flag (without it the names are ignored)
    +0x36 name (61 B)  +0x73 print name (61 B)  +0xB0 national print name
    +0xF0 appearance (72 B): playerID, 8 zero bytes, appearance data, 4 zero bytes

Derived 2026-10-11: an option-file record equals the database (Player.bin) record without
its 14-byte header (185/224 bytes identical for an unedited player), and the appearance
block equals PlayerAppearance.bin's 60-byte record with 8 bytes inserted after the ID.
"""
from __future__ import annotations

import struct
from pathlib import Path

from .crypto import Save

COUNT = 0x60
TABLE = 0x7C
STRIDE = 0x138
MAX = 30000
NAME, PRINT, NATIONAL = 0x36, 0x73, 0xB0
NAME_LEN = 61


class EditFile:
    def __init__(self, path):
        self.path = Path(path)
        self.save = Save.load(self.path)
        self.d = bytearray(self.save.data)

    def to_bytes(self):
        self.save.data = bytes(self.d)
        return self.save.encrypt()

    @property
    def count(self):
        return struct.unpack_from("<H", self.d, COUNT)[0]

    def find(self, pid):
        for k in range(self.count):
            if struct.unpack_from("<I", self.d, TABLE + k * STRIDE)[0] == pid:
                return k
        return None

    def add_player(self, pid, name, print_name, db_record, db_appearance,
                   height=None, weight=None, nationality=None):
        """Append a record for `pid`, cloned from a database player (`db_record`: 312-byte
        Player.bin record, `db_appearance`: 60-byte PlayerAppearance.bin record)."""
        if self.find(pid) is not None:
            raise ValueError(f"{pid} already has an option-file record")
        k = self.count
        if k >= MAX:
            raise ValueError("option-file player table is full")
        rec = bytearray(STRIDE)
        rec[0:0xF0] = db_record[14:14 + 0xF0]
        rec[0xF0:0xF0 + 72] = db_appearance[0:4] + bytes(8) + db_appearance[4:60] + bytes(4)
        for off in (0x00, 0x04, 0xF0):
            struct.pack_into("<I", rec, off, pid)
        if nationality is not None:
            struct.pack_into("<H", rec, 0x08, nationality)
        if height:
            rec[0x0A] = max(140, min(210, int(height)))
        if weight:
            rec[0x0B] = max(40, min(120, int(weight)))
        for off, text in ((NAME, name), (PRINT, print_name), (NATIONAL, print_name)):
            raw = text.encode("utf8")[:NAME_LEN - 1]
            rec[off:off + NAME_LEN] = raw + bytes(NAME_LEN - len(raw))
        rec[0x1F] |= 0x80
        o = TABLE + k * STRIDE
        self.d[o:o + STRIDE] = rec
        struct.pack_into("<H", self.d, COUNT, k + 1)
        return k


SQUADS_AT = 0x9D4648          # club blocks: u32 teamID, u32[40] playerIDs, u16[40] shirts
SQUAD_STRIDE = 0x11C


def _squad_table(d):
    """Offset of the squad table (blocks for teams 1, 2, 3… at the start)."""
    ok = lambda o: all(o + k * SQUAD_STRIDE + 4 <= len(d)
                       and struct.unpack_from("<I", d, o + k * SQUAD_STRIDE)[0] == k + 1 for k in range(3))
    if ok(SQUADS_AT):
        return SQUADS_AT
    i = 0
    probe = struct.pack("<I", 1)
    while (j := bytes(d).find(probe, i)) >= 0:
        if ok(j):
            return j
        i = j + 1
    raise ValueError("squad table not found in the option file")


def squads(edit):
    """{teamID: [(playerID, shirt)]}: the squads FL26 starts careers from (option file)."""
    d = edit.d
    o = _squad_table(d)
    out = {}
    k = 0
    while o + (k + 1) * SQUAD_STRIDE <= len(d):
        b = o + k * SQUAD_STRIDE
        tid = struct.unpack_from("<I", d, b)[0]
        if tid == 0 or tid in out or tid > 100000:
            break
        pids = struct.unpack_from("<40I", d, b + 4)
        shirts = struct.unpack_from("<40H", d, b + 0xA4)
        out[tid] = [(p, s) for p, s in zip(pids, shirts) if p]
        k += 1
    return out


def load_db_tables(dump_dir=None):
    """({pid: Player.bin record}, {pid: appearance record}) from a Sider dump."""
    from . import config
    pl = config.table_file("player", dump_dir).read_bytes()
    ap = config.table_file("playerappearance", dump_dir).read_bytes()
    players = {struct.unpack_from("<I", pl, i * 312 + 8)[0]: pl[i * 312:(i + 1) * 312]
               for i in range(len(pl) // 312)}
    faces = {struct.unpack_from("<I", ap, i * 60)[0]: ap[i * 60:(i + 1) * 60]
             for i in range(len(ap) // 60)}
    return players, faces
