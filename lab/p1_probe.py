"""P1: probe the index->player mapping. 12 orphan handles into Cruzeiro, read names in game."""
import sys, json, random, struct
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
import numpy as np
from fl26.career import Career
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
BASE = r"E:\FL2026\_archive\write-backups\BL00000000\20261011-152821-E03-resolve"   # pre-E03
c = Career.load(BASE)
c.path = SAVE
a = c.u32()
used = {h & 0xFFFF for p, hs in c.index().items() for h in hs}
used |= {h for cl in c.clubs() for h, _ in cl.members if h >> 16 == 0}
rng = random.Random(11)
def orphans(lo, hi, n):
    out = []
    while len(out) < n:
        i = rng.randrange(lo, hi)
        if i not in used and i not in out and not np.isin(a, [i, 0xCC210000 | i, 0xE5F20000 | i]).any():
            out.append(i)
    return sorted(out)
probes = ([0xCC210000 | i for i in orphans(0x0100, 0x49EA, 4)]
          + [i for i in orphans(0x49EC, 0x4A3F, 4)]
          + [0xE5F20000 | i for i in orphans(0x4A40, 0x6B12, 4)])
cz = c.club(120)
keep = {0x800000BA, 36943, 111809, 127062, 138525}          # Giu, Cassio, Fabricio, Kaio, Marquinhos
out = [p for p in cz.pids if p not in keep][:12]
before = validate.check(c)
for p in out:
    c.release(120, p)
for k, h in enumerate(probes):
    c.add(120, 900000 + k, shirt=60 + k, handle=h)          # dummy pid: the game ignores it
print("probes:", [f"{h:08X}" for h in probes])
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
json.dump({"probes": probes, "released": out}, open("p1_probe.json", "w"))
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "P1-probe"))
