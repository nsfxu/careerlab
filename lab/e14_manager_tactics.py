"""E14: does the manager record carry the team's tactics?

Swap full manager records Cruzeiro (120, a 4-3-3 side) <-> Man United (13, Amorim 3-4-3)
and read Cruzeiro's game plan in game.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.managers import Managers
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
c = Career.load(SAVE)
before = validate.check(c)
m = Managers(c)
print("before:", m.get(120), m.get(13))
m.swap(120, 13)
print("after: ", m.get(120), m.get(13))
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E14-manager-tactics"))
