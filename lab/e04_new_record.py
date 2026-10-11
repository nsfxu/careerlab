"""E04: add a player the career never knew by giving him a registry record.

Rhuan Gabriel (169267) was added to the database after this career was created, so he
has no record and no handle. Append a record cloned from the last pool record, then put
his new handle in Cruzeiro in place of Jonathan Jesus.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.registry import Registry
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
BASE = r"E:\FL2026\_archive\write-backups\BL00000000\20261011-152821-E03-resolve"   # pre-E03 = clean
c = Career.load(BASE); c.path = SAVE
before = validate.check(c)
reg = Registry(c)
template = reg.count - 1
h = reg.append(template, 169267, tag=0xE5F2)
reg.commit()
print(f"Rhuan Gabriel -> record {h & 0xFFFF:#x}, handle {h:08X}, template {template:#x} ({Registry(c).pid(template)})")
c.release(120, 163026)
c.add(120, 169267, shirt=31, handle=h)
r2 = Registry(c)
assert r2.pid(h & 0xFFFF) == 169267 and r2.count == template + 2
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E04-new-record"))
