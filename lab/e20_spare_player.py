"""E20: a player FL26 lacks (Kauã Moraes) via a spare database ID, on a fresh golden copy.

Career: the spare's own registry record becomes Kauã (efootballdb profile), added to
Cruzeiro. Option file: a record for the spare's ID (cloned from his own database entry)
renamed to Kauã Moraes, with the face of a young Brazilian donor. Rhuan Gabriel (tier A)
is added too, as in E19.
"""
import struct
import sys
from pathlib import Path
sys.path.insert(0, r"E:\FL2026\CareerLab\engine")
from fl26.career import Career
from fl26.registry import Registry
from fl26.editfile import EditFile, load_db_tables
from fl26.database import Database
from fl26 import efdb, profiles, validate, safewrite

SAVE_DIR = Path(r"C:\Users\PC-CASA\Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save")
GOLDEN = r"E:\FL2026\CareerLab\testdata\BL00000000.golden"
EDIT_GOLDEN = r"E:\FL2026\CareerLab\testdata\EDIT00000000.golden"
DUMP = r"E:\FL2026\SiderAddons\dbdump"
FACE_DONOR = 169270

sq = {pid: p for pid, _, _, p, _ in efdb.squad(274)}
db = Database(DUMP, EDIT_GOLDEN)
c = Career.load(GOLDEN); c.path = SAVE_DIR / "BL00000000"
e = EditFile(EDIT_GOLDEN); e.path = SAVE_DIR / "EDIT00000000"
before = validate.check(c)
reg = Registry(c)
rec_of = {reg.pid(i): i for i in range(reg.count)}
gap = profiles.season_gap(reg, rec_of, sq.values())

h_rhuan = profiles.build_new_player(c, reg, 169267, 120, sq[169267], gap)
edit_pids = {struct.unpack_from("<I", e.d, 0x7C + k * 0x138)[0] for k in range(e.count)}
spare, si = profiles.pick_spare(c, reg, db, edit_pids)
print("spare:", spare, db.player_name(spare))
h_kaua = profiles.adopt_spare(c, reg, si, 120, sq[176967], gap)
reg.commit()
c.add(120, 169267, handle=h_rhuan)
c.add(120, spare, handle=h_kaua)
print("new problems:", validate.new_problems(before, validate.check(c)) or "none")

players, faces = load_db_tables(DUMP)
p = sq[176967]
e.add_player(spare, p["player_name"], (p.get("shirt_name") or p["player_name"]).upper(),
             players[spare], faces[FACE_DONOR], p.get("height"), p.get("weight"),
             (p.get("nationality_a") or {}).get("country_id"))
if "--apply" in sys.argv:
    print("backup:", safewrite.write(c, "E20-spare-player"))
    print("backup:", safewrite.write_file(e, "E20-spare-player-edit"))
