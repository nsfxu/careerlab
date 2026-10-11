"""E16: swap manager records Cruzeiro (120) <-> Crystal Palace (7, Glasner, 3 CB).

E15 reverted first: the club-block preset copy changed nothing on screen. If Cruzeiro's
game plan becomes a back three, the formation travels with the manager record.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.managers import Managers
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
POS = "GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF".split()
c = Career.load(SAVE)
before = validate.check(c)
m = Managers(c)
show = lambda k: [POS[x] for x in c.d[m.base + k * 0x258 + 0x40:m.base + k * 0x258 + 0x40 + 11]]
print("before", m.get(120), show(120), "|", m.get(7), show(7))
m.swap(120, 7)
print("after ", m.get(120), show(120))
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E16-manager-formation"))
