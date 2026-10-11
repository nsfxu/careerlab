"""E12: give Cruzeiro a manager from the option file's coach list (Tite, 100093).

Writes coach ID + name into the club's manager record and block+0x144; the rest of the
record (tactics, as far as known) stays Arteta's from E11.
"""
import sys, struct
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
BASE, S, K = 0x133A30, 0x258, 120
c = Career.load(SAVE)
before = validate.check(c)
o = BASE + K * S
assert struct.unpack_from("<I", c.d, o)[0] == K
name = "Tite".encode()
struct.pack_into("<I", c.d, o + 4, 100093)
c.d[o + 8:o + 8 + 0x36] = name + bytes(0x36 - len(name))
struct.pack_into("<I", c.d, c.club(K).offset + 0x144, 100093)
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E12-set-manager-Tite"))
