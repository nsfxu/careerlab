"""E01: can a player the career has never known be added, given a fresh handle?

Releases three fringe Cruzeiro players and adds three DB players unknown to the career,
each with a handle from a different namespace and an index above anything allocated.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
CRUZEIRO = 120
RELEASE = [163026, 102232, 151850]           # Jonathan Jesus, Lucas Villalba, Joao Marcelo
ADD = [(169267, 0xE5F27001, 31),             # Rhuan Gabriel   secondary tag
       (169270, 0x00007002, 32),             # Nicolas Pontes  tag 0
       (169271, 0xCC217003, 33)]             # Gustavo Zago    primary tag

c = Career.load(SAVE)
before = validate.check(c)
for pid, *_ in ADD:
    assert c.handle_of(pid) is None, f"{pid} is already known"
variants = [int(a[1:]) for a in sys.argv if a.startswith("v")] or range(len(ADD))
for i in variants:
    c.release(CRUZEIRO, RELEASE[i])
for i in variants:
    pid, h, shirt = ADD[i]
    c.add(CRUZEIRO, pid, shirt=shirt, handle=h)
new = validate.new_problems(before, validate.check(c))
print("new problems:", new or "none")
cl = c.club(CRUZEIRO)
print("Cruzeiro now", len(cl.members), [f"{h:08X}:{p}" for h, p in cl.members[-4:]])
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E01-variants-" + "".join(map(str, variants))))
