"""E15: is the team's formation the preset inside its club squad block?

Copy Crystal Palace's (block 7, 3 CB + wing-backs) two presets +0x314..+0x454 into
Cruzeiro's block (120) and read Cruzeiro's game plan.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
LO, HI = 0x314, 0x454
c = Career.load(SAVE)
before = validate.check(c)
src, dst = c.club(7).offset, c.club(120).offset
c.d[dst + LO:dst + HI] = bytes(c.d[src + LO:src + HI])
c.dirty()
print("Cruzeiro preset0 now", list(c.d[dst + LO:dst + LO + 11]))
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E15-club-formation"))
