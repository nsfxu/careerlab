"""An editing session over one career: read views, staged edits, one apply.

Nothing writes until `apply()`. Apply replays the staged edits on a fresh load of the
save, refuses if the validator finds a new error, then goes through safewrite (game-not-
running check, backup into ...\\2026\\backup, verify by re-reading).
"""
from __future__ import annotations

import json
import os
import struct
from pathlib import Path

from . import attributes as A, created, efdb, profiles, safewrite, validate
from .career import CREATED_ID_MIN, Career
from .database import DEFAULT_DUMP, Database, identify_blocks
from .editfile import EditFile, load_db_tables
from .managers import Managers
from .registry import REC, Registry

POS_NAMES = "GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF".split()
CLUB_CONTEXT = [(0x28, 0x74), (0x80, 0x84)]      # competitions, current club
# Cheat Engine table names that differ from the registry's skill names
CREATED_SKILL_ALIASES = {"dipping_shot": "dipping_shots"}

SPARES = Path(os.environ.get("LOCALAPPDATA", ".")) / "CareerLab" / "spares.json"
FACE_DONOR = 169270          # young Brazilian whose face new players borrow (FL26 has none)


def load_spares():
    """{real eFootball ID: spare FL26 ID} for players FL26 lacks. Install-wide, because the
    option file that renames the spare is install-wide."""
    try:
        return {int(k): v for k, v in json.loads(SPARES.read_text(encoding="utf-8")).items()}
    except (OSError, ValueError):
        return {}


