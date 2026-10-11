"""E10: edit the created character through his own save record (CT layout)."""
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26 import created as C, validate, safewrite

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
c = Career.load(SAVE)
before = validate.check(c)
b = C.locate(c)
for f, v in (("speed", 99), ("finishing", 95), ("double_touch", 1)):
    print(f, C.get(c, b, f), "->", v)
    C.set(c, b, f, v)
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E10-created-char"))
