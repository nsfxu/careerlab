"""E11: swap managers between Cruzeiro (block 120) and Arsenal (block 0).

The displayed manager lives in a per-club table (0x258-byte records, +0 club index,
+4 coach ID, +8 name). Swap the records minus the index field, and swap block+0x144 too.
"""
import sys, struct
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
BASE, S = 0x133A30, 0x258
c = Career.load(SAVE)
before = validate.check(c)
def rec(k): return BASE + k * S
for k in (0, 120):
    assert struct.unpack_from("<I", c.d, rec(k))[0] == k
a, b = bytes(c.d[rec(0) + 4:rec(0) + S]), bytes(c.d[rec(120) + 4:rec(120) + S])
c.d[rec(0) + 4:rec(0) + S], c.d[rec(120) + 4:rec(120) + S] = b, a
for k, other in ((0, 120), (120, 0)):
    pass
f0, f120 = c.club(0).field_144, c.club(120).field_144
struct.pack_into("<I", c.d, c.club(0).offset + 0x144, f120)
struct.pack_into("<I", c.d, c.club(120).offset + 0x144, f0)
print("Arsenal now", c.d[rec(0) + 8:rec(0) + 30].split(b"\0")[0], "Cruzeiro now", c.d[rec(120) + 8:rec(120) + 30].split(b"\0")[0])
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E11-manager-swap"))
