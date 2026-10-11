"""The only path that writes a save: refuse while the game runs, back up, write, verify.

Backups go to a `backup` folder beside the game's `save` folder
(...\\2026\\backup\\<save name>\\<timestamp>-<label>), so they stay next to the real saves
but outside the folder the game scans.
"""
from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .crypto import Save


class WriteRefused(RuntimeError):
    pass


def game_running():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq FL_2026.exe", "/NH"],
                         capture_output=True, text=True).stdout
    return "FL_2026.exe" in out


def backup_dir(save_path):
    """`backup` beside the folder holding the save: ...\\2026\\save\\X -> ...\\2026\\backup\\X."""
    save_path = Path(save_path)
    return save_path.parent.parent / "backup" / save_path.name


def backup(save_path, label):
    save_path = Path(save_path)
    dest = backup_dir(save_path) / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(save_path, dest)
    return dest


def list_backups(save_path):
    d = backup_dir(save_path)
    return sorted(d.iterdir(), reverse=True) if d.exists() else []


def restore(save_path, backup_file):
    if game_running():
        raise WriteRefused("the game is running")
    save_path = Path(save_path)
    Save.load(backup_file)                       # refuse a file that does not decrypt
    backup(save_path, "before-restore")
    shutil.copy2(backup_file, save_path)


def write(career, label, dest=None):
    """Encrypt `career` to `dest` (default: where it was loaded from). Returns the backup."""
    if game_running():
        raise WriteRefused("the game is running; it holds the save in memory and would overwrite us")
    dest = Path(dest or career.path)
    expected = bytes(career.d)
    blob = career.to_bytes()
    saved = backup(dest, label)
    dest.write_bytes(blob)
    if Save.load(dest).data != expected:
        shutil.copy2(saved, dest)
        raise WriteRefused(f"{dest.name} did not verify after writing; restored the backup")
    return saved
