"""E09: edit attributes through the registry record.

Giu (record 0, the created character): speed 99, finishing 95.
Leo Aragao: distinct GK values to settle which of bits 76/82/88/96 is which.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.registry import Registry, REC
from fl26 import attributes as A, validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
c = Career.load(SAVE)
before = validate.check(c)
reg = Registry(c)
def edit(i, **kw):
    rec = bytearray(reg.record(i))
    print(reg.pid(i), "before", {k: A.get(rec, k) for k in kw})
    for k, v in kw.items():
        A.set(rec, k, v)
    reg.blob[i * REC:(i + 1) * REC] = rec
edit(0, speed=99, finishing=95)
leo = next(i for i in range(reg.count) if reg.pid(i) == 161249)
edit(leo, gk_catching=50, gk_clearing=60, gk_reflexes=70, gk_reach=55)
reg.commit()
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E09-attributes"))
