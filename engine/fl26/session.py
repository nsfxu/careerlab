"""An editing session over one career: read views, staged edits, one apply.

Nothing writes until `apply()`. Apply replays the staged edits on a fresh load of the
save, refuses if the validator finds a new error, then goes through safewrite (game-not-
running check, backup into ...\\2026\\backup, verify by re-reading).
"""
from __future__ import annotations

import struct
from pathlib import Path

from . import attributes as A, created, safewrite, validate
from .career import CREATED_ID_MIN, Career
from .database import Database, identify_blocks
from .managers import Managers
from .registry import REC, Registry

POS_NAMES = "GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF".split()
CLUB_CONTEXT = [(0x28, 0x74), (0x80, 0x84)]      # competitions, current club
# Cheat Engine table names that differ from the registry's skill names
CREATED_SKILL_ALIASES = {"heading_skill": "heading", "dipping_shot": "dipping_shots",
                         "gk_low_punt": "gk_low_punt"}


class EditError(RuntimeError):
    pass


class Session:
    def __init__(self, path, db: Database):
        self.path = Path(path)
        self.db = db
        self.staged = []
        self.reload()

    # ------------------------------------------------------------------ loading

    def reload(self):
        self.c = Career.load(self.path)
        self.reg = Registry(self.c)
        self.mgr = Managers(self.c)
        self.ids = identify_blocks(self.c, self.reg, self.db)
        self.rec_of = {self.reg.pid(i): i for i in range(self.reg.count)}
        try:
            self.created_base = created.locate(self.c)
        except LookupError:
            self.created_base = None

    # -------------------------------------------------------------------- views

    def name(self, pid):
        if pid >= CREATED_ID_MIN and self.created_base is not None:
            return created.name(self.c, self.created_base)
        return self.db.player_name(pid) or f"#{pid}"

    def club_name(self, k):
        tid, conf = self.ids.get(k, (None, 0))
        return self.db.team_name(tid) if tid else f"Squad {k}"

    def summary(self):
        me = None
        if self.created_base is not None:
            b = self.created_base
            blocks = self.c.club_of(0x800000BA)
            club = next((k for k in blocks if self.ids.get(k, (None,))[0] and self.ids[k][0] < 1000
                         or self.ids.get(k, (None,))[0]), None)
            me = {"name": created.name(self.c, b), "age": created.get(self.c, b, "age"),
                  "block": club, "club": self.club_name(club) if club is not None else None}
        return {"path": str(self.path), "slot": self.path.name, "clubs": len(self.c.clubs()),
                "registry": self.reg.count, "capacity": self.reg.capacity, "me": me,
                "staged": len(self.staged)}

    def clubs(self):
        out = []
        for cl in self.c.clubs():
            tid, conf = self.ids.get(cl.index, (None, 0))
            try:
                coach = self.mgr.get(cl.index)[1]
            except LookupError:
                coach = ""
            out.append({"block": cl.index, "teamId": tid, "name": self.club_name(cl.index),
                        "confidence": conf, "size": len(cl.members), "manager": coach})
        return out

    def _player_row(self, pid, handle=None, shirt=None):
        row = {"pid": pid, "name": self.name(pid), "shirt": shirt, "handle": handle,
               "created": pid >= CREATED_ID_MIN}
        if pid >= CREATED_ID_MIN and self.created_base is not None:
            b = self.created_base
            row.update(position=POS_NAMES[created.get(self.c, b, "registred_position")],
                       age=created.get(self.c, b, "age"))
            return row
        i = self.rec_of.get(pid)
        if i is not None:
            rec = self.reg.record(i)
            pos = A.get(rec, "registered_position")
            row.update(position=POS_NAMES[pos] if pos < 13 else "?", age=A.get(rec, "age"),
                       speed=A.get(rec, "speed"))
        return row

    def squad(self, k):
        cl = self.c.club(k)
        try:
            coach = self.mgr.get(k)
        except LookupError:
            coach = (None, "")
        return {"block": k, "name": self.club_name(k), "teamId": self.ids.get(k, (None,))[0],
                "manager": {"id": coach[0], "name": coach[1]},
                "players": [self._player_row(p, h, s) for (h, p), s in zip(cl.members, cl.shirts)]}

    def player(self, pid):
        row = self._player_row(pid)
        row["blocks"] = [{"block": k, "name": self.club_name(k)} for k in self.c.club_of(pid)]
        if pid >= CREATED_ID_MIN and self.created_base is not None:
            b = self.created_base
            row["fields"] = {f: created.get(self.c, b, f) for f in created.FIELDS}
            row["kind"] = "created"
            # skills under the registry's names, so the UI treats both kinds alike
            row["skillFields"] = {CREATED_SKILL_ALIASES.get(f, f): f for f, (_, _, bl) in created.FIELDS.items()
                                  if bl == 1 and CREATED_SKILL_ALIASES.get(f, f) in A.SKILLS}
            row["skills"] = [k for k, f in row["skillFields"].items() if row["fields"][f]]
            return row
        i = self.rec_of.get(pid)
        row["kind"] = "registry" if i is not None else "unknown"
        if i is not None:
            rec = self.reg.record(i)
            row["abilities"] = {k: A.get(rec, k) for k in A.ABILITIES}
            row["skills"] = [k for k in A.SKILLS if A.get(rec, k)]
            row["positions"] = {k[4:]: A.get(rec, k) for k in A.FIELDS if k.startswith("pos_")}
            row["form"] = A.get(rec, "form")
            row["weakFoot"] = [A.get(rec, "weak_foot_usage"), A.get(rec, "weak_foot_accuracy")]
            row["style"] = A.get(rec, "playing_style")
        return row

    def search(self, query, limit=60):
        q = query.strip().lower()
        if len(q) < 2:
            return []
        where = {}
        for cl in self.c.clubs():
            for _, p in cl.members:
                where.setdefault(p, []).append(cl.index)
        out = []
        for pid, nm in self.db.player_names.items():
            if q in nm.lower():
                out.append({"pid": pid, "name": nm, "hasRecord": pid in self.rec_of,
                            "blocks": [{"block": k, "name": self.club_name(k)} for k in where.get(pid, [])]})
                if len(out) >= limit:
                    break
        return out

    # ------------------------------------------------------------------ staging

    def stage(self, op):
        self._check(op)
        self.staged.append(op)
        return self.staged

    def unstage(self, index):
        del self.staged[index]
        return self.staged

    def _check(self, op):
        kind = op.get("op")
        pid = op.get("pid")
        if kind in ("move", "release", "add") and pid and pid >= CREATED_ID_MIN:
            raise EditError("the created character is not moved by squad tools")
        if kind == "add" and pid not in self.rec_of:
            raise EditError("this player has no record in the career yet (new-player creation "
                            "is not wired up in this build)")
        if kind not in ("move", "release", "add", "attr", "created", "manager_swap",
                        "manager_set", "shirt"):
            raise EditError(f"unknown edit {kind}")

    # -------------------------------------------------------------------- apply

    def _club_value(self, c, reg, k):
        """Most common registry club-context of a block, from its members."""
        import collections
        votes = collections.Counter()
        for h, p in c.club(k).members:
            i = h & 0xFFFF
            if i < reg.count and reg.pid(i) == p:
                votes[bytes(reg.blob[i * REC + 0x80:i * REC + 0x84])] += 1
        return votes.most_common(1)[0][0] if votes else None

    def _apply_ops(self, c, reg, mgr):
        rec_of = {reg.pid(i): i for i in range(reg.count)}
        for op in self.staged:
            kind = op["op"]
            if kind == "release":
                c.release(op["block"], op["pid"])
            elif kind in ("add", "move"):
                if kind == "move":
                    c.release(op["from"], op["pid"])
                to = op["to"] if kind == "move" else op["block"]
                i = rec_of[op["pid"]]
                c.add(to, op["pid"], shirt=op.get("shirt"), handle=reg.handle(i))
                # keep the record's club in step with the squad it now sits in
                mate = next((h & 0xFFFF for h, p in c.club(to).members
                             if p != op["pid"] and p < CREATED_ID_MIN
                             and (h & 0xFFFF) < reg.count and reg.pid(h & 0xFFFF) == p), None)
                if mate is not None:
                    for lo, hi in CLUB_CONTEXT:
                        reg.blob[i * REC + lo:i * REC + hi] = reg.blob[mate * REC + lo:mate * REC + hi]
            elif kind == "attr":
                i = rec_of[op["pid"]]
                rec = bytearray(reg.record(i))
                A.set(rec, op["field"], int(op["value"]))
                reg.blob[i * REC:(i + 1) * REC] = rec
            elif kind == "created":
                created.set(c, created.locate(c), op["field"], int(op["value"]))
            elif kind == "manager_swap":
                mgr.swap(op["a"], op["b"])
            elif kind == "manager_set":
                mgr.set(op["block"], int(op["coachId"]), op["name"])
            elif kind == "shirt":
                cl = c.club(op["block"])
                idx = cl.pids.index(op["pid"])
                struct.pack_into("<H", c.d, cl.offset + 0x14E + idx * 2, int(op["shirt"]))
        reg.commit()

    def preview(self):
        """Apply to a scratch copy and report validator differences, without writing."""
        c = Career.load(self.path)
        before = validate.check(c)
        self._apply_ops(c, Registry(c), Managers(c))
        new = validate.new_problems(before, validate.check(c))
        return {"edits": len(self.staged), "newProblems": [str(p) for p in new]}

    def apply(self):
        if not self.staged:
            raise EditError("nothing staged")
        c = Career.load(self.path)
        before = validate.check(c)
        self._apply_ops(c, Registry(c), Managers(c))
        new = validate.new_problems(before, validate.check(c))
        if new:
            raise EditError("refused: the edits would introduce problems: "
                            + "; ".join(str(p) for p in new[:5]))
        backup = safewrite.write(c, f"careerlab-{len(self.staged)}-edits")
        n = len(self.staged)
        self.staged = []
        self.reload()
        return {"applied": n, "backup": str(backup)}

    # ------------------------------------------------------------------ backups

    def backups(self):
        return [{"file": str(p), "name": p.name, "size": p.stat().st_size}
                for p in safewrite.list_backups(self.path)]

    def restore(self, file):
        safewrite.restore(self.path, file)
        self.staged = []
        self.reload()
        return self.summary()
