"""E19: new players built from efootballdb, on a fresh golden copy.

(a) Rhuan Gabriel (169267): in FL26's database, no career record -> registry record only.
(b) Kauã Moraes (176967): NOT in FL26's database -> option-file record (cloned from a
    similar database player: data + face) + registry record.
Both added to Cruzeiro.
"""
import shutil
import sys
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.registry import Registry
from fl26.editfile import EditFile, load_db_tables
from fl26 import efdb, profiles, validate, safewrite

SAVE_DIR = r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save"
GOLDEN = r"E:\FL2026\CareerLab\testdata\BL00000000.golden"
EDIT_GOLDEN = r"E:\FL2026\CareerLab\testdata\EDIT00000000.golden"
DUMP = r"E:\FL2026\SiderAddons\dbdump"
FACE_DONOR = 169270        # Nicolas Pontes: young Brazilian in FL26's DB, used as data/face template

sq = {pid: p for pid, _, _, p, _ in efdb.squad(274)}
c = Career.load(GOLDEN); c.path = SAVE_DIR + r"\BL00000000"
before = validate.check(c)
reg = Registry(c)
rec_of = {reg.pid(i): i for i in range(reg.count)}
gap = profiles.season_gap(reg, rec_of, sq.values())
handles = {}
for pid in (169267, 176967):
    assert pid not in rec_of
    handles[pid] = profiles.build_new_player(c, reg, pid, 120, sq[pid], gap)
reg.commit()
for pid, h in handles.items():
    c.add(120, pid, handle=h)
print("handles", {p: f"{h:08X}" for p, h in handles.items()}, "gap", gap)
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")

e = EditFile(EDIT_GOLDEN); e.path = __import__("pathlib").Path(SAVE_DIR + r"\EDIT00000000")
players, faces = load_db_tables(DUMP)
p = sq[176967]
k = e.add_player(176967, p["player_name"], (p.get("shirt_name") or p["player_name"]).upper(),
                 players[FACE_DONOR], faces[FACE_DONOR], p.get("height"), p.get("weight"),
                 (p.get("nationality_a") or {}).get("country_id"))
print("option-file record", k, "for", p["player_name"])
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E19-new-players"))
    print("backup:", safewrite.write_file(e, "E19-new-player-edit"))