def save_spares(m):
    SPARES.parent.mkdir(parents=True, exist_ok=True)
    SPARES.write_text(json.dumps({str(k): v for k, v in m.items()}, indent=1), encoding="utf-8")


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

    def my_block(self):
        blocks = self.c.club_of(0x800000BA)
        # his club, not a representative squad: national teams have IDs under 100
        return next((k for k in blocks if (self.ids.get(k, (None,))[0] or 0) >= 100),
                    blocks[0] if blocks else None)

    def summary(self):
        me = None
        if self.created_base is not None:
            b = self.created_base
            club = self.my_block()
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

    # ------------------------------------------------------------- efootballdb

    def career_pid(self, real_pid):
        """FL26 ID used for an eFootball player (his own, or the spare lent to him)."""
        return load_spares().get(real_pid, real_pid)

    def status(self, real_pid):
        """'record' (career knows him) | 'db' (in FL26, new to career) | 'absent' (FL26 lacks him)."""
        pid = self.career_pid(real_pid)
        if pid != real_pid:
            return "record" if pid in self.rec_of and self.c.club_of(pid) else "spare"
        if real_pid in self.rec_of:
            return "record"
        return "db" if real_pid in self.db.player_names else "absent"

    def sync_plan(self, block, refresh=False):
        """Bring a club's squad to efootballdb's: keep, move in, add, create, release."""
        tid = self.ids.get(block, (None,))[0]
        if not tid:
            raise EditError("this squad is not identified as a club, so it cannot be synced")
        rows = efdb.squad(tid, refresh=refresh)
        squad_pids = set(self.c.club(block).pids)
        where = {}
        for cl in self.c.clubs():
            for _, p in cl.members:
                where.setdefault(p, []).append(cl.index)
        plan = {"block": block, "team": self.club_name(block), "coach": efdb.coach(tid),
                "keep": [], "moveIn": [], "add": [], "create": [], "release": []}
        target = set()
        for real, shirt, order, p, a in rows:
            pid = self.career_pid(real)
            target.add(pid)
            item = {"pid": real, "careerPid": pid, "name": p.get("player_name"), "shirt": shirt,
                    "position": p.get("main_position_text"), "age": p.get("age")}
            st = self.status(real)
            if pid in squad_pids:
                plan["keep"].append(item)
            elif st == "record":
                clubs = [k for k in where.get(pid, [])
                         if k != block and (self.ids.get(k, (None,))[0] or 0) >= 100]
                if clubs:
                    item["from"] = clubs[0]
                    item["fromName"] = self.club_name(clubs[0])
                    plan["moveIn"].append(item)
                else:
                    plan["add"].append(item)
            else:
                item["kind"] = st
                plan["create"].append(item)
        for h, pid in self.c.club(block).members:
            if pid not in target and pid < CREATED_ID_MIN:
                plan["release"].append({"pid": pid, "name": self.name(pid)})
        return plan

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
        if kind not in ("move", "release", "add", "attr", "created", "manager_swap",
                        "manager_set", "shirt", "new"):
            raise EditError(f"unknown edit {kind}")
        if kind in ("move", "release", "add") and pid and pid >= CREATED_ID_MIN:
            raise EditError("the created character is not moved by squad tools")
        if kind == "add" and pid not in self.rec_of:
            raise EditError("this player has no career record: use create instead")
        if kind in ("add", "move", "new"):
            to = op.get("to", op.get("block"))
            planned = sum(1 for o in self.staged if o.get("to", o.get("block")) == to
                          and o["op"] in ("add", "move", "new")) - sum(
                1 for o in self.staged if o["op"] == "release" and o.get("block") == to) - sum(
                1 for o in self.staged if o["op"] == "move" and o.get("from") == to)
            if len(self.c.club(to).members) + planned + 1 > 40:
                raise EditError("a squad holds at most 40 players")

    # -------------------------------------------------------------------- apply

    def _gap(self, reg, rec_of):
        """Season gap: career ages minus efootballdb ages, from the user's own club."""
        k = self.my_block()
        tid = self.ids.get(k, (None,))[0] if k is not None else None
        if not tid:
            return 0
        return profiles.season_gap(reg, rec_of, [x for *_, x, _ in efdb.squad(tid)])

    def _apply_ops(self, c, reg, mgr, edit=None):
        """Replay staged edits on (c, reg, mgr). Returns {real ID: spare ID} newly lent."""
        rec_of = {reg.pid(i): i for i in range(reg.count)}
        spares = load_spares()
        new_spares = {}
        gap = None
        db_tables = None
        for op in self.staged:
            kind = op["op"]
            if kind == "new":
                real = int(op["pid"])
                p = efdb.player(real)
                if gap is None:
                    gap = self._gap(reg, rec_of)
                pid = spares.get(real) or new_spares.get(real)
                if pid is None and real in self.db.player_names:
                    if real in rec_of:
                        raise EditError(f"{p.get('player_name')} already has a career record")
                    h = profiles.build_new_player(c, reg, real, op["block"], p, gap)
                    rec_of[real] = h & 0xFFFF
                    c.add(op["block"], real, shirt=op.get("shirt"), handle=h)
                    continue
                if pid is None:                       # FL26 lacks him: lend a spare ID
                    if edit is None:
                        raise EditError("creating a player FL26 lacks needs the option file")
                    edit_pids = {struct.unpack_from("<I", edit.d, 0x7C + k * 0x138)[0]
                                 for k in range(edit.count)}
                    pid, si = profiles.pick_spare(c, reg, self.db, edit_pids,
                                                  exclude=set(spares.values()) | set(new_spares.values()))
                    if db_tables is None:
                        db_tables = load_db_tables(DEFAULT_DUMP)
                    players, faces = db_tables
                    edit.add_player(pid, p.get("player_name", f"#{real}"),
                                    (p.get("shirt_name") or p.get("player_name", "")).upper(),
                                    players[pid], faces.get(FACE_DONOR, faces[pid]),
                                    p.get("height"), p.get("weight"),
                                    (p.get("nationality_a") or {}).get("country_id"))
                    new_spares[real] = pid
                else:                                 # already lent earlier: reuse the spare
                    si = rec_of.get(pid)
                    if si is None:
                        raise EditError(f"the spare ID {pid} for {real} has no career record")
                    for k in c.club_of(pid):
                        c.release(k, pid)
                h = profiles.adopt_spare(c, reg, si, op["block"], p, gap)
                c.add(op["block"], pid, shirt=op.get("shirt"), handle=h)
            elif kind == "release":
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
        return new_spares

    def _edit_file(self):
        p = self.path.parent / "EDIT00000000"
        return EditFile(p) if p.exists() else None

    def preview(self):
        """Apply to a scratch copy and report validator differences, without writing."""
        c = Career.load(self.path)
        before = validate.check(c)
        self._apply_ops(c, Registry(c), Managers(c), self._edit_file())
        new = validate.new_problems(before, validate.check(c))
        return {"edits": len(self.staged), "newProblems": [str(p) for p in new]}

    def apply(self):
        if not self.staged:
            raise EditError("nothing staged")
        c = Career.load(self.path)
        edit = self._edit_file()
        before = validate.check(c)
        new_spares = self._apply_ops(c, Registry(c), Managers(c), edit)
        new = validate.new_problems(before, validate.check(c))
        if new:
            raise EditError("refused: the edits would introduce problems: "
                            + "; ".join(str(p) for p in new[:5]))
        label = f"careerlab-{len(self.staged)}-edits"
        if new_spares:            # option file first: a renamed spare is harmless on its own
            safewrite.write_file(edit, label)
        backup = safewrite.write(c, label)
        if new_spares:
            m = load_spares()
            m.update(new_spares)
            save_spares(m)
            self.db = Database(DEFAULT_DUMP, self.path.parent / "EDIT00000000")
        n = len(self.staged)
        self.staged = []
        self.reload()
        return {"applied": n, "backup": str(backup), "newPlayers": len(new_spares)}

    # ------------------------------------------------------------------ backups

    def backups(self):
        return [{"file": str(p), "name": p.name, "size": p.stat().st_size}
                for p in safewrite.list_backups(self.path)]

    def restore(self, file):
        safewrite.restore(self.path, file)
        self.staged = []
        self.reload()
        return self.summary()
