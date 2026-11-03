"""Offline regression tests against archived saves (no game needed).

Run:  python -m pytest -q   (from CareerLab/engine)
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fl26 import attributes as A, created, validate
from fl26.career import Career
from fl26.crypto import Save
from fl26.managers import Managers
from fl26.registry import Registry

TESTDATA = Path(__file__).resolve().parents[2] / "testdata"          # not in git (game saves)
CLEAN_BL0 = TESTDATA / "clean-BL00000000"         # test career before E03 (was _archive/write-backups)
DAMAGED_BL0 = TESTDATA / "damaged-BL00000000"     # 384 duplicates from the old app's August sync
USER_BL1 = TESTDATA / "user-BL00000001"           # the user's career, parked copy (read only)

needs = pytest.mark.skipif(not CLEAN_BL0.exists(), reason="archived saves not present")


@pytest.fixture(scope="module")
def bl0():
    return Career.load(CLEAN_BL0)


@needs
def test_crypto_roundtrip_is_byte_identical():
    raw = CLEAN_BL0.read_bytes()
    assert Save.decrypt(raw).encrypt() == raw


@needs
def test_namespaces_and_clubs(bl0):
    assert bl0.primary_tag() == 0xCC21
    assert len(bl0.clubs()) == 730
    assert all(c.consistent for c in bl0.clubs())


@needs
def test_validator_calibration(bl0):
    assert not [p for p in validate.check(bl0) if p.level == "ERROR"]
    damaged = validate.check(Career.load(DAMAGED_BL0))
    assert sum(p.code == "duplicate-in-squad" for p in damaged) == 384


@needs
def test_registry_agrees_with_every_pair(bl0):
    reg = Registry(bl0)
    assert reg.count == 27423
    for pid, hs in bl0.index().items():
        for h in hs:
            if h >> 16 in bl0.namespaces():
                assert reg.pid(h & 0xFFFF) == pid


@needs
def test_registry_repack_roundtrip():
    c = Career.load(CLEAN_BL0)
    reg = Registry(c)
    blob = bytes(reg.blob)
    reg.commit()
    again = Registry(c)
    assert bytes(again.blob) == blob and again.count == reg.count


@needs
def test_attribute_decode_matches_screen(bl0):
    # Leo Aragao (161249) as read off his in-game pages before any edit
    reg = Registry(bl0)
    rec = reg.record(reg.index_of(161249))
    want = dict(offensive_awareness=58, ball_control=61, dribbling=56, kicking_power=83,
                gk_awareness=87, gk_catching=84, gk_clearing=84, gk_reflexes=85, gk_reach=90,
                age=28)
    assert {k: A.get(rec, k) for k in want} == want


@needs
def test_attribute_set_roundtrip(bl0):
    rec = bytearray(Registry(bl0).record(1))
    A.set(rec, "speed", 99)
    assert A.get(rec, "speed") == 99
    with pytest.raises(ValueError):
        A.set(rec, "speed", 104)


@needs
def test_created_character_record(bl0):
    base = created.locate(bl0)
    assert created.name(bl0, base) == "Giu"
    assert created.get(bl0, base, "speed") == 93


@needs
def test_manager_table_both_careers(bl0):
    assert Managers(bl0).get(120) == (6, "Leonardo Jardim")
    if USER_BL1.exists():
        assert Managers(Career.load(USER_BL1)).get(0) == (102109, "Mikel Arteta")


def test_no_field_name_collisions():
    # a duplicate key silently overwrote the Heading ability twice; keep it impossible
    from fl26 import created as C
    assert len(A.ABILITIES) == 25 and A.FIELDS["heading"] == (50, 6, 40)
    assert C.FIELDS["heading"][2] == 7 and "heading_skill" in C.FIELDS


@needs
def test_profile_rebuild_matches_career(bl0):
    import json
    from fl26 import profiles
    reg = Registry(bl0)
    rec = reg.record(reg.index_of(151850))          # Joao Marcelo
    p = {"main_position": 1, "cb": 2, "header": A.get(rec, "heading"), "heading": 1,
         "fighting_spirit": 1, "age": 26}
    built = profiles.block_from_efdb(p, rec, gap=4)
    assert A.get(built, "registered_position") == 1 and A.get(built, "pos_cb") == 2
    assert A.get(built, "heading_skill") == 1 and A.get(built, "fighting_spirit") == 1
    assert A.get(built, "age") == 30


def test_style_never_inherited_from_template():
    # a striker once got his goalkeeper teammate's style: unknown styles map to "none"
    assert A.style_from_efootballdb(22, is_gk=False) == 4
    assert A.style_from_efootballdb(99, is_gk=False) == 0
    assert A.style_from_efootballdb(0, is_gk=True) == A.STYLE_GK
    assert A.style_from_efootballdb(0, is_gk=False) == 12


def test_league_moves_leave_before_they_arrive():
    from fl26.session import Session
    ops = [{"op": "release", "pid": 1, "block": 0},
           {"op": "move", "pid": 2, "from": 0, "to": 1},
           {"op": "move", "pid": 3, "from": 1, "to": 0},
           {"op": "add", "pid": 4, "block": 1}]
    kinds = [(o["op"], o["pid"]) for o in Session._expand_moves(ops)]
    assert kinds == [("release", 1), ("_out", 2), ("_out", 3), ("_in", 2), ("_in", 3), ("add", 4)]
    # a single move, or a run that moves one player twice, stays as written
    assert [o["op"] for o in Session._expand_moves(ops[1:2])] == ["move"]
    twice = [{"op": "move", "pid": 2, "from": 0, "to": 1}, {"op": "move", "pid": 2, "from": 1, "to": 2}]
    assert [o["op"] for o in Session._expand_moves(twice)] == ["move", "move"]


def test_config_prefers_newest_dump_copy(tmp_path):
    from fl26 import config
    for n in ("player.raw", "player.copy1.raw", "player.copy2.raw", "team.raw"):
        (tmp_path / n).write_bytes(b"x")
    assert config.table_file("player", tmp_path).name == "player.copy2.raw"
    assert config.table_file("team", tmp_path).name == "team.raw"
    assert not config.dump_ok(tmp_path)               # playerassignment/appearance missing
    assert config.asset("DBDump.lua").exists()


def test_backup_description():
    from fl26.session import Session

    class S(Session):
        def __init__(self):
            pass

        def club_name(self, k):
            return f"Club {k}"

    s = S()
    d = s.describe([{"op": "release", "block": 1, "source": "Club 1 sync", "label": "Release A"},
                    {"op": "move", "from": 1, "to": 2, "source": "Club 1 sync"},
                    {"op": "move", "from": 2, "to": 1, "source": "Club 1 sync"}])
    assert d["title"] == "Club 1 sync" and d["clubs"] == ["Club 1", "Club 2"]
    assert d["summary"] == "2 moves · 1 release" and d["edits"][0] == "Release A"
    assert S().describe([{"op": "attr", "pid": 5, "label": "X: Speed 70 → 80"}])["title"] == "X: Speed 70 → 80"


def test_same_person_across_ids():
    from fl26.session import same_person
    assert same_person("Johan Manzambi", "Johan Manzambi")
    assert same_person("Fabrício Bruno", "Fabricio Bruno")
    assert same_person("A. Harriman-Annous", "Ayden Harriman-Annous")
    assert not same_person("Lucas Silva", "Luan Silva")       # same initial, both full: different men
    assert not same_person("Matheus Pereira", "Matheus Henrique")


def test_pesmaster_parse_squad():
    from fl26.pesmaster import parse_squad
    page = ('<h2>Cruzeiro EC eFootball Players</h2>'
            '<a href="/cassio/efootball-2022/player/36943/">'
            '<a href="/cassio/efootball-2022/player/36943/">'          # cards link twice
            '<a href="/joao-marcelo/efootball-2022/player/151850/">'
            '<a href="/batatinha-delfim/efootball-2022/player/8563654/">'   # invented
            '<h2>Cruzeiro EC eFootball Lineup</h2>'
            '<a href="/legend/efootball-2022/player/7511/">')            # legends: not squad
    assert parse_squad(page) == [(36943, "Cassio"), (151850, "Joao Marcelo")]


def test_staging_one_value_replaces_the_last():
    from fl26.session import Session
    s = Session.__new__(Session)
    s.staged = []
    s._check = lambda op: None
    for v in (33, 32, 27):
        s.stage({"op": "attr", "pid": 1, "field": "age", "value": v})
    assert s.staged == [{"op": "attr", "pid": 1, "field": "age", "value": 27}]
    s.stage({"op": "attr", "pid": 1, "field": "speed", "value": 90})
    s.stage({"op": "attr", "pid": 1, "field": "age", "revert": True})
    assert [o["field"] for o in s.staged] == ["speed"]
    s.stage({"op": "move", "pid": 2, "from": 1, "to": 3})
    s.stage({"op": "move", "pid": 2, "from": 3, "to": 4})              # moves are not merged
    assert len(s.staged) == 3


def test_image_names_match_game_files():
    from fl26.images import KINDS
    assert KINDS["player"][1](151850) == "151850.dds"
    assert KINDS["flag"][1](274) == "e_000274_r.png"
    assert KINDS["coach"][1](100110) == "coach_100110.png"
    assert KINDS["league"][1](21)[0] == "emb_0021_l.png"


def test_match_competition_prefers_the_league_over_a_cup():
    from fl26.database import match_competition
    league = set(range(1, 21))
    comps = {9: set(range(1, 21)) - {20} | {99}, 15: set(range(1, 45))}   # 15 = a cup with everyone
    assert match_competition(league, comps) == 9
    assert match_competition({500, 501}, comps) is None
    assert match_competition(league, {120: league, 119: league}) == 119     # league before its cup


@pytest.fixture(scope="module")
def nat_session():
    from fl26.database import Database
    from fl26.session import Session
    try:
        db = Database(TESTDATA / "dbdump", None)
    except FileNotFoundError:
        pytest.skip("no FL26 database dump")
    return Session(CLEAN_BL0, db)


@needs
def test_national_teams_named_by_nationality(nat_session):
    s = nat_session
    teams = {t["name"]: t for t in s.national_teams()}
    assert len(teams) > 100 and "Brazil" in teams and "Senegal" in teams
    br = teams["Brazil"]
    assert br["nationality"] == 146 and br["size"] == 23
    assert s._is_club(s.my_block())                          # his club, never his country
    assert not any(c["national"] for c in s.clubs() if c["name"] == "Cruzeiro EC")


@needs
def test_callup_rules(nat_session):
    from fl26.session import EditError
    s = nat_session
    br = next(t for t in s.national_teams() if t["name"] == "Brazil")
    k = br["block"]
    outsider = next(p for p in s.c.club(k).pids if p < 0x80000000)
    cand = s.callup_candidates(k)["players"][0]["pid"]
    with pytest.raises(EditError):                           # squad of 23 is full
        s._check({"op": "callup", "block": k, "pid": cand})
    foreign = next(p for p in s.rec_of if p < 0x80000000 and s.nationality(p) not in (146, None))
    with pytest.raises(EditError):
        s._check({"op": "callup", "block": k, "pid": foreign})
    s.staged = [{"op": "drop", "block": k, "pid": outsider}]
    s._check({"op": "callup", "block": k, "pid": cand})      # room after a drop
    s.staged = []


@needs
def test_callup_of_a_free_agent_applies(nat_session):
    """A clubless player has no squad entry, so the call-up takes his handle from the record."""
    s = nat_session
    br = next(t for t in s.national_teams() if t["name"] == "Brazil")
    k = br["block"]
    here = set(s.c.club(k).pids)
    free = next(r["pid"] for r in s.callup_candidates(k)["players"] if not r["club"] and r["pid"] not in here)
    out = next(p for p in s.c.club(k).pids if p < 0x80000000)
    s.staged = [{"op": "drop", "block": k, "pid": out}, {"op": "callup", "block": k, "pid": free}]
    c = Career.load(s.path)
    s._apply_ops(c, Registry(c), Managers(c))
    assert free in c.club(k).pids and out not in c.club(k).pids
    s.staged = []


def test_database_ages_are_plausible():
    """Database age = low 6 bits of player byte 0x33 + 16 (checked against efootballdb)."""
    from fl26.database import Database
    try:
        db = Database(TESTDATA / "dbdump", None)
    except FileNotFoundError:
        pytest.skip("no FL26 database dump")
    ages = list(db.player_age.values())
    assert sum(15 <= a <= 45 for a in ages) > 0.97 * len(ages)
    assert 22 <= sorted(ages)[len(ages) // 2] <= 30


# ------------------------------------------------------------------ FL27 and the upgrade

FL27_BL0 = TESTDATA / "fl27-BL00000000"           # an FL27-made career (the upgrade's wrapper)
FL27_KEY = Path(os.environ.get("LOCALAPPDATA", ".")) / "CareerLab" / "FL_key.bin"   # never in the repo
needs27 = pytest.mark.skipif(not (FL27_BL0.exists() and FL27_KEY.exists() and USER_BL1.exists()),
                             reason="FL27 save or key not present")


@pytest.fixture(scope="module")
def fl27_key():
    from fl26 import crypto
    key = FL27_KEY.read_bytes()
    crypto.add_key(key)
    return key


@needs
def test_peek_reads_the_description_without_the_payload():
    info = Save.peek(USER_BL1)
    assert info["kind"] == "BL" and info["game"] == "SP Football Life 2026"
    assert info["title"].endswith("02") and len(info["lines"]) == 3
    from fl26.crypto import stamp_version
    assert info["stamp"] == (260203, 200, 200) and stamp_version(info["stamp"]) == "26.2.3"


@needs27
def test_fl27_save_opens_with_its_key_and_round_trips(fl27_key):
    from fl26.crypto import MASTER_KEY_PES21, UnknownKey
    raw = FL27_BL0.read_bytes()
    with pytest.raises(UnknownKey):
        Save.decrypt(raw, MASTER_KEY_PES21)
    s = Save.decrypt(raw)
    assert s.master == fl27_key and s.game == "SP Football Life 2027"
    assert s.encrypt() == raw


@needs27
def test_upgrade_wraps_fl26_career_in_fl27_envelope(fl27_key, tmp_path):
    import shutil
    from fl26 import migrate
    shutil.copy(FL27_BL0, tmp_path / "BL00000000")
    shutil.copy(USER_BL1, tmp_path / "src")
    dest = migrate.upgrade(tmp_path / "src", tmp_path)
    assert dest.name == "BL00000001"                       # first free slot, nothing overwritten
    src, wrap, new = Save.load(tmp_path / "src"), Save.load(FL27_BL0), Save.load(dest)
    assert new.master == fl27_key and new.game == wrap.game and new.enc_header == wrap.enc_header
    assert new.data[12:24] == wrap.data[12:24] != src.data[12:24]    # FL27's version stamp
    assert new.data[:12] + new.data[24:] == src.data[:12] + src.data[24:]
    assert new.logo == src.logo and Save.peek(dest)["lines"] == Save.peek(tmp_path / "src")["lines"]
    assert Career(new, dest).clubs()                        # the engine reads it as a career


def test_retitle_follows_the_slot():
    from fl26.migrate import retitle
    desc = b"Rumo ao Estrelato 02".ljust(128, b"\0") + b"Giu\nClub\n1/1/2030".ljust(256, b"\0")
    out = retitle(desc, Path("BL00000004"))
    assert out[:128].rstrip(b"\0") == b"Rumo ao Estrelato 05" and out[128:] == desc[128:]


def test_upgrade_refuses_without_an_fl27_career(tmp_path):
    from fl26 import migrate
    with pytest.raises(ValueError):
        migrate.wrapper(tmp_path)


def test_legacy_config_moves_into_the_fl26_block(tmp_path, monkeypatch):
    import json
    from fl26 import config
    monkeypatch.setattr(config, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(config, "_game", None)
    (tmp_path / "config.json").write_text(json.dumps({"gameDir": "E:\\FL2026", "lang": "pt"}))
    cfg = config.load()
    assert cfg["games"]["fl26"] == {"gameDir": "E:\\FL2026"} and "gameDir" not in cfg
    both = lambda g=None: Path("X:/game")
    monkeypatch.setattr(config, "detect_game_dir", both)
    assert config.game().id == "fl26"                        # set up before FL27: stays on FL26
    monkeypatch.setattr(config, "_game", None)
    monkeypatch.setattr(config, "detect_game_dir", lambda g=None: Path("X:/g") if g.id == "fl27" else None)
    assert config.game().id == "fl27"                        # ...until FL26 is uninstalled
