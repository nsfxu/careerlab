"""Konami PES 2021 save encryption, in pure Python.

A port of the4chancup's pesXdecrypter (public domain). A save is

    320-byte encryption header | FileHeader (208 B) | description | logo | data | serial

each section XORed with a keystream derived from MT19937. CPython's `random` module *is*
MT19937, so the generator runs at C speed: we compute init_by_array ourselves, load the
state with setstate(), and pull the whole stream with one getrandbits() call.

The property everything rests on: decrypt -> encrypt of an untouched save is
byte-identical. `Save.verify_roundtrip()` asserts it.

Each game has its own 64-byte master key: FL26 kept PES 2021's, FL27 has a new one
(SmokePatch publishes it as FL_key.bin; it is not shipped here, config.py finds the user's
copy and registers it with `add_key`). The decrypted FileHeader starts with the master key,
byte-shuffled, so a save tells which known key opens it.
"""
import random
import struct

import numpy as np

MASTER_KEY_PES21 = bytes([
    0x90, 0x61, 0xD8, 0x66, 0x43, 0x77, 0x24, 0xF8, 0x92, 0xBA, 0xB8, 0x71, 0x21, 0xC7, 0x60, 0x63,
    0xF0, 0x91, 0x9A, 0x7D, 0xED, 0x47, 0x80, 0xDE, 0x51, 0xF5, 0xDD, 0xD1, 0x08, 0xFE, 0x32, 0x84,
    0xF5, 0x09, 0x92, 0x00, 0xB2, 0x3E, 0x88, 0x9F, 0xEB, 0x24, 0x43, 0x05, 0x58, 0x76, 0x00, 0x22,
    0x9B, 0xFE, 0xEC, 0xF6, 0x50, 0x00, 0x29, 0xD3, 0x42, 0x75, 0x50, 0xB9, 0xEC, 0xD2, 0xF6, 0x75,
])

KNOWN_KEYS = [MASTER_KEY_PES21]

ENC_HEADER_SIZE = 320
FILE_HEADER_SIZE = 208  # PES18+ layout, includes gameVersionString[32]
_M32 = 0xFFFFFFFF


def _mt_state(key_words):
    """MT19937 init_by_array, returning a state tuple for random.setstate()."""
    mt = [0] * 624
    mt[0] = 19650218
    for i in range(1, 624):
        mt[i] = (1812433253 * (mt[i - 1] ^ (mt[i - 1] >> 30)) + i) & _M32
    i, j, n = 1, 0, len(key_words)
    for _ in range(max(624, n)):
        mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1664525)) + key_words[j] + j) & _M32
        i, j = i + 1, j + 1
        if i >= 624:
            mt[0], i = mt[623], 1
        if j >= n:
            j = 0
    for _ in range(623):
        mt[i] = ((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1566083941)) - i) & _M32
        i += 1
        if i >= 624:
            mt[0], i = mt[623], 1
    mt[0] = 0x80000000
    return (3, tuple(mt) + (624,), None)


def _rol(a, s):
    return ((a << s) | (a >> (32 - s))) & 0xFFFFFFFF


def _ror(a, s):
    return ((a >> s) | (a << (32 - s))) & 0xFFFFFFFF


def _crypt_stream(key64, data):
    """XOR `data` with the keystream for a 64-byte key. Symmetric."""
    n = len(data) // 4
    rest = len(data) & 3
    rng = random.Random()
    rng.setstate(_mt_state(struct.unpack("<16I", key64)))
    count = n + 5
    r = np.frombuffer(rng.getrandbits(32 * count).to_bytes(4 * count, "little"), dtype="<u4")

    # The reference loop keeps four rotated copies of earlier outputs. Unrolled, word i
    # (for i >= 4) is  r[i+4] ^ ror(r[i+3],13) ^ ror(r[i+2],6) ^ rol(r[i+1],5) ^ ror(r[i],10).
    # The first four words still see the unrotated seeds, so they run the loop literally.
    ks = np.empty(n + 1, dtype="<u4")
    c0, c1, c2, c3 = (int(x) for x in r[:4])
    head = min(n + 1, 4)
    for i in range(head):
        c4 = int(r[i + 4])
        ks[i] = c4 ^ c3 ^ c2 ^ c1 ^ c0
        c0, c1, c2, c3 = _ror(c1, 15), _rol(c2, 11), _rol(c3, 7), _ror(c4, 13)
    if n + 1 > 4:
        def rot(x, s, left):
            return (x << s | x >> (32 - s)) if left else (x >> s | x << (32 - s))
        i = np.arange(4, n + 1)
        ks[4:] = (r[i + 4] ^ rot(r[i + 3], 13, False) ^ rot(r[i + 2], 6, False)
                  ^ rot(r[i + 1], 5, True) ^ rot(r[i], 10, False))

    words = np.frombuffer(data, dtype="<u4", count=n) ^ ks[:n]
    out = words.tobytes()
    if rest:
        tail = int.from_bytes(data[4 * n:], "little") ^ (int(ks[n]) & ((1 << (8 * rest)) - 1))
        out += tail.to_bytes(rest, "little")
    return out


def _xor_param(key64, param):
    q = struct.unpack("<8Q", key64)
    return struct.pack("<8Q", *(x ^ param for x in q))


class UnknownKey(ValueError):
    """No known master key opens the file (an FL27 save before FL_key.bin is found)."""


