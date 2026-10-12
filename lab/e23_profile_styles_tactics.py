"""E23: created-character profile, registry playing-style names, copy tactics.

One apply, one game session:
  * Giu: height 181, weight 79, left foot, registered CF with CF=A, Goal Poacher (CT list 1),
    weak foot 4/4, form 5, injury resistance 1.
  * 22 Cruzeiro players get registry playing_style 0..21, so the Base de dados cards show
    every style's Portuguese name for the registry numbering (it differs from the CT list).
  * Cruzeiro's manager keeps his name but gets the tactics of a club whose preset 0 has a
    different number of centre-backs (formation must change on Plano de jogo).
Prints the slot -> style table needed to read the screenshots.
"""
import json
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career, CREATED_ID_MIN
from fl26.registry import Registry, REC
from fl26.managers import Managers
from fl26 import attributes as A, created, validate, safewrite
from fl26.database import Database

SAVE = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\BL00000000"
POS = "GK CB LB RB DMF CMF LMF RMF AMF LWF RWF SS CF".split()
CRU = 120

c = Career.load(SAVE)
before = validate.check(c)
reg, m = Registry(c), Managers(c)
db = Database(None, r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\EDIT00000000")
rec_of = {reg.pid(i): i for i in range(reg.count)}

# --- Giu
b = created.locate(c)
for f, v in (("height_cm", 181), ("weight_kg", 79), ("stronger_foot", 1), ("registred_position", 12),
             ("cf_center_forward", 2), ("playing_style", 1), ("weak_foot_usage", 3),
             ("weak_foot_accuracy", 3), ("form", 4), ("injury_resistance", 0)):
    print("Giu", f, created.get(c, b, f), "->", v)
    created.set(c, b, f, v)

# --- registry styles 0..21 on Cruzeiro players (squad order)
table = []
cl = c.club(CRU)
for slot, (pid, shirt) in enumerate(zip(cl.pids, cl.shirts)):
    if pid >= CREATED_ID_MIN or pid not in rec_of or len(table) == 22:
        continue
    i = rec_of[pid]
    rec = bytearray(reg.record(i))
    style = len(table)
    table.append({"slot": slot, "shirt": shirt, "name": db.player_name(pid), "style": style,
                  "was": A.get(rec, "playing_style")})
    A.set(rec, "playing_style", style)
    reg.blob[i * REC:(i + 1) * REC] = rec
reg.commit()

# --- copy tactics from a club with a different back line
show = lambda k: [POS[x] if x < 13 else "?" for x in c.d[m.base + k * 0x258 + 0x40:m.base + k * 0x258 + 0x40 + 11]]
mine = show(CRU)
donor = next(k for k in range(len(c.clubs())) if k != CRU and m.get(k)[1]
             and show(k).count("CB") != mine.count("CB") and "?" not in show(k))
print("Cruzeiro preset 0:", mine, "| donor", donor, m.get(donor), show(donor))
m.copy_tactics(CRU, donor)
print("after:", show(CRU), "manager still", m.get(CRU))

print(json.dumps(table, ensure_ascii=False, indent=0))
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E23-profile-styles-tactics"))
