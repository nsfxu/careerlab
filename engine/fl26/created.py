"""The created character's own player record, stored in the career save.

The created character (playerID >= 0x100000, e.g. 0x800000BA) is not in the database, so
the save carries his full player record in the game's in-memory layout: playerID at +0x30,
commentary ID at +0x34, name at +0x38. Verified 2026-10-11: every ability on his in-game
pages decodes exactly with the field map below, which is taken from the user's Cheat
Engine table FL_2026.CT (ptrPlayer struct). His registry record 0 is only a mirror -
editing it changes nothing on screen.

Fields: name -> (byte offset, bit start, bit length). Abilities are raw values (40-99).
"""
from __future__ import annotations

import struct

FIELDS = {
    "player_id": (0x030, 0, 32),   # Player ID
    "team": (0x12C, 0, 16),   # Team (?)
    "league": (0x12E, 0, 16),   # League (?)
    "commentary_id": (0x034, 0, 32),   # Commentary ID
    "nationality": (0x144, 0, 16),   # Nationality
    "weight_kg": (0x001, 0, 8),   # Weight (kg)
    "height_cm": (0x000, 0, 8),   # Height (cm)
    "age": (0x01C, 0, 6),   # Age
    "stronger_foot": (0x003, 7, 1),   # Stronger Foot
    "registred_position": (0x007, 4, 4),   # Registred Position
    "cf_center_forward": (0x01F, 1, 2),   # CF - Center Forward
    "ss_second_striker": (0x01F, 3, 2),   # SS - Second Striker
    "lwf_left_wing_forward": (0x01F, 5, 2),   # LWF - Left Wing Forward
    "rwf_right_wing_forward": (0x020, 0, 2),   # RWF - Right Wing Forward
    "amf_attacking_midfielder": (0x020, 2, 2),   # AMF - Attacking Midfielder
    "lmf_left_midfielder": (0x021, 0, 2),   # LMF - Left Midfielder
    "rmf_right_midfielder": (0x021, 2, 2),   # RMF - Right Midfielder
    "cmf_center_midfielder": (0x020, 6, 2),   # CMF - Center Midfielder
    "dmf_defensive_midfielder": (0x020, 4, 2),   # DMF - Defensive Midfielder
    "lb_left_back": (0x021, 6, 2),   # LB - Left Back
    "rb_right_back": (0x022, 0, 2),   # RB - Right Back
    "cb_center_back": (0x021, 4, 2),   # CB - Center Back
    "gk_goalkeeper": (0x022, 2, 2),   # GK - Goalkeeper
    "weak_foot_usage": (0x023, 0, 2),   # Weak Foot Usage
    "weak_foot_accuracy": (0x022, 4, 2),   # Weak Foot Accuracy
    "form": (0x017, 4, 3),   # Form
    "injury_resistance": (0x022, 6, 2),   # Injury Resistance
    "offensive_awareness": (0x003, 0, 7),   # Offensive Awareness
    "ball_control": (0x006, 5, 7),   # Ball Control
    "dribbling": (0x005, 6, 7),   # Dribbling
    "tight_possession": (0x008, 0, 7),   # Tight Possession
    "low_pass": (0x009, 6, 7),   # Low Pass
    "lofted_pass": (0x00A, 5, 7),   # Lofted Pass
    "finishing": (0x008, 7, 7),   # Finishing
    "heading": (0x00C, 0, 7),   # Heading
    "place_kicking": (0x00E, 5, 7),   # Place Kicking
    "curl": (0x010, 0, 7),   # Curl
    "speed": (0x014, 7, 7),   # Speed
    "acceleration": (0x018, 7, 7),   # Acceleration
    "kicking_power": (0x018, 0, 7),   # Kicking Power
    "jump": (0x019, 6, 7),   # Jump
    "physical_contact": (0x015, 6, 7),   # Physical Contact
    "balance": (0x016, 5, 7),   # Balance
    "stamina": (0x01A, 5, 7),   # Stamina
    "defensive_awareness": (0x004, 0, 7),   # Defensive Awareness
    "ball_winning": (0x00C, 7, 7),   # Ball Winning
    "aggression": (0x00D, 6, 7),   # Aggression
    "gk_awareness": (0x004, 7, 7),   # GK Awareness
    "gk_catching": (0x010, 7, 7),   # GK Catching
    "gk_clearing": (0x011, 6, 7),   # GK Clearing
    "gk_reflexes": (0x012, 5, 7),   # GK Reflexes
    "gk_reach": (0x014, 0, 7),   # GK Reach
    "scissors_feint": (0x024, 3, 1),   # Scissors Feint
    "double_touch": (0x029, 0, 1),   # Double Touch
    "flip_flap": (0x024, 4, 1),   # Flip Flap
    "marseille_turn": (0x024, 5, 1),   # Marseille Turn
    "sombrero": (0x024, 6, 1),   # Sombrero
    "cross_over_turn": (0x029, 1, 1),   # Cross Over Turn
    "cut_behind_turn": (0x024, 7, 1),   # Cut Behind & Turn
    "scotch_move": (0x025, 0, 1),   # Scotch Move
    "step_on_skill_control": (0x028, 3, 1),   # Step On Skill control
    "heading": (0x025, 1, 1),   # Heading
    "long_range_drive": (0x025, 2, 1),   # Long Range Drive
    "chip_shot_control": (0x028, 2, 1),   # Chip shot control
    "long_range_shooting": (0x029, 2, 1),   # Long Range Shooting
    "knuckle_shot": (0x025, 3, 1),   # Knuckle Shot
    "dipping_shot": (0x028, 4, 1),   # Dipping Shot
    "rising_shots": (0x028, 5, 1),   # Rising Shots
    "acrobatic_finishing": (0x025, 4, 1),   # Acrobatic Finishing
    "heel_trick": (0x025, 5, 1),   # Heel Trick
    "first_time_shot": (0x025, 6, 1),   # First-time Shot
    "one_touch_pass": (0x025, 7, 1),   # One-touch Pass
    "through_passing": (0x029, 3, 1),   # Through Passing
    "weighted_pass": (0x026, 0, 1),   # Weighted Pass
    "pinpoint_crossing": (0x026, 1, 1),   # Pinpoint Crossing
    "outside_curler": (0x026, 2, 1),   # Outside Curler
    "rabona": (0x026, 3, 1),   # Rabona
    "no_look_pass": (0x027, 7, 1),   # No Look Pass
    "low_lofted_pass": (0x026, 4, 1),   # Low Lofted Pass
    "gk_low_punt": (0x026, 5, 1),   # GK Low Punt
    "gk_high_punt": (0x028, 6, 1),   # GK High Punt
    "long_throw": (0x026, 6, 1),   # Long Throw
    "gk_long_throw": (0x026, 7, 1),   # GK Long Throw
    "penalty_specialist": (0x028, 0, 1),   # Penalty Specialist
    "gk_penalty_saver": (0x028, 1, 1),   # GK Penalty Saver
    "gamesmanship": (0x027, 0, 1),   # Gamesmanship
    "man_marking": (0x027, 1, 1),   # Man Marking
    "track_back": (0x027, 2, 1),   # Track Back
    "interception": (0x028, 7, 1),   # Interception
    "acrobatic_clear": (0x027, 3, 1),   # Acrobatic Clear
    "captaincy": (0x027, 4, 1),   # Captaincy
    "super_sub": (0x027, 5, 1),   # Super-Sub
    "fighting_spirit": (0x027, 6, 1),   # Fighting Spirit
    "playing_style": (0x01D, 3, 5),   # Playing Style
    "trickster": (0x01B, 7, 1),   # Trickster
    "mazing_run": (0x01F, 7, 1),   # Mazing Run
    "speeding_bullet": (0x023, 6, 1),   # Speeding Bullet
    "incisive_run": (0x023, 7, 1),   # Incisive Run
    "long_ball_expert": (0x024, 0, 1),   # Long Ball Expert
    "early_cross": (0x024, 1, 1),   # Early Cross
    "long_ranger": (0x024, 2, 1),   # Long Ranger
    "team_role": (0x150, 0, 5),   # Team Role
    "level": (0x143, 6, 2),   # Level
    "team_player_lone_wolf": (0x151, 0, 8),   # Team Player - Lone Wolf
    "passion_composure": (0x152, 0, 8),   # Passion - Composure
    "technique_strength": (0x153, 0, 8),   # Technique - Strength
    "insight_instinct": (0x154, 0, 8),   # Insight - Instinct
    "impact": (0x155, 0, 8),   # Impact
    "salary_euro": (0x15C, 0, 32),   # Salary (Euro)
    "year": (0x138, 0, 16),   # Year
    "month": (0x13A, 0, 8),   # Month
    "day": (0x13B, 0, 8),   # Day
    "stamina_bar": (0x146, 0, 7),   # Stamina Bar
    "blinking_form_arrow": (0x146, 7, 1),   # Blinking Form Arrow
    "form_arrow": (0x147, 0, 3),   # Form Arrow
    "period_unavailable_days": (0x148, 0, 8),   # Period Unavailable (days)
    "affection": (0x13E, 0, 8),   # Affection
    "max_affection": (0x13F, 0, 1),   # Max Affection (?)
    "is_transfer_listed": (0x14A, 1, 1),   # Is Transfer Listed
    "is_loan_listed": (0x14A, 2, 1),   # Is Loan Listed
    "is_listed_player": (0x13F, 1, 1),   # Is Listed Player
    "market_value_euro": (0x174, 0, 32),   # Market Value (Euro)
    "transfer_budget": (0x16ECBF4, 0, 32),   # Transfer Budget
    "salary_budget": (0x16ECC08, 0, 32),   # Salary Budget
    "focus_points": (0x00A, 0, 8),   # Focus Points
}

