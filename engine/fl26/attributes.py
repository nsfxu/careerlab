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

# Position ratings (0 = cannot play, 1 = can, 2 = natural), solved 2026-10-11 against
# efootballdb.com for 285 players (96-99% agreement). Five of them live in the 2 spare bits
# at the top of each ability word.
FIELDS.update({
    "pos_cf": (30, 2, 0), "pos_ss": (62, 2, 0), "pos_lwf": (94, 2, 0),
    "pos_rwf": (126, 2, 0), "pos_amf": (158, 2, 0), "pos_dmf": (181, 2, 0),
    "pos_cmf": (183, 2, 0), "pos_lmf": (185, 2, 0), "pos_rmf": (187, 2, 0),
    "pos_cb": (189, 2, 0), "pos_lb": (192, 2, 0), "pos_rb": (194, 2, 0),
    "pos_gk": (196, 2, 0),
    # FL26 (PES 2021) style numbering -- NOT efootballdb's, which was renumbered; see
    # STYLE_FROM_EFOOTBALLDB.
    "playing_style": (166, 5, 0),
})

# Skills: one bit each, solved against efootballdb for 285 players (96-100% agreement).
SKILLS = {
    "scissors_feint": 191, "flip_flap": 204, "marseille_turn": 205, "sombrero": 206,
    "cut_behind_turn": 207, "scotch_move": 208, "heading": 209, "long_range_drive": 210,
    "knuckle_shot": 211, "acrobatic_finishing": 212, "heel_trick": 213,
    "first_time_shot": 214, "one_touch_pass": 215, "weighted_pass": 216,
    "pinpoint_crossing": 217, "outside_curler": 218, "rabona": 219, "low_lofted_pass": 220,
    "gk_low_punt": 221, "long_throw": 222, "gk_long_throw": 223, "gamesmanship": 224,
    "man_marking": 225, "track_back": 226, "acrobatic_clear": 227, "captaincy": 228,
    "super_sub": 229, "fighting_spirit": 230, "no_look_pass": 231,
    "penalty_specialist": 232, "gk_penalty_saver": 233, "chip_shot_control": 234,
    "step_on_skill_control": 235, "dipping_shots": 236, "rising_shots": 237,
    "gk_high_punt": 238, "interception": 239, "double_touch": 240, "cross_over_turn": 241,
    "long_range_shooting": 242, "through_passing": 243,
}
FIELDS.update({k: (b, 1, 0) for k, b in SKILLS.items()})

# efootballdb playing_style -> FL26 playing_style, majority mapping from the same 285 players.
STYLE_FROM_EFOOTBALLDB = {13: 4, 14: 5, 4: 6, 18: 7, 6: 10, 7: 11, 0: 12, 20: 13, 8: 14,
                          11: 15, 21: 16, 12: 17, 15: 18, 10: 19}

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
