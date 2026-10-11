"""E03: what makes a handle resolve to a real player?

A  F. Sahnoune (55252) moved in with the tag-0 handle the GAME allocated for him
   (he appears exactly once in the save, only in his club block) -- control.
B  Rhuan Gabriel (unknown) with tag 0 and a free index in the game's tag-0 window.
C  Nicolas Pontes (unknown) with the primary tag and a free index in the primary range.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
import numpy as np
from fl26.career import Career
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
c = Career.load(SAVE)
a = c.u32()
lows = {h & 0xFFFF for p, hs in c.index().items() for h in hs}
lows |= {h for cl in c.clubs() for h, _ in cl.members if h >> 16 == 0}
def free_in(lo, hi):
    for i in range(lo, hi):
        if i not in lows and not np.isin(a, [i, (c.primary_tag() << 16) | i]).any():
            return i
    raise SystemExit(f"no free index in {lo:#x}..{hi:#x}")
hB = free_in(0x49EB, 0x4A3F)                       # tag 0 window
hC = (c.primary_tag() << 16) | free_in(0x0100, 0x49EA)
print(f"B handle {hB:08X}   C handle {hC:08X}")

before = validate.check(c)
src = c.club_of(55252)
print("Sahnoune is in block", src)
c.release(src[0], 55252)
for pid in (163026, 153346, 120102):               # Jonathan Jesus, Otavio Costa, Sinisterra
    c.release(120, pid)
c.add(120, 55252, shirt=31, handle=0x000049F3)
c.add(120, 169267, shirt=32, handle=hB)
c.add(120, 169270, shirt=33, handle=hC)
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
print("Cruzeiro", len(c.club(120).members))
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E03-resolve"))
