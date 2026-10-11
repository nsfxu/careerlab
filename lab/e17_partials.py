"""E17: close the Partial gaps in one run, on a fresh copy of the golden save.

Giu: salary, contract year, form arrow.  Cruzeiro (manager record): captain candidate byte
+0x251 -> Giu's squad slot; preset 0 defensive line (+0xCE) 6 -> 1, compactness (+0xCF) 7 -> 10.
"""
import sys, shutil
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.managers import Managers
from fl26 import created as C, validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
GOLDEN = r"E:\FL2026\CareerLab\testdata\BL00000000.golden"
c = Career.load(GOLDEN); c.path = SAVE
before = validate.check(c)
b = C.locate(c)
for f, v in (("salary_euro", 250000), ("year", 2040), ("form_arrow", 4)):
    print(f, C.get(c, b, f), "->", v); C.set(c, b, f, v)
m = Managers(c); o = m.base + 120 * 0x258
giu_slot = c.club(120).pids.index(0x800000BA)
print("Giu slot", giu_slot, "| captain candidate", c.d[o + 0x251], "->", giu_slot)
c.d[o + 0x251] = giu_slot
print("def line", c.d[o + 0xCE], "-> 1 | compactness", c.d[o + 0xCF], "-> 10")
c.d[o + 0xCE], c.d[o + 0xCF] = 1, 10
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E17-partials"))
