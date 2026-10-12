"""Read files out of the game's CRI CPK archives (read-only).

A CPK starts with "CPK " + an @UTF table (the header: TocOffset, ContentOffset…); the TOC is
another @UTF table with one row per file (DirName, FileName, FileSize, ExtractSize,
FileOffset). @UTF tables may be XOR-obfuscated. A file's bytes start at FileOffset plus the
smaller of TocOffset/ContentOffset. Konami wraps many files in "WESYS" (zlib) on top.
"""
from __future__ import annotations

import struct
import zlib

_FMT = {0: ">B", 1: ">b", 2: ">H", 3: ">h", 4: ">I", 5: ">i", 6: ">Q", 7: ">q", 8: ">f"}


def _plain(data):
    if data[:4] == b"@UTF":
        return data
    out, m = bytearray(len(data)), 0x655F
    for i, b in enumerate(data):
        out[i] = b ^ (m & 0xFF)
        m = (m * 0x4115) & 0xFFFFFFFF
    return bytes(out)


def _value(data, pos, typ, string_at):
    if typ in _FMT:
        return struct.unpack_from(_FMT[typ], data, pos)[0], pos + struct.calcsize(_FMT[typ])
    if typ == 0xA:
        return string_at(struct.unpack_from(">I", data, pos)[0]), pos + 4
    if typ == 0xB:
        return struct.unpack_from(">II", data, pos), pos + 8
    raise ValueError(f"unknown @UTF column type {typ}")


def read_utf(data):
    """An @UTF table as a list of {column: value} rows."""
    data = _plain(data)
    if data[:4] != b"@UTF":
        raise ValueError("not an @UTF table")
    _, rows_off, strings_off, data_off, _, ncols, row_len, nrows = struct.unpack_from(">IIIIIHHI", data, 4)
    base = 8
    strings = data[base + strings_off:base + data_off]

    def string_at(o):
        return strings[o:strings.index(b"\0", o)].decode("utf-8", "replace")

    cols, pos = [], base + 24
    for _ in range(ncols):
        flags = data[pos]
        name = string_at(struct.unpack_from(">I", data, pos + 1)[0])
        pos += 5
        storage, typ, const = flags & 0xF0, flags & 0x0F, None
        if storage == 0x30:                       # constant stored in the column header
            const, pos = _value(data, pos, typ, string_at)
        cols.append((name, storage, typ, const))
    rows = []
    for r in range(nrows):
        pos, row = base + rows_off + r * row_len, {}
        for name, storage, typ, const in cols:
            if storage == 0x50:
                row[name], pos = _value(data, pos, typ, string_at)
            else:
                row[name] = const
        rows.append(row)
    return rows


def _table_at(f, offset):
    f.seek(offset)
    head = f.read(16)
    size = struct.unpack_from("<I", head, 8)[0]
    return read_utf(f.read(size))


def files(path):
    """[(dir, name, offset, size, extract_size)] for one archive."""
    with open(path, "rb") as f:
        if f.read(4) != b"CPK ":
            raise ValueError(f"{path} is not a CPK archive")
        hdr = _table_at(f, 0)[0]
        toc_off = hdr.get("TocOffset")
        if not toc_off:
            return []
        base = min(x for x in (toc_off, hdr.get("ContentOffset")) if x)
        return [(r.get("DirName") or "", r.get("FileName") or "", base + r["FileOffset"], r["FileSize"],
                 r.get("ExtractSize") or r["FileSize"]) for r in _table_at(f, toc_off)]


def read(path, offset, size):
    """One file's bytes, unwrapped from Konami's WESYS container if needed."""
    with open(path, "rb") as f:
        f.seek(offset)
        data = f.read(size)
    if data[3:8] == b"WESYS":
        data = zlib.decompress(data[16:])
    return data
