"""What changed between two states of the same career (read-only).

Club blocks are fixed slots, so a block index means the same club in both saves; players are
compared by ID. Used for "what did the game do since last time" (auto snapshots) and for
"compare with this backup".
"""
from __future__ import annotations

from . import attributes as A, created
from .career import CREATED_ID_MIN, Career
from .managers import Managers
from .registry import Registry


def _rating(rec):
    """Rough strength from the registry abilities (the game computes the real overall)."""
    gk = A.get(rec, "registered_position") == 0
    vals = [A.get(rec, k) for k in A.ABILITIES if k.startswith("gk_") == gk]
    return round(sum(vals) / len(vals))


class View:
    """Everything the comparison needs from one save."""

    def __init__(self, path):
        self.c = Career.load(path)
        self.reg = Registry(self.c)
        try:
            self.mgr = Managers(self.c)
        except LookupError:
            self.mgr = None
        self.rec_of = {self.reg.pid(i): i for i in range(self.reg.count)}
        self.squads = {cl.index: [p for _, p in cl.members] for cl in self.c.clubs()}
        try:
            self.created_base = created.locate(self.c)
        except LookupError:
            self.created_base = None

    def manager(self, k):
        try:
            return self.mgr.get(k) if self.mgr else (None, "")
        except LookupError:
            return (None, "")

    def player(self, pid):
        i = self.rec_of.get(pid)
        if i is None:
            return None
        rec = self.reg.record(i)
        return {"rating": _rating(rec), "age": A.get(rec, "age"),
                "abilities": {k: A.get(rec, k) for k in A.ABILITIES}}

    def me(self):
        if self.created_base is None:
            return None
        b = self.created_base
        out = {}
        for k in A.ABILITIES:
            try:
                out[k] = created.get(self.c, b, k)
            except KeyError:
                pass
        for k in ("age",):
            out[k] = created.get(self.c, b, k)
        return out


def compare(old: View, new: View, name, club_name, is_club, my_block=None):
    """Differences old → new. `name(pid)`, `club_name(block)`, `is_club(block)` come from the
    session (database names and club identification)."""
    where_old, where_new = {}, {}
    for k, ps in old.squads.items():
        if is_club(k):
            for p in ps:
                where_old.setdefault(p, k)
    for k, ps in new.squads.items():
        if is_club(k):
            for p in ps:
                where_new.setdefault(p, k)

    transfers, joined, left, regens = [], [], [], []
    for p in set(where_old) | set(where_new):
        if p >= CREATED_ID_MIN:
            continue
        a, b = where_old.get(p), where_new.get(p)
        if a == b:
            continue
        item = {"pid": p, "name": name(p)}
        if a is not None:
            item.update(fromBlock=a, fromName=club_name(a))
        if b is not None:
            item.update(toBlock=b, toName=club_name(b))
        (transfers if a is not None and b is not None else joined if b is not None else left).append(item)
    for p in set(where_old) & set(where_new):
        po, pn = old.player(p), new.player(p)
        if po and pn and pn["age"] + 5 < po["age"]:      # retired and came back as a youngster
            regens.append({"pid": p, "name": name(p), "fromAge": po["age"], "toAge": pn["age"],
                           "club": club_name(where_new[p])})
    key = lambda x: (x.get("toName") or x.get("fromName") or "", x["name"])
    transfers.sort(key=key), joined.sort(key=key), left.sort(key=key)

    managers = []
    for k in new.squads:
        if not is_club(k):
            continue
        (ia, na), (ib, nb) = old.manager(k), new.manager(k)
        if ia != ib and (na or nb):
            managers.append({"block": k, "club": club_name(k), "from": na, "to": nb})
    managers.sort(key=lambda x: x["club"])

    out = {"transfers": transfers, "joined": joined, "left": left, "regens": regens,
           "managers": managers, "myClub": None, "me": None}

    if my_block is not None:
        ins = [t for t in transfers + joined if t.get("toBlock") == my_block]
        outs = [t for t in transfers + left if t.get("fromBlock") == my_block]
        ratings = []
        for p in new.squads.get(my_block, []):
            if p >= CREATED_ID_MIN:
                continue
            po, pn = old.player(p), new.player(p)
            if po and pn and po["rating"] != pn["rating"]:
                ratings.append({"pid": p, "name": name(p), "from": po["rating"], "to": pn["rating"]})
        ratings.sort(key=lambda r: -abs(r["to"] - r["from"]))
        out["myClub"] = {"block": my_block, "name": club_name(my_block), "in": ins, "out": outs,
                         "ratings": ratings}

    mo, mn = old.me(), new.me()
    if mo and mn:
        out["me"] = {"changes": [{"field": k, "from": mo[k], "to": mn[k]}
                                 for k in mn if k in mo and mo[k] != mn[k]]}

    out["counts"] = {k: len(out[k]) for k in ("transfers", "joined", "left", "regens", "managers")}
    out["empty"] = not any(out["counts"].values()) and not (out["me"] and out["me"]["changes"]) \
        and not (out["myClub"] and (out["myClub"]["ratings"] or out["myClub"]["in"] or out["myClub"]["out"]))
    return out
