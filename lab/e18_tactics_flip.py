"""E18: flip preset-0 tactical choices in Cruzeiro's manager record.

attacking_style (+0x40+0x63) 1 -> 0, pressuring (+0x40+0x69) 0 -> 1; on top of E17.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.managers import Managers
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
c = Career.load(SAVE)
before = validate.check(c)
o = Managers(c).base + 120 * 0x258 + 0x40
print("attacking_style", c.d[o + 0x63], "pressuring", c.d[o + 0x69])
c.d[o + 0x63], c.d[o + 0x69] = 0, 1
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E18-tactics-flip"))
