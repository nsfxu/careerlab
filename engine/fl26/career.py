"""A Become a Legend career save (BL0000000x), read and edited in memory.

The model, every piece of it proven in game before this rewrite:

* A career refers to a player by an 8-byte pair (u32 handle, u32 playerID). The pair is
  repeated across squad, contract, stats and history structures. The handle is the
  identity; the playerID beside it is a cross-checked copy.
* Handles live in namespaces: the high 16 bits are a per-save tag. A save has a primary
  namespace, a small secondary one, and the created character's reserved 0x4140.
* The club squad table: 0x690-byte blocks from 0x19C. Each holds up to 40 pairs, its own
  index at +0x140, a u32 at +0x144 (NOT the displayed manager), 40 u16 shirt numbers at
  +0x14E and the squad length at +0x2DA. The length exists three times (pair terminator,
  shirt array, count) and all three must agree.
"""
from __future__ import annotations

import collections
import dataclasses
import struct
from pathlib import Path

import numpy as np

from .crypto import Save

CREATED_ID_MIN = 0x100000
CREATED_TAG = 0x4140
PLAUSIBLE_PID_MAX = 400_000

CLUB_TABLE = 0x19C
CLUB_STRIDE = 0x690
CLUB_SLOTS = 40
CLUB_SELF_INDEX = 0x140
CLUB_FIELD_144 = 0x144
CLUB_SHIRTS = 0x14E
CLUB_COUNT = 0x2DA
EMPTY_PAIR = (0x0000FFFF, 0)


class CareerError(RuntimeError):
    pass


@dataclasses.dataclass
class Club:
    index: int
    offset: int
    members: list          # [(handle, pid)] in slot order, length = count field
    shirts: list           # u16 per member
    field_144: int
    terminator: int        # slot of the first empty pair
    shirt_len: int         # slots before the first 0 shirt

    @property
    def pids(self):
        return [p for _, p in self.members]

    @property
    def consistent(self):
        return len(self.members) == self.terminator == self.shirt_len


