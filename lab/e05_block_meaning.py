"""E05: what does the record's 32-byte block control?

Two unknown players with very different profiles get records cloned from the SAME template
(Edoardo Caporello, the last pool record): Gustavo Zago (goalkeeper) and Hazem Mastouri (Tunisian striker).
Rhuan Gabriel stays from E04 for reference.
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.registry import Registry
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
BASE = r"E:\FL2026\_archive\write-backups\BL00000000\20261011-152821-E03-resolve"
c = Career.load(BASE); c.path = SAVE
before = validate.check(c)
reg = Registry(c)
T = reg.count - 1
hs = {pid: reg.append(T, pid, tag=0xE5F2) for pid in (169267, 169271, 173759)}
reg.commit()
for out in (163026, 153346, 120102):            # Jonathan Jesus, Otavio Costa, Sinisterra
    c.release(120, out)
for k, (pid, h) in enumerate(hs.items()):
    c.add(120, pid, shirt=31 + k, handle=h)
print({p: f"{h:08X}" for p, h in hs.items()})
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E05-block-meaning"))