NUL = bytes(1)
PID_OFF = 0x30
NAME_OFF = 0x38


def _is_name(field):
    """Null-terminated UTF-8 text of letters, then zero padding to the end of the field."""
    text, _, pad = field.partition(NUL)
    try:
        s = text.decode("utf8")
    except UnicodeDecodeError:
        return False
    return (len(s) >= 2 and any(ch.isalpha() for ch in s)
            and all(ch.isalpha() or ch in " .'-" for ch in s) and not pad.strip(NUL))


def locate(career, pid=0x800000BA):
    """Offset of the created character's record: his playerID followed 8 bytes on by a name."""
    d = career.d
    pat = struct.pack("<I", pid)
    hits, i = [], 0
    while (j := d.find(pat, i)) >= 0:
        i = j + 1
        base = j - PID_OFF
        if base < 0:
            continue
        # A real record has a printable full name at +0x38 and shirt name at +0x75.
        if all(_is_name(bytes(d[base + o:base + o + 61])) for o in (NAME_OFF, 0x75)):
            hits.append(base)
    if len(hits) != 1:
        raise LookupError(f"expected one created-character record, found {len(hits)}")
    return hits[0]


def get(career, base, field):
    off, bs, bl = FIELDS[field]
    v = int.from_bytes(bytes(career.d[base + off:base + off + (bs + bl + 7) // 8]), "little")
    return (v >> bs) & ((1 << bl) - 1)


def set(career, base, field, value):
    off, bs, bl = FIELDS[field]
    if not 0 <= value < (1 << bl):
        raise ValueError(f"{field}={value} does not fit in {bl} bits")
    n = (bs + bl + 7) // 8
    v = int.from_bytes(bytes(career.d[base + off:base + off + n]), "little")
    mask = ((1 << bl) - 1) << bs
    v = (v & ~mask) | (value << bs)
    career.d[base + off:base + off + n] = v.to_bytes(n, "little")


def name(career, base):
    return bytes(career.d[base + NAME_OFF:base + NAME_OFF + 61]).split(NUL)[0].decode("utf8", "replace")
