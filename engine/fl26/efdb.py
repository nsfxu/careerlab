"""efootballdb.com client: real squads with FL26-compatible team and player IDs.

`GET https://api.efootballdb.com/api/2022/teams/<teamID>` returns the squad (shirt,
order, captain, set-piece takers), the coach, the tactics and each player's full record.
Its IDs are FL26's IDs (verified 2026-10-11 on Cruzeiro: 23/23 players).

Polite by construction: fetched only on request, one call per club, cached on disk.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path

API = "https://api.efootballdb.com/api/2022/teams/{}"
CACHE = Path(os.environ.get("LOCALAPPDATA", ".")) / "CareerLab" / "efdb-cache"
UA = "Mozilla/5.0 (CareerLab personal squad sync)"


def team(team_id, max_age_hours=24, refresh=False):
    """The club's efootballdb record (dict), from cache when fresh enough."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"team-{int(team_id)}.json"
    if not refresh and path.exists() and time.time() - path.stat().st_mtime < max_age_hours * 3600:
        return json.loads(path.read_text(encoding="utf-8"))
    req = urllib.request.Request(API.format(int(team_id)), headers={
        "User-Agent": UA, "Referer": "https://www.efootballdb.com/", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))["data"]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def player(pid, max_age_hours=168, refresh=False):
    """One player's efootballdb record (`/api/2022/players/<id>`), cached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"player-{int(pid)}.json"
    if not refresh and path.exists() and time.time() - path.stat().st_mtime < max_age_hours * 3600:
        return json.loads(path.read_text(encoding="utf-8"))
    req = urllib.request.Request(f"https://api.efootballdb.com/api/2022/players/{int(pid)}", headers={
        "User-Agent": UA, "Referer": "https://www.efootballdb.com/", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))["data"]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def squad(team_id, **kw):
    """[(pid, shirt, order, player dict, assignment dict)] sorted by squad order."""
    d = team(team_id, **kw)
    rows = []
    for a in d.get("player_assignments", []):
        p = a["player"]
        rows.append((p["pes_id"], a.get("shirt_number"), a.get("order_number"), p, a))
    rows.sort(key=lambda r: (r[2] if r[2] is not None else 999))
    return rows


def coach(team_id, **kw):
    c = team(team_id, **kw).get("coach") or {}
    return {"id": c.get("pes_id"), "name": c.get("name") or c.get("english_name") or ""}
