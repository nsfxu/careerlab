"""E08: is a club really capped at the squad length it started the career with?

Cruzeiro started at 28 and holds 27 after the game's own save. Add five players who
already have registry records (no new records involved) to reach 32.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.registry import Registry
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
c = Career.load(SAVE)
before = validate.check(c)
reg = Registry(c)
recs = {reg.pid(i): i for i in range(reg.count)}
taken = {p for cl in c.clubs() for p in cl.pids}
# Cruzeiro players at career creation that no squad holds any more, then any free records
wanted = [p for p in (128067, 160104, 110068) if p in recs and p not in taken]
wanted += [reg.pid(i) for i in range(0x0F10, 0x0F60) if reg.pid(i) not in taken and reg.pid(i) not in wanted][:5 - len(wanted)]
for k, pid in enumerate(wanted):
    c.add(120, pid, shirt=40 + k, handle=reg.handle(recs[pid]))
print("added", wanted, "-> Cruzeiro", len(c.club(120).members))
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E08-capacity"))
