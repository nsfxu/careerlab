"""The only path that writes a save: refuse while the game runs, back up, write, verify."""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .crypto import Save

BACKUPS = Path(r"E:\FL2026\_archive\write-backups")


class WriteRefused(RuntimeError):
    pass


def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FL_2026.exe", "/NH"],
                         capture_output=True, text=True).stdout
    return "FL_2026.exe" in out


def write(career, label, dest=None):
    """Encrypt `career` to `dest` (default: where it was loaded from). Returns the backup."""
    if game_running():
        raise WriteRefused("the game is running; it holds the save in memory and would overwrite us")
    dest = Path(dest or career.path)
    expected = bytes(career.d)
    blob = career.to_bytes()
    backup = BACKUPS / dest.name / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dest, backup)
    dest.write_bytes(blob)
    if Save.load(dest).data != expected:
        shutil.copy2(backup, dest)
        raise WriteRefused(f"{dest.name} did not verify after writing; restored the backup")
    return backup
