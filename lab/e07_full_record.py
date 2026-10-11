"""E07: new players built from the donor's whole record, with the club context and age fixed.

E06: the 32-byte block gives position/ratings but nationality lives at +0x90 and age is
stored as an age (byte 0x12 bits 2-7), frozen at the donor's season (2025 vs this 2030).
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.registry import Registry, REC
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
BASE = r"E:\FL2026\_archive\write-backups\BL00000000\20261011-152821-E03-resolve"
DONOR = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\ML00000000"
YEARS = 2030 - 2025

c = Career.load(BASE); c.path = SAVE
before = validate.check(c)
reg, donor = Registry(c), Registry(Career.load(DONOR))
dindex = {donor.pid(i): i for i in range(donor.count)}
mate = reg.record(c.handle_of(111809) & 0xFFFF)      # Fabricio Bruno: club context
hs = {}
for pid in (169267, 169271, 173759):
    rec = bytearray(donor.record(dindex[pid]))
    rec[0x28:0x74] = mate[0x28:0x74]                   # competitions, prior-club, counters
    rec[0x7C:0x90] = mate[0x7C:0x90]                   # loan/club/contract/joined
    age = (rec[0x12] >> 2) + YEARS
    rec[0x12] = (rec[0x12] & 3) | (min(age, 63) << 2)
    h = reg.append(0, pid, tag=0xE5F2)
    i = h & 0xFFFF
    rec[0x20:0x24] = h.to_bytes(4, "little"); rec[0x24:0x28] = pid.to_bytes(4, "little")
    reg.blob[i * REC:(i + 1) * REC] = rec
    hs[pid] = h
reg.commit()
for out in (163026, 153346, 120102):
    c.release(120, out)
for k, (pid, h) in enumerate(hs.items()):
    c.add(120, pid, shirt=31 + k, handle=h)
print({p: f"{h:08X}" for p, h in hs.items()})
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E07-full-record"))