class Career:
    def __init__(self, save: Save, path: Path | None = None):
        self.save = save
        self.path = path
        self.d = bytearray(save.data)
        self._cache = {}

    @classmethod
    def load(cls, path):
        path = Path(path)
        return cls(Save.load(path), path)

    def to_bytes(self):
        """The re-encrypted save, ready to write."""
        self.save.data = bytes(self.d)
        return self.save.encrypt()

    # ------------------------------------------------------------------ views

    def u32(self):
        n = len(self.d) // 4
        return np.frombuffer(bytes(self.d[:n * 4]), dtype="<u4")

    def dirty(self):
        self._cache.clear()

    def _cached(self, key, fn):
        if key not in self._cache:
            self._cache[key] = fn()
        return self._cache[key]

    # ------------------------------------------------------------- namespaces

    def namespaces(self):
        """{tag: handles} for every tag whose handles bind one-to-one to playerIDs.

        Frequency is not evidence (tag 0x0000 outnumbers the real one); binding is.
        A genuine handle is followed by the same playerID everywhere it occurs.
        """
        def compute():
            a = self.u32()
            h, p = a[:-1], a[1:]
            m = (p >= 1) & (p <= PLAUSIBLE_PID_MAX)
            h, p = h[m], p[m]
            tags = h >> 16
            out = {}
            cand, counts = np.unique(tags, return_counts=True)
            for t in cand[np.argsort(-counts)][:40]:
                t = int(t)
                if t in (0, 0xFFFF):
                    continue
                sel = tags == t
                pairs = np.unique((h[sel].astype(np.uint64) << 32) | p[sel])
                hs, per_handle = np.unique(pairs >> 32, return_counts=True)
                # A real namespace is ~100% one-to-one; stray words in 20 MB cost a few.
                if len(hs) >= 50 and (per_handle == 1).mean() >= 0.99:
                    out[t] = len(hs)
            return out
        return self._cached("ns", compute)

    def primary_tag(self):
        ns = self.namespaces()
        if not ns:
            raise CareerError("no handle namespace found; is this a career save?")
        return max(ns, key=ns.get)

    # --------------------------------------------------------------- registry

    def index(self):
        """{pid: {handle: occurrences}} over every namespace, created character included."""
        def compute():
            a = self.u32()
            tags = set(self.namespaces())
            h, p = a[:-1], a[1:]
            t = h >> 16
            ok = np.isin(t, list(tags)) & (p >= 1) & (p <= PLAUSIBLE_PID_MAX)
            ok |= (t == CREATED_TAG) & (p >= CREATED_ID_MIN)
            pairs, counts = np.unique((h[ok].astype(np.uint64) << 32) | p[ok], return_counts=True)
            idx = collections.defaultdict(dict)
            for pr, c in zip(pairs.tolist(), counts.tolist()):
                idx[pr & 0xFFFFFFFF][pr >> 32] = c
            return dict(idx)
        return self._cached("index", compute)

    def handle_of(self, pid):
        """The handle the career uses for this player, or None if it has never heard of him."""
        hs = self.index().get(pid)
        return max(hs, key=hs.get) if hs else None

    def created_ids(self):
        return sorted(p for p in self.index() if p >= CREATED_ID_MIN
                      and sum(self.index()[p].values()) >= 3)

    def bindings(self, handles):
        """{handle: Counter(word that follows it)} for every aligned occurrence.

        Exact for any handle, whatever its namespace -- including the tag-0x0000
        handles the game allocates for its own in-career signings.
        """
        a = self.u32()
        want = np.array(sorted(set(handles)), dtype="<u4")
        pos = np.nonzero(np.isin(a[:-1], want))[0]
        out = collections.defaultdict(collections.Counter)
        for h, p in zip(a[pos].tolist(), a[pos + 1].tolist()):
            out[h][p] += 1
        return out

    def pair_offsets(self, handle, pid):
        pat = struct.pack("<II", handle, pid)
        out, i = [], 0
        while (j := self.d.find(pat, i)) >= 0:
            if j % 4 == 0:
                out.append(j)
            i = j + 1
        return out

    # ------------------------------------------------------------------ clubs

    def club(self, k):
        o = CLUB_TABLE + k * CLUB_STRIDE
        d = self.d
        n = min(struct.unpack_from("<H", d, o + CLUB_COUNT)[0], CLUB_SLOTS)
        pairs = [struct.unpack_from("<II", d, o + i * 8) for i in range(CLUB_SLOTS)]
        shirts_all = list(struct.unpack_from("<40H", d, o + CLUB_SHIRTS))
        term = next((i for i, pr in enumerate(pairs) if pr == EMPTY_PAIR), CLUB_SLOTS)
        slen = next((i for i, s in enumerate(shirts_all) if s == 0), CLUB_SLOTS)
        return Club(k, o, pairs[:n], shirts_all[:n],
                    struct.unpack_from("<I", d, o + CLUB_FIELD_144)[0], term, slen)

    def clubs(self):
        def compute():
            out = []
            for k in range(2000):
                o = CLUB_TABLE + k * CLUB_STRIDE
                if o + CLUB_STRIDE > len(self.d):
                    break
                if struct.unpack_from("<I", self.d, o + CLUB_SELF_INDEX)[0] != k:
                    break
                out.append(self.club(k))
            return out
        return self._cached("clubs", compute)

    def club_of(self, pid):
        return [c.index for c in self.clubs() if pid in c.pids]

    # ----------------------------------------------------------------- writes

    def _write_squad(self, c: Club, members, shirts):
        if len(members) > CLUB_SLOTS:
            raise CareerError("a squad block has 40 slots")
        d, o = self.d, c.offset
        for i in range(CLUB_SLOTS):
            if i < len(members):
                struct.pack_into("<II", d, o + i * 8, *members[i])
                struct.pack_into("<H", d, o + CLUB_SHIRTS + i * 2, shirts[i])
            else:
                struct.pack_into("<II", d, o + i * 8, *EMPTY_PAIR)
                struct.pack_into("<H", d, o + CLUB_SHIRTS + i * 2, 0)
        struct.pack_into("<H", d, o + CLUB_COUNT, len(members))
        self.dirty()

    def release(self, k, pid):
        c = self.club(k)
        keep = [(m, s) for m, s in zip(c.members, c.shirts) if m[1] != pid]
        if len(keep) == len(c.members):
            raise CareerError(f"{pid} is not in club block {k}")
        self._write_squad(c, [m for m, _ in keep], [s for _, s in keep])

    def remove_slot(self, k, slot):
        """Drop one squad slot (used to repair a player the game listed twice)."""
        c = self.club(k)
        members, shirts = list(c.members), list(c.shirts)
        del members[slot], shirts[slot]
        self._write_squad(c, members, shirts)

    def add(self, k, pid, shirt=None, handle=None):
        c = self.club(k)
        if pid in c.pids:
            raise CareerError(f"{pid} is already in club block {k}")
        handle = handle or self.handle_of(pid)
        if handle is None:
            raise CareerError(f"{pid} has no handle in this career")
        if shirt is None or shirt in c.shirts:
            shirt = next(s for s in range(1, 100) if s not in c.shirts)
        self._write_squad(c, c.members + [(handle, pid)], c.shirts + [shirt])

    def swap_identity(self, mapping):
        """Rewrite every (handle, pid) pair per {(h, p): (h2, p2)}, in ONE pass.

        Simultaneous on purpose: applied one swap at a time, a player outgoing in one
        swap and incoming in another vanishes from both clubs.
        """
        a = self.u32().copy()
        key = (a[:-1].astype(np.uint64) << 32) | a[1:]
        want = np.array([(h << 32) | p for h, p in mapping], dtype=np.uint64)
        hits = np.nonzero(np.isin(key, want))[0]
        last, n = -2, 0
        for i in hits.tolist():
            if i <= last + 1:   # never rewrite a word that was just written
                continue
            h, p = mapping[(int(a[i]), int(a[i + 1]))]
            a[i], a[i + 1] = h, p
            last, n = i, n + 1
        self.d[:len(a) * 4] = a.tobytes()
        self.dirty()
        return n
