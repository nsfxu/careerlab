"""E06: new players with their attribute block copied from a career the game created later.

E05 showed the record's first 32 bytes carry position, ratings, style, nationality and
age. ML00000000 was created in August with the database of that time, so the game itself
wrote correct blocks for players this BAL career never had. Build each new record from a
Cruzeiro teammate in THIS career (competitions, club, contract) + the donor's block.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.registry import Registry, REC
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
BASE = r"E:\FL2026\_archive\write-backups\BL00000000\20261011-152821-E03-resolve"
DONOR = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\ML00000000"
c = Career.load(BASE); c.path = SAVE
before = validate.check(c)
reg, donor = Registry(c), Registry(Career.load(DONOR))
dindex = {donor.pid(i): i for i in range(donor.count)}
mate = c.handle_of(111809) & 0xFFFF                 # Fabricio Bruno's record as the club template
hs = {}
for pid in (169267, 169271, 173759):
    h = reg.append(mate, pid, tag=0xE5F2)
    i = h & 0xFFFF
    reg.blob[i * REC:i * REC + 32] = donor.record(dindex[pid])[:32]
    hs[pid] = h
reg.commit()
for out in (163026, 153346, 120102):
    c.release(120, out)
for k, (pid, h) in enumerate(hs.items()):
    c.add(120, pid, shirt=31 + k, handle=h)
print({p: f"{h:08X}" for p, h in hs.items()})
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E06-donor-block"))
