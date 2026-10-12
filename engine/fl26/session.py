"""An editing session over one career: read views, staged edits, one apply.

Nothing writes until `apply()`. Apply replays the staged edits on a fresh load of the
save, refuses if the validator finds a new error, then goes through safewrite (game-not-
running check, backup into ...\\2026\\backup, verify by re-reading).
"""
from __future__ import annotations

import json
import os
import re
import struct
import unicodedata
from pathlib import Path

from . import attributes as A, created, efdb, i18n, pesmaster, profiles, safewrite, validate
from .i18n import tr
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
FACE_DONOR = 169270          # fallback face (young Brazilian) when no same-nationality donor


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


def _name_tokens(name):
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]+", " ", n).split()


def same_person(a, b):
    """Same player under two IDs? (FL26's patch gave some players their own IDs, e.g. Johan
    Manzambi is 90286 in FL26 and 174191 on efootballdb.) Full names must match, except
    that an abbreviated first name ("A. Harriman-Annous") matches by initial + surname."""
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return False
    if ta == tb:
        return True
    if len(ta) >= 2 and len(tb) >= 2 and (len(ta[0]) == 1 or len(tb[0]) == 1):
        return ta[0][0] == tb[0][0] and ta[1:] == tb[1:]
    return False


class Session:
    def __init__(self, path, db: Database):
        self.path = Path(path)
        self.db = db
        self.staged = []
        self.reload()

    # ------------------------------------------------------------------ loading

    def reload(self):
        self._check_spares()
        self.c = Career.load(self.path)
        self.reg = Registry(self.c)
        self.mgr = Managers(self.c)
        self.ids = identify_blocks(self.c, self.reg, self.db)
        self.rec_of = {self.reg.pid(i): i for i in range(self.reg.count)}
        try:
            self.created_base = created.locate(self.c)
        except LookupError:
            self.created_base = None

    def _check_spares(self):
        """Drop spare mappings the option file no longer backs (e.g. it was restored)."""
        m = load_spares()
        if not m:
            return
        e = self._edit_file()
        if e is None:
            return
        renamed = {}
        for k in range(e.count):
            o = 0x7C + k * 0x138
            if e.d[o + 0x1F] & 0x80:
                renamed[struct.unpack_from("<I", e.d, o)[0]] = True
        good = {real: spare for real, spare in m.items() if spare in renamed}
        if good != m:
            save_spares(good)

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
        try:
            cap = self.mgr.captain(k)
        except LookupError:
            cap = None
        rows = [self._player_row(p, h, s) for (h, p), s in zip(cl.members, cl.shirts)]
        for i, r in enumerate(rows):
            r["captain"] = (i == cap)
        return {"block": k, "name": self.club_name(k), "teamId": self.ids.get(k, (None,))[0],
                "manager": {"id": coach[0], "name": coach[1]}, "players": rows}

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
            row["registeredPosition"] = A.get(rec, "registered_position")
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
            raise EditError(tr("err.notClub"))
        if efdb.made_up(tid, refresh=refresh):
            raise EditError(tr("err.madeUp"))
        rows = efdb.squad(tid, refresh=refresh)
        squad_pids = set(self.c.club(block).pids)
        where = {}
        for cl in self.c.clubs():
            for _, p in cl.members:
                where.setdefault(p, []).append(cl.index)
        plan = {"block": block, "team": self.club_name(block), "coach": efdb.coach(tid),
                "keep": [], "moveIn": [], "add": [], "create": [], "release": [],
                "numbers": {}, "renumber": [], "captain": None}
        current_shirt = dict(zip(self.c.club(block).pids, self.c.club(block).shirts))
        target = set()
        for real, shirt, order, p, a in rows:
            pid = self.career_pid(real)
            target.add(pid)
            item = {"pid": real, "careerPid": pid, "name": p.get("player_name"), "shirt": shirt,
                    "position": p.get("main_position_text"), "age": p.get("age")}
            if isinstance(shirt, int) and 1 <= shirt <= 99:
                plan["numbers"][str(real)] = shirt
                if pid in squad_pids and current_shirt.get(pid) != shirt:
                    plan["renumber"].append({"pid": real, "name": item["name"], "position": item["position"],
                                             "from": current_shirt.get(pid), "to": shirt})
            if a.get("captain"):
                plan["captain"] = {"pid": real, "name": item["name"]}
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
                plan["release"].append({"pid": pid, "name": self.name(pid),
                                        "position": self._player_row(pid).get("position")})
        # a "new" player who is really one of ours under another ID: keep him, not a twin
        for it in list(plan["create"]):
            r = next((r for r in plan["release"] if same_person(it["name"], r["name"])), None)
            if r is None:
                continue
            plan["create"].remove(it)
            plan["release"].remove(r)
            plan["keep"].append({**it, "careerPid": r["pid"], "matchedByName": True})
            n = plan["numbers"].pop(str(it["pid"]), None)
            if n is not None:
                plan["numbers"][str(r["pid"])] = n
                if current_shirt.get(r["pid"]) != n:
                    plan["renumber"].append({"pid": r["pid"], "name": it["name"], "position": it["position"],
                                             "from": current_shirt.get(r["pid"]), "to": n})
            if plan["captain"] and plan["captain"]["pid"] == it["pid"]:
                plan["captain"]["pid"] = r["pid"]
        # second opinion: does pesmaster.com list the same squad?
        cc = pesmaster.cross_check(tid, [r[0] for r in rows], refresh=refresh)
        if "error" not in cc:
            efdb_names = {r[0]: r[3].get("player_name") for r in rows}
            cc["onlyEfdb"] = [efdb_names.get(p) or f"#{p}" for p in cc["onlyEfdb"]]
            cc["onlyPesmaster"] = [self.db.player_name(p) or n for p, n in cc["onlyPesmaster"]]
        plan["crossCheck"] = cc
        return plan

    def _is_club(self, k):
        return (self.ids.get(k, (None,))[0] or 0) >= 100      # national teams are < 100

    def leagues(self):
        """efootballdb leagues whose clubs this career holds (at least half of them)."""
        by_tid = {}
        for k, (tid, conf) in sorted(self.ids.items(), key=lambda kv: -kv[1][1]):
            if tid and self._is_club(k):
                by_tid.setdefault(tid, k)
        mine = self.my_block()
        out = []
        for comp in efdb.competitions():
            if comp["national"]:
                continue
            blocks = [by_tid[t] for t in comp["teams"] if t in by_tid]
            if len(blocks) >= 2 and len(blocks) * 2 >= len(comp["teams"]):
                out.append({"id": comp["id"], "name": comp["name"], "blocks": blocks,
                            "clubs": len(blocks), "total": len(comp["teams"]),
                            "mine": mine in blocks})
        out.sort(key=lambda x: (not x["mine"], x["name"]))
        return out

    def rating(self, pid):
        """Rough strength from the registry abilities (the game's overall is computed)."""
        i = self.rec_of.get(pid)
        if i is None:
            return 0
        rec = self.reg.record(i)
        gk = A.get(rec, "registered_position") == 0
        vals = [A.get(rec, k) for k in A.ABILITIES if k.startswith("gk_") == gk]
        return sum(vals) / len(vals)

    MIN_SQUAD = 23

    def league_plan(self, comp_id, refresh=False, min_squad=MIN_SQUAD):
        """Sync every club of a league at once. Players changing clubs inside the league
        become one move (not a release here and an add there), so nobody is lost.

        Returns {"league", "clubs": [{block, name, keep, ops}], "skipped"}; each op is a
        stageable edit carrying a `label` and a `kind` (release/move/add/create/numbers/
        captain), listed under its destination club."""
        lg = next((x for x in self.leagues() if x["id"] == int(comp_id)), None)
        if lg is None:
            raise EditError(tr("err.noLeague"))
        names = {k: self.club_name(k) for k in lg["blocks"]}
        made_up = [k for k in lg["blocks"] if efdb.made_up(self.ids[k][0], refresh=refresh)]
        blocks = [k for k in lg["blocks"] if k not in made_up]
        members = {k: [p for _, p in self.c.club(k).members] for k in blocks}
        where = {}
        for cl in self.c.clubs():
            if self._is_club(cl.index):
                for _, p in cl.members:
                    where.setdefault(p, []).append(cl.index)
        target, target_of, info, skipped = {}, {}, {}, []
        clubs = {k: {"block": k, "name": names[k], "teamId": self.ids[k][0], "keep": 0,
                     "ops": [], "numbers": {}, "captain": None} for k in blocks}
        for k in blocks:
            target[k] = []
            for real, shirt, order, p, a in efdb.squad(self.ids[k][0], refresh=refresh):
                pid = self.career_pid(real)
                name = p.get("player_name") or f"#{real}"
                if pid in target_of:              # listed by two clubs (loan): first wins
                    skipped.append(tr("skip.twoClubs", name=name, a=names[target_of[pid]], b=names[k]))
                    continue
                target_of[pid] = k
                target[k].append(pid)
                info[pid] = {"real": real, "name": name, "shirt": shirt,
                             "position": p.get("main_position_text"), "age": p.get("age")}
                if isinstance(shirt, int) and 1 <= shirt <= 99:
                    clubs[k]["numbers"][str(real)] = shirt
                if a.get("captain"):
                    clubs[k]["captain"] = {"pid": real, "name": name}
        size = {k: len(self.c.club(k).members) for k in blocks}
        releases, moves, adds, creates = [], [], [], []
        for k in blocks:
            for pid in members[k]:
                if pid < CREATED_ID_MIN and target_of.get(pid) is None:
                    releases.append({"op": "release", "pid": pid, "block": k, "kind": "release",
                                     "name": self.name(pid),
                                     "label": tr("lab.release", name=self.name(pid), club=names[k])})
                    size[k] -= 1
        for k in blocks:
            for pid in target[k]:
                if pid in members[k]:
                    clubs[k]["keep"] += 1
                    continue
                it = info[pid]
                src = [b for b in where.get(pid, []) if b != k]
                if src:
                    frm = src[0]
                    op = {"op": "move", "pid": pid, "from": frm, "to": k, "kind": "move",
                          "fromName": self.club_name(frm),
                          "label": tr("lab.move", name=it["name"], src=self.club_name(frm), dst=names[k])}
                    if frm in size:
                        size[frm] -= 1
                elif self.status(it["real"]) == "record":
                    op = {"op": "add", "pid": pid, "block": k, "kind": "add",
                          "label": tr("lab.add", name=it["name"], club=names[k])}
                else:
                    absent = self.status(it["real"]) != "db"
                    op = {"op": "new", "pid": it["real"], "block": k, "shirt": it["shirt"],
                          "kind": "create", "absent": absent,
                          "label": tr("lab.create", name=it["name"], club=names[k]) + (tr("lab.newToFl26") if absent else "")}
                op.update(name=it["name"], position=it["position"], age=it["age"])
                size[k] += 1
                (moves if op["op"] == "move" else adds if op["op"] == "add" else creates).append(op)
        # a "new" player who is really one of ours under another ID: keep or move him instead
        for op in list(creates):
            r = next((r for r in releases if same_person(op["name"], r["name"])), None)
            if r is None:
                continue
            creates.remove(op)
            releases.remove(r)
            k, fl = op["block"], r["pid"]
            if r["block"] == k:
                clubs[k]["keep"] += 1
            else:
                moves.append({"op": "move", "pid": fl, "from": r["block"], "to": k, "kind": "move",
                              "fromName": names[r["block"]], "name": op["name"], "position": op["position"],
                              "age": op["age"], "label": tr("lab.move", name=op["name"], src=names[r["block"]], dst=names[k])})
            n = clubs[k]["numbers"].pop(str(op["pid"]), None)
            if n is not None:
                clubs[k]["numbers"][str(fl)] = n
            if clubs[k]["captain"] and clubs[k]["captain"]["pid"] == op["pid"]:
                clubs[k]["captain"]["pid"] = fl
        # efootballdb squads can be thin (16-18 players): below `min_squad` a club keeps its
        # best players that were to be released, so AI clubs still field a full bench
        for k in blocks:
            if size[k] >= min_squad:
                continue
            mine = sorted((o for o in releases if o["block"] == k), key=lambda o: -self.rating(o["pid"]))
            for o in mine[:min_squad - size[k]]:
                releases.remove(o)
                clubs[k].setdefault("kept", []).append(o["name"])
                size[k] += 1
        # 40-player cap: drop the last arrivals (lowest in efootballdb's order) that do not fit
        for k in blocks:
            while size[k] > 40:
                for lst in (creates, adds, moves):
                    cut = next((o for o in reversed(lst) if o.get("to", o.get("block")) == k), None)
                    if cut:
                        lst.remove(cut)
                        skipped.append(tr("skip.over40", name=cut["name"], club=names[k]))
                        if cut["op"] == "move" and cut["from"] in size:
                            size[cut["from"]] += 1
                        break
                size[k] -= 1
        for op in releases:
            clubs[op["block"]]["ops"].append(op)
        for op in moves + adds + creates:
            clubs[op.get("to", op.get("block"))]["ops"].append(op)
        for k in blocks:
            cl = clubs[k]
            # numbers and captain only when something would actually change, so a synced
            # league plans to nothing
            arrivals = any(o["kind"] in ("move", "add", "create") for o in cl["ops"])
            squad = self.c.club(k)
            shirt_now = dict(zip(squad.pids, squad.shirts))
            reserved = {n for p, n in shirt_now.items() if p >= CREATED_ID_MIN}   # Giu keeps his
            renumber = arrivals or any(
                shirt_now.get(self.career_pid(int(real))) not in (None, n)
                for real, n in cl["numbers"].items() if n not in reserved)
            if cl["numbers"] and renumber:
                cl["ops"].append({"op": "renumber", "block": k, "numbers": cl["numbers"],
                                  "kind": "numbers", "label": tr("lab.numbers", club=names[k])})
            if cl["captain"] and not arrivals:
                cap = self.career_pid(cl["captain"]["pid"])
                try:
                    if cap in squad.pids and self.mgr.captain(k) == squad.pids.index(cap):
                        cl["captain"] = None              # already wearing the armband
                except LookupError:
                    pass
            if cl["captain"]:
                cl["ops"].append({"op": "captain", "block": k, "pid": cl["captain"]["pid"],
                                  "kind": "captain",
                                  "label": tr("lab.captain", club=names[k], name=cl["captain"]["name"])})
            del cl["numbers"]
        return {"league": lg["name"], "id": lg["id"], "clubs": [clubs[k] for k in blocks],
                "skipped": skipped, "madeUp": [names[k] for k in made_up], "minSquad": min_squad}

    # ------------------------------------------------------------------ staging

    def stage(self, op):
        self._check(op)
        self.staged.append(op)
        return self.staged

    ORDER = {"release": 0, "move": 1, "add": 2, "new": 2, "renumber": 3, "captain": 4}
    UI_ONLY = ("kind", "name", "position", "age", "absent", "fromName")   # `label`, `source` are kept

    def stage_many(self, ops):
        """Stage a batch (a league sync) in a safe order: releases, moves, arrivals, then
        numbers and captains. All or nothing. Returns the ops in staged order."""
        ops = sorted(ops, key=lambda o: self.ORDER.get(o.get("op"), 5))
        n = len(self.staged)
        try:
            for op in ops:
                op = {k: v for k, v in op.items() if k not in self.UI_ONLY}
                self._check(op)
                self.staged.append(op)
        except Exception:
            del self.staged[n:]
            raise
        return {"staged": self.staged, "order": ops}

    def unstage(self, index):
        del self.staged[index]
        return self.staged

    def unstage_all(self):
        self.staged = []
        return self.staged

    def describe(self, ops=None):
        """What a batch of edits does, for the backup taken before it is applied:
        {kind, title, summary, counts, clubs, edits}, in the current language."""
        ops = self.staged if ops is None else ops
        counts = {}
        for o in ops:
            k = "manager" if o["op"].startswith("manager") else o["op"]
            counts[k] = counts.get(k, 0) + 1
        blocks = set()
        for o in ops:
            for key in ("block", "from", "to", "a", "b"):
                if isinstance(o.get(key), int):
                    blocks.add(o[key])
        clubs = sorted(self.club_name(k) for k in blocks)
        summary = " · ".join(i18n.count(k, n) for k, n in sorted(counts.items(), key=lambda kv: -kv[1]))
        sources = []
        for o in ops:
            if o.get("source") and o["source"] not in sources:
                sources.append(o["source"])
        if sources and sum(1 for o in ops if o.get("source")) * 2 >= len(ops):
            title = " + ".join(sources[:2]) + (tr("desc.more", n=len(sources) - 2) if len(sources) > 2 else "")
        elif len(ops) == 1:
            title = ops[0].get("label") or summary
        elif len(clubs) == 1:
            title = tr("desc.atClub", n=len(ops), club=clubs[0])
        else:
            title = tr("desc.acrossClubs", n=len(ops), c=len(clubs)) if clubs else tr("desc.edits", n=len(ops))
        return {"kind": "apply", "title": title, "summary": summary, "counts": counts,
                "clubs": clubs, "edits": [o.get("label") or o["op"] for o in ops]}

    def _check(self, op):
        kind = op.get("op")
        pid = op.get("pid")
        if kind not in ("move", "release", "add", "attr", "created", "manager_swap",
                        "manager_set", "tactics_copy", "shirt", "new", "renumber", "captain",
                        "dedupe"):
            raise EditError(tr("err.unknownEdit", kind=kind))
        if kind in ("move", "release", "add") and pid and pid >= CREATED_ID_MIN:
            raise EditError(tr("err.createdNotMoved"))
        if kind == "add" and pid not in self.rec_of:
            raise EditError(tr("err.noRecord"))
        if kind in ("add", "move", "new"):
            to = op.get("to", op.get("block"))
            planned = sum(1 for o in self.staged if o.get("to", o.get("block")) == to
                          and o["op"] in ("add", "move", "new")) - sum(
                1 for o in self.staged if o["op"] == "release" and o.get("block") == to) - sum(
                1 for o in self.staged if o["op"] == "move" and o.get("from") == to)
            if len(self.c.club(to).members) + planned + 1 > 40:
                raise EditError(tr("err.max40"))

    # -------------------------------------------------------------------- apply

    def _gap(self, reg, rec_of):
        """Season gap: career ages minus efootballdb ages, from the user's own club."""
        k = self.my_block()
        tid = self.ids.get(k, (None,))[0] if k is not None else None
        if not tid:
            return 0
        return profiles.season_gap(reg, rec_of, [x for *_, x, _ in efdb.squad(tid)])

    @staticmethod
    def _release(c, mgr, k, pid):
        slot = c.club(k).pids.index(pid)
        c.release(k, pid)
        try:
            mgr.slot_removed(k, slot)
        except LookupError:
            pass

    @staticmethod
    def _add(c, mgr, k, pid, shirt, handle):
        c.add(k, pid, shirt=shirt, handle=handle)
        try:
            mgr.slot_added(k, len(c.club(k).members) - 1)
        except LookupError:
            pass

    @staticmethod
    def _dedupe(c, mgr, k):
        """Keep the first entry of every player listed more than once in squad k."""
        seen, extra = set(), []
        for slot, pid in enumerate(c.club(k).pids):
            (extra.append(slot) if pid in seen else seen.add(pid))
        for slot in reversed(extra):
            c.remove_slot(k, slot)
            try:
                mgr.slot_removed(k, slot)
            except LookupError:
                pass

    def duplicates(self):
        """Players the game lists twice in one squad (it does this at season rollover)."""
        out = []
        for cl in self.c.clubs():
            counts = {}
            for p in cl.pids:
                counts[p] = counts.get(p, 0) + 1
            for p, n in counts.items():
                if n > 1:
                    out.append({"block": cl.index, "club": self.club_name(cl.index), "pid": p,
                                "name": self.name(p), "copies": n})
        return out

    def export_csv(self, path, block=None):
        """Squads to CSV (UTF-8 with BOM so Excel reads accents): one club or every club."""
        import csv
        blocks = [block] if block is not None else [cl.index for cl in self.c.clubs() if self._is_club(cl.index)]
        rows = 0
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["club", "team_id", "shirt", "player_id", "name", "position", "age", "rating",
                        "speed", "captain"])
            for k in blocks:
                sq = self.squad(k)
                for r in sq["players"]:
                    rating = self.rating(r["pid"]) if r["pid"] < CREATED_ID_MIN else ""
                    w.writerow([sq["name"], sq["teamId"] or "", r.get("shirt") or "", r["pid"], r["name"],
                                r.get("position") or "", r.get("age") or "",
                                round(rating) if rating != "" else "", r.get("speed") or "",
                                "yes" if r.get("captain") else ""])
                    rows += 1
        return {"path": str(path), "rows": rows, "clubs": len(blocks)}

    @staticmethod
    def _renumber(c, k, numbers):
        """Set shirt numbers {pid: shirt} in one go; others keep theirs unless clashing."""
        cl = c.club(k)
        want = {int(p): int(n) for p, n in numbers.items() if int(p) in cl.pids and 1 <= int(n) <= 99}
        # the created character keeps his own number (his "preferred number" in BAL);
        # whoever was meant to take it gets a free one instead
        mine = {p: n for p, n in zip(cl.pids, cl.shirts) if p >= CREATED_ID_MIN and n}
        want = {p: n for p, n in want.items() if p not in mine and n not in mine.values()}
        want.update(mine)
        taken = set(want.values())
        out = []
        for p, cur in zip(cl.pids, cl.shirts):
            if p in want:
                out.append(want[p])
            elif cur in taken or cur == 0:
                free = next(n for n in range(1, 100) if n not in taken)
                taken.add(free)
                out.append(free)
            else:
                taken.add(cur)
                out.append(cur)
        for i, n in enumerate(out):
            struct.pack_into("<H", c.d, cl.offset + 0x14E + i * 2, n)

    def _apply_ops(self, c, reg, mgr, edit=None):
        """Replay staged edits on (c, reg, mgr). Returns {real ID: spare ID} newly lent."""
        rec_of = {reg.pid(i): i for i in range(reg.count)}
        spares = load_spares()
        new_spares = {}
        gap = None
        db_tables = None
        # each destination club's context donor, taken before releases can empty a squad
        donor = {k: profiles.mate_index(c, reg, k)
                for k in {o["block"] for o in self.staged if o["op"] == "new"}}
        for op in self._expand_moves(self.staged):
            kind = op["op"]
            if kind == "new":
                real = int(op["pid"])
                p = efdb.player(real)
                gap = 0       # real ages: a created player arrives as old as he really is
                pid = spares.get(real) or new_spares.get(real)
                if pid is None and real in self.db.player_names:
                    if real in rec_of:
                        raise EditError(tr("err.hasRecord", name=p.get("player_name")))
                    h = profiles.build_new_player(c, reg, real, op["block"], p, gap,
                                                  mate=donor[op["block"]])
                    rec_of[real] = h & 0xFFFF
                    self._add(c, mgr, op["block"], real, op.get("shirt"), h)
                    continue
                if pid is None:                       # FL26 lacks him: lend a spare ID
                    if edit is None:
                        raise EditError(tr("err.needsEdit"))
                    edit_pids = {struct.unpack_from("<I", edit.d, 0x7C + k * 0x138)[0]
                                 for k in range(edit.count)}
                    pid, si = profiles.pick_spare(c, reg, self.db, edit_pids,
                                                  exclude=set(spares.values()) | set(new_spares.values()))
                    if db_tables is None:
                        db_tables = load_db_tables(DEFAULT_DUMP)
                    players, faces = db_tables
                    nat = (p.get("nationality_a") or {}).get("country_id")
                    face = profiles.face_donor(players, faces, self.db, nat, real,
                                               exclude={pid}) if nat else FACE_DONOR
                    edit.add_player(pid, p.get("player_name", f"#{real}"),
                                    (p.get("shirt_name") or p.get("player_name", "")).upper(),
                                    players[pid], faces.get(face, faces[pid]),
                                    p.get("height"), p.get("weight"),
                                    (p.get("nationality_a") or {}).get("country_id"))
                    new_spares[real] = pid
                else:                                 # already lent earlier: reuse the spare
                    si = rec_of.get(pid)
                    if si is None:
                        raise EditError(tr("err.spareNoRecord", pid=pid, real=real))
                    for k in c.club_of(pid):
                        self._release(c, mgr, k, pid)
                h = profiles.adopt_spare(c, reg, si, op["block"], p, gap, mate=donor[op["block"]])
                self._add(c, mgr, op["block"], pid, op.get("shirt"), h)
            elif kind == "release":
                self._release(c, mgr, op["block"], op["pid"])
            elif kind == "_out":
                self._release(c, mgr, op["from"], op["pid"])
            elif kind in ("add", "move", "_in"):
                if kind == "move":
                    self._release(c, mgr, op["from"], op["pid"])
                to = op["block"] if kind == "add" else op["to"]
                i = rec_of[op["pid"]]
                self._add(c, mgr, to, op["pid"], op.get("shirt"), reg.handle(i))
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
            elif kind == "tactics_copy":
                mgr.copy_tactics(op["block"], op["from"])
            elif kind == "dedupe":
                self._dedupe(c, mgr, op["block"])
            elif kind == "shirt":
                self._renumber(c, op["block"], {op["pid"]: op["shirt"]})
            elif kind == "renumber":
                pid_map = {**{str(k): v for k, v in spares.items()}, **{str(k): v for k, v in new_spares.items()}}
                self._renumber(c, op["block"], {pid_map.get(str(p), p): n for p, n in op["numbers"].items()})
            elif kind == "captain":
                pid = (spares.get(int(op["pid"])) or new_spares.get(int(op["pid"])) or int(op["pid"]))
                cl = c.club(op["block"])
                if pid in cl.pids:
                    mgr.set_captain(op["block"], cl.pids.index(pid))
        reg.commit()
        return new_spares

    @staticmethod
    def _expand_moves(ops):
        """A run of moves (a league sync) is applied as all departures, then all arrivals,
        so a full squad can let a player go before it receives one."""
        out, i = [], 0
        while i < len(ops):
            j = i
            while j < len(ops) and ops[j]["op"] == "move":
                j += 1
            run = ops[i:j]
            if len(run) > 1 and len({o["pid"] for o in run}) == len(run):
                out += [{**o, "op": "_out"} for o in run] + [{**o, "op": "_in"} for o in run]
            elif run:
                out += run
            else:
                out.append(ops[i])
                j = i + 1
            i = j
        return out

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
            raise EditError(tr("err.nothing"))
        c = Career.load(self.path)
        edit = self._edit_file()
        before = validate.check(c)
        new_spares = self._apply_ops(c, Registry(c), Managers(c), edit)
        new = validate.new_problems(before, validate.check(c))
        if new:
            raise EditError(tr("err.refused")
                            + "; ".join(str(p) for p in new[:5]))
        label = f"careerlab-{len(self.staged)}-edits"
        meta = self.describe()
        if new_spares:            # option file first: a renamed spare is harmless on its own
            safewrite.write_file(edit, label, meta={**meta, "title": tr("desc.optionFile", n=len(new_spares), title=meta["title"])})
        backup = safewrite.write(c, label, meta=meta)
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
        out = []
        for p in safewrite.list_backups(self.path):
            m = safewrite.read_meta(p) or {}
            out.append({"file": str(p), "name": p.name, "size": p.stat().st_size,
                        "kind": m.get("kind") or self._kind_from_name(p.name),
                        "title": m.get("title"), "summary": m.get("summary", ""),
                        "clubs": m.get("clubs", []), "edits": m.get("edits", [])})
        return out

    @staticmethod
    def _kind_from_name(name):
        """Backups made before descriptions existed: guess from the file name."""
        if "before-restore" in name:
            return "restore"
        return "apply" if "careerlab" in name else "other"

    def restore(self, file):
        safewrite.restore(self.path, file)
        self.staged = []
        self.reload()
        return self.summary()
