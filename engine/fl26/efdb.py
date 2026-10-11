"""efootballdb.com client: real squads with FL26-compatible team and player IDs.

`GET https://api.efootballdb.com/api/2022/teams/<teamID>` returns the squad (shirt,
order, captain, set-piece takers), the coach, the tactics and each player's full record.
Its IDs are FL26's IDs (verified 2026-10-11 on Cruzeiro: 23/23 players).

Polite by construction: fetched only on request, one call per club, cached on disk.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from pathlib import Path

API = "https://api.efootballdb.com/api/2022/teams/{}"
SITE = "https://www.efootballdb.com"
CACHE = Path(os.environ.get("LOCALAPPDATA", ".")) / "CareerLab" / "efdb-cache"
UA = "Mozilla/5.0 (CareerLab personal squad sync)"


def _get(url, accept="application/json"):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Referer": SITE + "/", "Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def _fresh(path, max_age_hours):
    return path.exists() and time.time() - path.stat().st_mtime < max_age_hours * 3600


def team(team_id, max_age_hours=24, refresh=False):
    """The club's efootballdb record (dict), from cache when fresh enough."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"team-{int(team_id)}.json"
    if not refresh and _fresh(path, max_age_hours):
        return json.loads(path.read_text(encoding="utf-8"))
    data = json.loads(_get(API.format(int(team_id))))["data"]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    # the squad carries every player's full record: seed the player cache so creating
    # them later costs no extra request
    for a in data.get("player_assignments", []):
        p = a.get("player") or {}
        pp = CACHE / f"player-{p.get('pes_id')}.json"
        if p.get("pes_id") and not _fresh(pp, 168):
            pp.write_text(json.dumps(p, ensure_ascii=False), encoding="utf-8")
    return data


def player(pid, max_age_hours=168, refresh=False):
    """One player's efootballdb record (`/api/2022/players/<id>`), cached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"player-{int(pid)}.json"
    if not refresh and _fresh(path, max_age_hours):
        return json.loads(path.read_text(encoding="utf-8"))
    data = json.loads(_get(f"https://api.efootballdb.com/api/2022/players/{int(pid)}"))["data"]
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def competitions(max_age_hours=168, refresh=False):
    """[{id, name, national, teams: [team IDs]}] for every league efootballdb lists.

    Read from the site's own team-list page data (`/_next/data/<buildId>/en/teams.json`);
    the build ID changes on each deploy, so it is read from the home page first."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "competitions.json"
    if not refresh and _fresh(path, max_age_hours):
        return json.loads(path.read_text(encoding="utf-8"))
    m = re.search(r'"buildId":"([^"]+)"', _get(SITE + "/", "text/html"))
    if not m:
        raise RuntimeError("efootballdb's page layout changed: league list not found")
    comps = json.loads(_get(f"{SITE}/_next/data/{m.group(1)}/en/teams.json"))["pageProps"]["competitions"]
    out = [{"id": c["pes_id"], "name": c.get("competition_name") or f"League {c['pes_id']}",
            "national": bool(c.get("is_national_team_competition")),
            "teams": [e["team"]["pes_id"] for e in c["entries"] if e.get("team")]}
           for c in comps if c.get("entries")]
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def made_up(team_id, **kw):
    """True when eFootball lacks the club's player licence and lists invented players
    (e.g. Clube do Remo: "Batatinha Delfim"...). FL26 usually has the real squad then."""
    d = team(team_id, **kw)
    pa = d.get("player_assignments", [])
    fake = sum(1 for a in pa if a["player"].get("fake_version"))
    return d.get("has_licensed_names") == 0 or (pa and fake * 2 > len(pa))


def squad(team_id, **kw):
    """[(pid, shirt, order, player dict, assignment dict)] sorted by squad order.
    Invented players (`fake_version`) are left out."""
    d = team(team_id, **kw)
    rows = []
    for a in d.get("player_assignments", []):
        p = a["player"]
        if p.get("fake_version"):
            continue
        rows.append((p["pes_id"], a.get("shirt_number"), a.get("order_number"), p, a))
    rows.sort(key=lambda r: (r[2] if r[2] is not None else 999))
    return rows


def coach(team_id, **kw):
    c = team(team_id, **kw).get("coach") or {}
    return {"id": c.get("pes_id"), "name": c.get("name") or c.get("english_name") or ""}
