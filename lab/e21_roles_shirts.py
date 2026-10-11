"""E21: identify the set-piece/captain bytes and confirm shirt numbers.

Manager record roles (option-file game plan offsets + 0x3C), written as squad slots:
  +0x248 Kaio Jorge(14)  +0x249 Marquinhos(13)  +0x24A Neiser(9)
  +0x24B M.Pereira(10)   +0x24C Kaique(12)      +0x24D Keny(15)
  +0x24E Cássio(0)       +0x24F Lucas Silva(18) +0x250 Wanderson(22)
Shirts: Kaio Jorge 19 -> 99, Cássio 1 -> 13.
"""
import struct
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.managers import Managers
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
c = Career.load(SAVE)
before = validate.check(c)
o = Managers(c).base + 120 * 0x258
for off, slot in ((0x248, 14), (0x249, 13), (0x24A, 9), (0x24B, 10), (0x24C, 12),
                  (0x24D, 15), (0x24E, 0), (0x24F, 18), (0x250, 22)):
    c.d[o + off] = slot
cl = c.club(120)
for slot, shirt in ((14, 99), (0, 13)):
    struct.pack_into("<H", c.d, cl.offset + 0x14E + slot * 2, shirt)
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E21-roles-shirts"))
