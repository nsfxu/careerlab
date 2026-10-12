"""E24: can a national-team squad be edited, and does the edit survive the next call-up?

National teams are ordinary squad blocks (23 players), but they hold the game's own call-ups,
so database voting can't name them; each block is one nationality (Brazil = 146 -> block 681
in slot 1, which already lists Giu). The edit is squad-only: players stay at their clubs.

  * out: the two best-rated non-Giu players of Brazil's squad
  * in:  Cássio Ramos (GK, 43) and Matheus Pereira (AMF, 34) of Cruzeiro, easy to spot

Then in game: Base de dados > Brazil's squad, and skip to the next international friendly
to see whether the game keeps or re-picks the squad.
"""
import struct
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career, CREATED_ID_MIN
from fl26.registry import Registry
from fl26.managers import Managers
from fl26 import attributes as A, validate, safewrite
from fl26.database import Database

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
BRAZIL = 146
IN = ("Cássio Ramos", "Matheus Pereira")

c = Career.load(SAVE)
before = validate.check(c)
reg, m = Registry(c), Managers(c)
db = Database(None, r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\EDIT00000000")
rec_of = {reg.pid(i): i for i in range(reg.count)}
nat = lambda pid: struct.unpack_from("<H", reg.record(rec_of[pid]), 0x90)[0] if pid in rec_of else None
rating = lambda pid: A.overall_estimate(reg.record(rec_of[pid])) if pid in rec_of else 0
name = lambda pid: db.player_name(pid) or ("Giu" if pid >= CREATED_ID_MIN else f"#{pid}")

# Brazil's block: every member Brazilian, 20+ members, not a club (Cruzeiro is all-Brazilian too)
blocks = [k for k, cl in enumerate(c.clubs()) if len(cl.members) >= 20 and k != 120
          and all(nat(p) == BRAZIL or p >= CREATED_ID_MIN for _, p in cl.members)
          and sum(p in db.player_teams for _, p in cl.members) and k >= 584]
print("Brazilian national blocks:", blocks)
k = blocks[0]
cl = c.club(k)
print(f"block {k}: {len(cl.members)} players, manager {m.get(k)}")
for p, s in zip(cl.pids, cl.shirts):
    print(f"  {s:>2} {name(p):<28} ovr {rating(p)}")

out = sorted((p for p in cl.pids if p < CREATED_ID_MIN), key=rating, reverse=True)[:2]
cru = c.club(120)
inn = [p for p in cru.pids if name(p) in IN]
assert len(inn) == 2, inn
for p in out:
    slot = c.club(k).pids.index(p)
    c.release(k, p)
    try:
        m.slot_removed(k, slot)
    except LookupError:
        pass
for p in inn:
    c.add(k, p)
    try:
        m.slot_added(k, len(c.club(k).members) - 1)
    except LookupError:
        pass
print("out:", [name(p) for p in out], "| in:", [name(p) for p in inn])
print("after:", [name(p) for p in c.club(k).pids])
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E24-brazil-callups"))
