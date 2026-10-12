# Data sources

## FL26's own database (Sider dump)

The engine needs FL26's base database (names, teams, assignments, appearances). It is not
read from the CPK: the Sider Lua module `DBDump.lua` (shipped in `engine/fl26/assets/`)
writes each database file as the game loads it to `<game>\SiderAddons\dbdump\` as
`<table>.copyN.raw`. The game loads each table 2–3 times; the highest copy is the patched
database it really uses (`config.table_file` picks it). Layouts: see `database.py` docstring.
Nationality in a dump player record = 9 bits at bit 233.

The first-run setup can enable the module (one `lua.module = "DBDump.lua"` line in
`sider.ini`, backup kept); then the user starts the game once.

## efootballdb.com (main squad source)

- `GET https://api.efootballdb.com/api/2022/teams/<teamID>`: squad (shirt, order, captain,
  takers), coach, tactics, and every player's full record (abilities, positions, skills,
  style, age, nationality…). No login; send a browser-like User-Agent and Referer.
- `GET https://api.efootballdb.com/api/2022/players/<id>`: one player (rarely needed: the team
  call already carries the record, and `efdb.team` seeds the player cache from it).
- League list: `https://www.efootballdb.com/_next/data/<buildId>/en/teams.json`
  (`pageProps.competitions[].entries[].team.pes_id`); the build ID comes from the home page
  `"buildId"` and changes on every site deploy.
- **IDs are FL26's IDs** (team and player), so sync is an ID lookup.
- **Invented squads**: clubs without eFootball's player licence list made-up names (team
  `has_licensed_names: 0`, players `fake_version` truthy, e.g. Clube do Remo). Skip them; FL26
  usually has the real squad.
- Some squads are thin (16–18 players): the league sync keeps clubs at 23+.
- Mappings to FL26: abilities by name (`profiles.ABILITY_SOURCE`), skills by name, positions =
  registry position codes, playing style via `attributes.STYLE_FROM_EFOOTBALLDB` (0 is the
  goalkeeper style for keepers, 12 otherwise; unknown = none).
- Politeness: fetch only on user request, one call per club, cache (teams 24 h, players and
  leagues 7 days). Personal tool; no terms of use stated.

## pesmaster.com (planned second source)

`https://www.pesmaster.com/<club>/efootball-2022/team/<teamID>/`, HTML only. Same IDs as FL26:
Cruzeiro's 28 players are identical to efootballdb's. Planned as a cross-check and fallback
(FEATURES.md section 11).

## pesdb.net

Same IDs, HTML only, oriented to Dream Team cards, no squad API: cross-check single players only.

## Game images (the user's own install)

Read from the CPK archives on demand, never shipped: `common/render/symbol/player/<id>.dds`
(29,484 portraits, DDS in WESYS), `common/render/symbol/flag/e_<teamID:06d>_r.png` (3,297
crests), `common/render/symbol/coach/coach_<coachID>.png` (1,021 photos). Priority like the
game: `Data/*.cpk`, then `download/*.cpk` in `spFileList.bin` order (later wins), then Sider
`cpk.root` folders. Borrowed spare IDs and the created player get a silhouette (their
portrait would be someone else's).

League emblems: `common/render/symbol/emblemLc/emb_<compID:04d>_l.png` (some leagues only have
the `_w`/`_e`/`_b` colour variants). `compID` is FL26's competition ID, not efootballdb's: the
CompetitionEntry dump (12-byte records: teamID, entryID, u8 competitionID) maps it to teams,
and `database.match_competition` picks the FL26 competition whose clubs are most like the
efootballdb league's (Jaccard; ties go to the lower ID, since each cup follows its league).
