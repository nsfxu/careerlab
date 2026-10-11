"""E02: an unknown player given a FREE index inside the allocated handle range.

E01 showed an index above the range (0x7001) crashes the career on load. The game's own
in-career handles all sit inside the range, so try a hole left by a removed player.
usage: e02_free_index.py <hex handle> [--apply]
"""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26 import validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
handle = int(sys.argv[1], 16)
c = Career.load(SAVE)
before = validate.check(c)
assert c.handle_of(169267) is None
assert not (c.u32() == handle).any(), "handle already used somewhere"
c.release(120, 163026)                      # Jonathan Jesus out
c.add(120, 169267, shirt=31, handle=handle) # Rhuan Gabriel in
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, f"E02-{handle:08X}"))
