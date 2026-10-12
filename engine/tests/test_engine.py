"""Offline regression tests against archived saves (no game needed).

Run:  python -m pytest -q   (from CareerLab/engine)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fl26 import attributes as A, created, validate
from fl26.career import Career
from fl26.crypto import Save
from fl26.managers import Managers
from fl26.registry import Registry

ARCHIVE = Path(r"E:\FL2026\_archive")
CLEAN_BL0 = ARCHIVE / "write-backups/BL00000000/20261011-152821-E03-resolve"   # pre-E03 clean
DAMAGED_BL0 = ARCHIVE / "old-FLCareerEditor/backups/BL00000000/20261001-124359-damaged-by-the-August-swap-sync----384-d"
USER_BL1 = ARCHIVE / "PARKED-user-career/BL00000001"

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
