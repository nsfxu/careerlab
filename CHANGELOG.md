# Changelog

## 2.0.0 — 2026-10-12

- **Profile editor**: playing style, registered position, position ratings on a mini pitch
  (click to cycle C/B/A), weak foot, form and age for any player; height, weight, best foot
  and injury resistance for your own player. Style names exactly as FL26 shows them.
- **Copy tactics**: give a club another club's formations and tactics, keeping its manager.
- **Reset a club to the FL26 database**: the club sync dialog can also target the squad in
  FL26's own database (the option file new careers start from), undoing AI transfers.
- **Free agents**: browse the players without a club (strongest first, filter by position,
  age and name) and sign them for the open club.
- **Overall column** in the squad table: an estimate from the abilities, within about 3 points
  of the game's own overall.
- **Export squads to CSV** (this club or all clubs) from Settings → Tools.
- **Repair duplicate entries**: the game lists some players twice at season rollover; one
  click keeps a single entry (and fixes the manager's lineup/captain references).
- UI review: the squad toolbar keeps the search usable on narrower windows, dialogs scroll
  when taller than the window, unknown values are no longer shown as "null".

## 1.0.1 — 2026-10-12

- Header: the career and game status no longer wrap onto several lines; the update button
  reads "Update to x.y.z" (details in its tooltip); narrow windows shorten the career
  name and keep only the status dot.

## 1.0.0 — 2026-10-12

First public release.

**Squads and the real world**
- Sync a club to its real squad on efootballdb.com (same player IDs as FL26): moves, free
  players, new players, releases, real shirt numbers and captain, reviewed before applying.
- Sync a whole league in one plan: transfers inside the league become moves, clubs keep at
  least 23 players, clubs with invented eFootball squads are left as FL26 has them.
- pesmaster.com as a second opinion: the club sync says whether it lists the same squad.
- Players FL26 lacks are created with real ratings, age, position, style and nationality, and
  a face borrowed from a player of the same nationality.
- A player FL26 knows under another ID is recognised by name instead of duplicated.

**Editing**
- Player panel: abilities grouped like the game with rating bars, skills, shirt number,
  captaincy, move and release. Your own player's abilities and skills.
- Change a club's manager, with or without his tactics.
- Search any player in FL26's database; create one the career has never had.

**Safety**
- Everything is staged first; Review shows each edit (undo one or all) and checks the save.
- Refuses to write while the game runs; every write is backed up and verified.
- Backups say what restoring them would undo, with the full list of edits.

**App**
- Portuguese (pt-BR) and English, switched with the flags in Settings. Positions, abilities
  and skills follow the language: FL26's Portuguese labels or PES 2021's English names.
- Automatic updates from GitHub Releases ("Restart to update").
- First-run setup finds the game and saves folders and installs the database reader.
- Windows installer (per-user, no admin).

## 0.2.0 — 2026-10-11
UI review: icon set, cleaner layout, grouped player panel. League sync, installer.

## 0.1.0 — 2026-10-11
First working build: club sync, new players, player and manager editing, backups.
