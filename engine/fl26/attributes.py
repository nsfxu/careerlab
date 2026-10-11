"""Player attributes inside a registry record (the career's own copy of a player).

Solved 2026-10-11 by reading the ability pages of eight Cruzeiro players in game and
solving for bit fields that reproduce every value: abilities are 6-bit fields holding
(value - 40), packed five per 32-bit little-endian word with two spare bits. Bit offsets
count from bit 0 of record byte 0, least significant bit first.
"""
from __future__ import annotations

# name: (bit offset, width, value added to the raw field)
FIELDS = {
    "offensive_awareness": (0, 6, 40),
    "defensive_awareness": (6, 6, 40),
    "gk_awareness": (12, 6, 40),
    "dribbling": (18, 6, 40),
    "ball_control": (24, 6, 40),
    "finishing": (32, 6, 40),
    "low_pass": (38, 6, 40),
    "lofted_pass": (44, 6, 40),
    "heading": (50, 6, 40),
    "ball_winning": (56, 6, 40),
    "place_kicking": (64, 6, 40),
    "curl": (70, 6, 40),
    "gk_catching": (76, 6, 40),      # 76/82 order from the CT table, confirm with E09
    "gk_clearing": (82, 6, 40),
    "gk_reflexes": (88, 6, 40),
    "gk_reach": (96, 6, 40),
    "speed": (102, 6, 40),
    "physical_contact": (108, 6, 40),
    "balance": (114, 6, 40),
    "kicking_power": (120, 6, 40),
    "acceleration": (128, 6, 40),
    "jump": (134, 6, 40),
    "stamina": (140, 6, 40),
    "age": (146, 6, 0),
    "tight_possession": (152, 6, 40),
    "aggression": (160, 6, 40),
    "registered_position": (171, 4, 0),
    "form": (175, 3, 1),
    "weak_foot_accuracy": (198, 2, 1),
    "weak_foot_usage": (202, 2, 1),
}

ABILITIES = [k for k, (_, w, base) in FIELDS.items() if w == 6 and base == 40]


def get(rec, name):
    off, width, base = FIELDS[name]
    v = int.from_bytes(bytes(rec[off // 8:(off + width + 7) // 8 + 1]), "little")
    return ((v >> (off % 8)) & ((1 << width) - 1)) + base


def set(rec, name, value):
    """Write `value` into a mutable record (bytearray)."""
    off, width, base = FIELDS[name]
    raw = value - base
    if not 0 <= raw < (1 << width):
        raise ValueError(f"{name}={value} outside {base}..{base + (1 << width) - 1}")
    lo, hi = off // 8, (off + width + 7) // 8 + 1
    v = int.from_bytes(bytes(rec[lo:hi]), "little")
    mask = ((1 << width) - 1) << (off % 8)
    v = (v & ~mask) | (raw << (off % 8))
    rec[lo:hi] = v.to_bytes(hi - lo, "little")


def read_all(rec):
    return {k: get(rec, k) for k in FIELDS}
