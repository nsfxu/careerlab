"""The career's player registry: one 156-byte record per handle index, zlib-compressed.

This is the table that turns a handle into a player. It is why the playerID written next
to a handle is ignored (the record decides), why an index past the last record crashes
the game (the record there is empty), and why a player added to the database after the
career began has no handle (he has no record). Found 2026-10-11 from probe run P1:
index * 156 + 36 lands on the playerID of every probe the game displayed.

Layout of the section, located by its directory just before it:

    directory (LE u32 x8): ?, 1, 3, RECORD COUNT, club count, CONTAINER SIZE, TAIL SIZE, 0
    container:  "20110912" marker (BE u32), u32 0,
                BE u32 total uncompressed, BE u32 sum of compressed chunk lengths,
                chunks of { BE u32 usize, BE u32 csize, BE u32 next-data offset | 0 } + zlib
                (next-data offset is relative to the compressed-total field)
    tail:       the rest of the save

Record (156 bytes): +0x20 u32 handle, +0x24 u32 playerID (tag << 16 | own index).
Index 0 is the created character.
"""
from __future__ import annotations

import struct
import zlib

REC = 156
CHUNK = 0x40000
MARKER = 0x20110912
OFF_PID = 0x24
OFF_HANDLE = 0x20


class RegistryError(RuntimeError):
    pass


class Registry:
    def __init__(self, career):
        self.c = career
        d = career.d
        m = struct.pack(">I", MARKER)
        self.start = d.find(m)
        if self.start < 0 or d.find(m, self.start + 1) >= 0:
            raise RegistryError("registry marker not found exactly once")
        self.dir = self.start - 0x24
        f = struct.unpack_from("<8I", d, self.dir)
        if f[5] + self.start + f[6] != len(d):          # f[1:3] is (1,3) in BAL, (0,0) in ML
            raise RegistryError(f"directory does not describe the file: {f}")
        self.count = f[3]
        self.size = f[5]
        p = self.start + 8
        self.usize, self.ctotal = struct.unpack_from(">II", d, p)
        self.base = p + 4                  # next-data offsets are relative to this field
        p += 8
        parts = []
        while True:
            u, cl, nxt = struct.unpack_from(">III", d, p)
            parts.append(zlib.decompress(bytes(d[p + 12:p + 12 + cl])))
            if len(parts[-1]) != u:
                raise RegistryError("chunk size mismatch")
            p += 12 + cl
            if nxt == 0:
                break
            if self.base + nxt != p + 12:
                raise RegistryError("chunk chain does not line up")
        if p != self.start + self.size:
            raise RegistryError("container size field disagrees with the chunks")
        self.blob = bytearray(b"".join(parts))
        if len(self.blob) != self.usize:
            raise RegistryError("total size mismatch")

    # ------------------------------------------------------------------ records

    @property
    def capacity(self):
        return len(self.blob) // REC

    def record(self, i):
        return bytes(self.blob[i * REC:(i + 1) * REC])

    def pid(self, i):
        return struct.unpack_from("<I", self.blob, i * REC + OFF_PID)[0]

    def handle(self, i):
        return struct.unpack_from("<I", self.blob, i * REC + OFF_HANDLE)[0]

    def index_of(self, pid):
        for i in range(self.count):
            if self.pid(i) == pid:
                return i
        return None

    def append(self, template_index, pid, tag):
        """Copy record `template_index` to the next free index as player `pid`."""
        i = self.count
        if i >= self.capacity:
            raise RegistryError("registry is full")
        if self.index_of(pid) is not None:
            raise RegistryError(f"{pid} already has a record")
        rec = bytearray(self.record(template_index))
        struct.pack_into("<I", rec, OFF_PID, pid)
        struct.pack_into("<I", rec, OFF_HANDLE, (tag << 16) | i)
        self.blob[i * REC:(i + 1) * REC] = rec
        self.count += 1
        return (tag << 16) | i

    # -------------------------------------------------------------------- write

    def commit(self):
        """Recompress into the career's data, fixing the directory sizes."""
        chunks = [bytes(self.blob[o:o + CHUNK]) for o in range(0, len(self.blob), CHUNK)]
        comp = [zlib.compress(ch, 9) for ch in chunks]
        body = bytearray()
        pos = self.base + 4                          # first chunk header, absolute
        for k, (ch, z) in enumerate(zip(chunks, comp)):
            data_at = pos + 12
            nxt = 0 if k == len(chunks) - 1 else (data_at + len(z) + 12) - self.base
            body += struct.pack(">III", len(ch), len(z), nxt) + z
            pos = data_at + len(z)
        head = struct.pack(">II", MARKER, 0) + struct.pack(">II", len(self.blob),
                                                           self._ctotal(comp))
        container = head + body
        d = self.c.d
        tail = bytes(d[self.start + self.size:])
        d[self.start:] = container + tail
        struct.pack_into("<I", d, self.dir + 12, self.count)
        struct.pack_into("<I", d, self.dir + 20, len(container))
        self.size = len(container)
        self.c.dirty()

    @staticmethod
    def _ctotal(comp):
        # In the original file: 1,256,348 = container 1,256,580 - 16 header - 12 x 18 chunk
        # headers, i.e. the sum of the compressed chunk lengths.
        return sum(len(z) for z in comp)
