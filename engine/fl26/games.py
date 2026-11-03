"""The games CareerLab edits. FL27 is the same PES 2021 engine as FL26 with the same save
layout (E25): what changes per game is the exe, where saves live, the save key and the
name the game writes into every save's header.
"""
from __future__ import annotations

import dataclasses
import os
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class Game:
    id: str
    name: str            # "Football Life 2027"
    short: str           # "FL27": UI text written for FL26 shows the active game's
    exe: str
    header: str          # FileHeader game string in every save the game writes
    save_dir: Path       # default Become a Legend save folder
    folders: tuple       # usual install folder names, tried on every drive
    key_file: str | None  # master key file the user supplies; None = built in (PES 2021's)


def _docs(*parts):
    return Path(os.path.expanduser(r"~\Documents")).joinpath(*parts)


FL26 = Game("fl26", "Football Life 2026", "FL26", "FL_2026.exe", "SP Football Life 2026",
            _docs("KONAMI", "eFootball PES 2021 SEASON UPDATE", "2026", "save"),
            ("FL2026", "FL 2026", "Football Life 2026", "SP Football Life 2026",
             r"Games\FL2026", r"Games\Football Life 2026"), None)
# FL27 moved its saves out of the KONAMI folder and has its own save key (FL_key.bin,
# published by SmokePatch; never shipped with CareerLab)
FL27 = Game("fl27", "Football Life 2027", "FL27", "FL_2027.exe", "SP Football Life 2027",
            _docs("SPGAME", "Football Life", "2027", "save"),
            ("SP Football Life 2027", "FL2027", "FL 2027", "Football Life 2027",
             r"Games\SP Football Life 2027", r"Games\FL2027"), "FL_key.bin")

GAMES = {g.id: g for g in (FL26, FL27)}


def by_header(header):
    return next((g for g in GAMES.values() if g.header == header), None)
