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
