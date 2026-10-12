"""pesmaster.com: a second, independent source for real squads (cross-check for efootballdb).

`https://www.pesmaster.com/x/efootball-2022/team/<teamID>/` (any slug works; the site
redirects) is HTML only. The club's current squad is the player cards between the
"<club> eFootball Players" and "<club> eFootball Lineup" headings; links carry the player
ID, which is FL26's ID (verified 2026-10-12: Cruzeiro's 28 players identical to
efootballdb's). Sections after that (Legends, Generations) are not the squad.

Clubs without eFootball's player licence list invented players there too, with IDs far
above real ones (Clube do Remo: 8,563,654…): `INVENTED_ID` filters them.

Polite like efdb: fetched only on request, one page per club, cached a day.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request

from .efdb import CACHE, UA, _fresh

URL = "https://www.pesmaster.com/x/efootball-2022/team/{}/"
INVENTED_ID = 1_000_000
_LINK = re.compile(r'href="/([a-z0-9-]+)/efootball-2022/player/(\d+)/"')


def _slug_name(slug):
    return " ".join(w.capitalize() for w in slug.split("-"))


def parse_squad(page):
    """[(player ID, name from the link slug)] in page order, invented players dropped."""
    start = page.find("eFootball Players</h")
    end = page.find("eFootball Lineup</h", start)
    if start < 0:
        raise ValueError("pesmaster page layout changed: squad section not found")
    section = page[start:end if end > start else len(page)]
    out, seen = [], set()
    for slug, pid in _LINK.findall(section):
        pid = int(pid)
        if pid in seen or pid >= INVENTED_ID:
            continue
        seen.add(pid)
        out.append((pid, _slug_name(slug)))
    return out


def squad(team_id, max_age_hours=24, refresh=False):
    """The club's current squad on pesmaster: [(player ID, name)], cached."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"pm-team-{int(team_id)}.json"
    if not refresh and _fresh(path, max_age_hours):
        return [tuple(x) for x in json.loads(path.read_text(encoding="utf-8"))]
    req = urllib.request.Request(URL.format(int(team_id)), headers={
        "User-Agent": UA, "Accept": "text/html", "Referer": "https://www.pesmaster.com/"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    rows = parse_squad(page)
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def cross_check(team_id, efdb_ids, refresh=False):
    """Compare efootballdb's squad (`efdb_ids`) with pesmaster's.
    Returns {"source", "agree", "onlyEfdb": [IDs], "onlyPesmaster": [(ID, name)]} or {"error"}."""
    try:
        rows = squad(team_id, refresh=refresh)
    except Exception as e:                      # a second opinion must never block a sync
        return {"source": "pesmaster.com", "error": str(e)}
    pm = {pid for pid, _ in rows}
    ef = set(efdb_ids)
    return {"source": "pesmaster.com", "agree": pm == ef, "count": len(pm),
            "onlyEfdb": sorted(ef - pm),
            "onlyPesmaster": [(pid, name) for pid, name in rows if pid not in ef]}