def add_key(master):
    master = bytes(master)
    if len(master) != 64:
        raise ValueError("a master key is 64 bytes")
    if master not in KNOWN_KEYS:
        KNOWN_KEYS.append(master)


def _shuffled(master):
    return b"".join(master[i:i + 8][::-1] for i in range(0, 64, 8))


def _header_key(enc_header_tail, master):
    return bytes(a ^ b for a, b in zip(enc_header_tail, _shuffled(master)))


def _open_headers(raw, masters):
    """(master, enc_header, rolling key, file header) for the first key that opens `raw`."""
    for master in masters:
        hk = _header_key(raw[256:320], master)
        enc_header = _crypt_stream(hk, raw[:ENC_HEADER_SIZE])[:256] + raw[256:320]
        rk = _rolling_key(enc_header)
        fh = _crypt_stream(_xor_param(rk, FILE_HEADER_SIZE),
                           raw[ENC_HEADER_SIZE:ENC_HEADER_SIZE + FILE_HEADER_SIZE])
        if fh[:64] == _shuffled(master):
            return master, enc_header, rk, fh
    raise UnknownKey("no known key opens this save")


def _text(b):
    return bytes(b).split(b"\0")[0].decode("utf-8", "replace")


def _rolling_key(enc_header):
    k = bytearray(enc_header[:64])
    for idx, b in enumerate(enc_header[64:320]):
        k[idx & 63] ^= b
    return bytes(k)


class Save:
    """A decrypted save. `data` is the payload everything else in the engine reads."""

    def __init__(self, enc_header, file_header, description, logo, data, serial, master=MASTER_KEY_PES21):
        self.master = master
        self.enc_header = enc_header
        self.file_header = file_header
        self.description = description
        self.logo = logo
        self.data = data
        self.serial = serial

    @classmethod
    def decrypt(cls, raw, master=None):
        """`master` None: whichever known key opens it (the Save remembers it for encrypt)."""
        raw = bytes(raw)
        master, enc_header, rk, fh = _open_headers(raw, [master] if master else KNOWN_KEYS)
        p = ENC_HEADER_SIZE + FILE_HEADER_SIZE
        data_size, logo_size, desc_size, serial_len = struct.unpack_from("<4I", fh, 64)
        sections = []
        for param, size in ((0, desc_size), (1, logo_size), (2, data_size), (3, serial_len * 2)):
            sections.append(_crypt_stream(_xor_param(rk, param), raw[p:p + size]))
            p += size
        if p != len(raw):
            raise ValueError(f"size mismatch: header accounts for {p} bytes, file has {len(raw)}")
        return cls(enc_header, fh, *sections, master=master)

    @staticmethod
    def peek(path):
        """{kind, game, title, lines, stamp} from the headers, the description and the
        payload's first bytes, without decrypting the 19 MB payload: for listing saves."""
        with open(path, "rb") as f:
            raw = f.read(ENC_HEADER_SIZE + FILE_HEADER_SIZE)
            master, _, rk, fh = _open_headers(raw, KNOWN_KEYS)
            data_size, logo_size, desc_size = struct.unpack_from("<3I", fh, 64)
            desc = _crypt_stream(_xor_param(rk, 0), f.read(desc_size))
            f.seek(logo_size, 1)
            # the keystream starts with the section, so its head decrypts on its own
            head = _crypt_stream(_xor_param(rk, 2), f.read(min(24, data_size)))
        # BL description: slot title at 0 ("Rumo ao Estrelato 02"), then
        # "player\nclub / league\ndate" at 128
        return {"kind": _text(fh[144:176]), "game": _text(fh[176:208]),
                "title": _text(desc[:128]), "lines": _text(desc[128:]).split("\n") if len(desc) > 128 else [],
                "stamp": struct.unpack_from("<3I", head, 12) if len(head) == 24 else None,
                "master": master}

    @property
    def kind(self):
        """File type from the header: BL, EDIT, SYSTEM..."""
        return _text(self.file_header[144:176])

    @property
    def game(self):
        """The game that wrote it: "SP Football Life 2026" / "SP Football Life 2027"."""
        return _text(self.file_header[176:208])

    def encrypt(self, master=None):
        master = master or self.master
        fh = bytearray(self.file_header)
        struct.pack_into("<4I", fh, 64, len(self.data), len(self.logo), len(self.description),
                         len(self.serial) // 2)
        hk = _header_key(self.enc_header[256:320], master)
        out = [_crypt_stream(hk, self.enc_header)[:256] + self.enc_header[256:320]]
        rk = _rolling_key(self.enc_header)
        out.append(_crypt_stream(_xor_param(rk, FILE_HEADER_SIZE), bytes(fh)))
        for param, sec in ((0, self.description), (1, self.logo), (2, self.data), (3, self.serial)):
            out.append(_crypt_stream(_xor_param(rk, param), bytes(sec)))
        return b"".join(out)

    @classmethod
    def load(cls, path, master=None):
        with open(path, "rb") as f:
            return cls.decrypt(f.read(), master)

    def verify_roundtrip(self, raw):
        """True if re-encrypting reproduces `raw` exactly."""
        return self.encrypt() == bytes(raw)


def stamp_version(stamp):
    """Payload version stamp -> game version: 270100 -> "27.1.0" (FL27's version.ini says
    27.1.0), 260203 -> "26.2.3"."""
    if not stamp:
        return None
    v = stamp[0]
    return f"{v // 10000}.{v // 100 % 100}.{v % 100}"
