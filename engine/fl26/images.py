"""Game images (player portraits, club crests, manager photos) from the user's own FL26
install, converted to PNG and cached in %LOCALAPPDATA%\\CareerLab\\images. Nothing from
the game is shipped with CareerLab.

    common/render/symbol/player/<playerID>.dds     128x128 portraits (DDS inside WESYS)
    common/render/symbol/flag/e_<teamID:06d>_r.png 128x128 crests
    common/render/symbol/coach/coach_<coachID>.png 256x256 manager photos

Priority follows the game: Data/*.cpk first, then download/*.cpk in spFileList.bin order
(later wins), then Sider's loose cpk.root folders.
"""
from __future__ import annotations

import io
import os
import re
import threading
from pathlib import Path

from . import config, cpk

CACHE = Path(os.environ.get("LOCALAPPDATA", ".")) / "CareerLab" / "images"
KINDS = {
    "player": ("common/render/symbol/player", lambda i: f"{int(i)}.dds"),
    "flag": ("common/render/symbol/flag", lambda i: f"e_{int(i):06d}_r.png"),
    "coach": ("common/render/symbol/coach", lambda i: f"coach_{int(i)}.png"),
}
_DIRS = {d for d, _ in KINDS.values()}
_lock = threading.Lock()
_index = None            # (dir, name) -> ("cpk", path, offset, size) | ("file", path)
_index_game = None


def _archive_order(game):
    out = sorted((game / "Data").glob("*.cpk"))
    dl = game / "download"
    listed = []
    lst = dl / "spFileList.bin"
    if lst.exists():
        listed = [m.decode() for m in re.findall(rb"[A-Za-z0-9_\-]+\.cpk", lst.read_bytes())]
    seen = set()
    for name in listed:
        if (dl / name).exists():
            out.append(dl / name)
            seen.add(name.lower())
    out += [p for p in sorted(dl.glob("*.cpk")) if p.name.lower() not in seen]
    return out


def _sider_roots(game):
    ini = game / "SiderAddons" / "sider.ini"
    try:
        text = ini.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    roots = []
    for m in re.finditer(r'^\s*cpk\.root\s*=\s*"([^"]+)"', text, re.M):
        p = m.group(1).replace("\\\\", "\\").replace("\\_", "_")
        roots.append((game / "SiderAddons" / p).resolve())
    return roots


def build_index(game=None):
    game = Path(game) if game else config.game_dir()
    idx = {}
    if not game:
        return idx
    for path in _archive_order(game):
        try:
            for d, name, off, size, _ in cpk.files(path):
                if d in _DIRS:
                    idx[(d, name)] = ("cpk", str(path), off, size)
        except (OSError, ValueError):
            continue
    for root in _sider_roots(game):
        for d in _DIRS:
            folder = root / d
            if folder.is_dir():
                for f in folder.iterdir():
                    idx[(d, f.name)] = ("file", str(f))
    return idx


def _ensure_index():
    global _index, _index_game
    game = config.game_dir()
    with _lock:
        if _index is None or _index_game != game:
            _index, _index_game = build_index(game), game
        return _index


def warm_up():
    """Build the index in the background so the first image is quick."""
    threading.Thread(target=_ensure_index, daemon=True).start()


def path_for(kind, ident):
    """Cached PNG for (kind, id), extracting it from the game the first time; None if the
    game has no such image."""
    if kind not in KINDS:
        raise ValueError(f"unknown image kind {kind}")
    out = CACHE / kind / f"{int(ident)}.png"
    if out.exists():
        return out
    d, name_of = KINDS[kind]
    entry = _ensure_index().get((d, name_of(ident)))
    if entry is None:
        return None
    data = cpk.read(entry[1], entry[2], entry[3]) if entry[0] == "cpk" else Path(entry[1]).read_bytes()
    out.parent.mkdir(parents=True, exist_ok=True)
    if data[:4] == b"\x89PNG":
        out.write_bytes(data)
    else:                                         # DDS portraits: convert for the browser
        from PIL import Image
        Image.open(io.BytesIO(data)).convert("RGBA").save(out, "PNG")
    return out


def stats():
    idx = _ensure_index()
    return {k: sum(1 for (d, _) in idx if d == KINDS[k][0]) for k in KINDS}
