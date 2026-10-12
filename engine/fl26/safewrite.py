"""The only path that writes a save: refuse while the game runs, back up, write, verify.

Backups go to a `backup` folder beside the game's `save` folder
(...\\2026\\backup\\<save name>\\<timestamp>-<label>), so they stay next to the real saves
but outside the folder the game scans.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .crypto import Save
from .i18n import tr


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


META = ".json"


def backup(save_path, label, meta=None):
    """Copy the save aside. `meta` (what is about to change) goes to <backup>.json."""
    save_path = Path(save_path)
    dest = backup_dir(save_path) / f"{datetime.now():%Y%m%d-%H%M%S}-{label}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(save_path, dest)
    if meta:
        dest.with_name(dest.name + META).write_text(
            json.dumps({"created": datetime.now().isoformat(timespec="seconds"), **meta},
                       ensure_ascii=False, indent=1), encoding="utf-8")
    return dest


def list_backups(save_path):
    d = backup_dir(save_path)
    if not d.exists():
        return []
    return sorted((p for p in d.iterdir() if p.is_file() and not p.name.endswith(META)), reverse=True)


def read_meta(backup_file):
    try:
        return json.loads(Path(str(backup_file) + META).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def restore(save_path, backup_file):
    if game_running():
        raise WriteRefused(tr("err.gameRunning"))
    save_path = Path(save_path)
    Save.load(backup_file)                       # refuse a file that does not decrypt
    m = read_meta(backup_file) or {}
    stamp = Path(backup_file).name[:15]
    backup(save_path, "before-restore", {
        "kind": "restore",
        "title": tr("desc.beforeRestore", when=f"{stamp[6:8]}/{stamp[4:6]} {stamp[9:11]}:{stamp[11:13]}"),
        "summary": m.get("title", ""), "edits": []})
    shutil.copy2(backup_file, save_path)


def write_file(obj, label, dest=None, meta=None):
    """Like `write`, for anything with `.d` (decrypted payload), `.path` and `.to_bytes()`
    -- the option file included."""
    if game_running():
        raise WriteRefused(tr("err.gameRunning"))
    dest = Path(dest or obj.path)
    expected = bytes(obj.d)
    blob = obj.to_bytes()
    saved = backup(dest, label, meta)
    dest.write_bytes(blob)
    if Save.load(dest).data != expected:
        shutil.copy2(saved, dest)
        raise WriteRefused(tr("err.notVerified", name=dest.name))
    return saved


def write(career, label, dest=None, meta=None):
    """Encrypt `career` to `dest` (default: where it was loaded from). Returns the backup."""
    if game_running():
        raise WriteRefused(tr("err.gameRunningSave"))
    dest = Path(dest or career.path)
    expected = bytes(career.d)
    blob = career.to_bytes()
    saved = backup(dest, label, meta)
    dest.write_bytes(blob)
    if Save.load(dest).data != expected:
        shutil.copy2(saved, dest)
        raise WriteRefused(tr("err.notVerified", name=dest.name))
    return saved
