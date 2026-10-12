# CareerLab

**Edit a Football Life 2026 *Become a Legend* career that is already in progress**: bring
squads up to date with the real world, move and release players, create players the game
doesn't have, edit ratings and skills, change managers, and never lose a career doing it.

![Squad view and player panel](docs/screenshots/01-squad-and-player.png)

## What it does

- **Sync a club or a whole league** to the real squads on [efootballdb.com](https://www.efootballdb.com)
  (same player IDs as FL26): moves, free players, new players, releases, real shirt numbers
  and captains, in one reviewed batch.
- **Create players FL26 doesn't have** (academy promotions, new signings) with their real
  ratings, age, position, style and nationality, and a lookalike face.
- **Edit any player**: the 25 abilities, skills, shirt number, captaincy; move or release him.
- **Edit your own player** (the created character): abilities and skills.
- **Change a club's manager**, with or without his tactics.
- **Safe by design**: nothing is written until you apply, every apply is checked and backed up,
  and the save is never touched while the game is running.

## Install

1. Download `CareerLab-Setup-<version>.exe` from the repository's **Releases** page and run it
   (per-user install, no admin). Windows SmartScreen may warn because the installer is not
   signed: *More info → Run anyway*.
2. On first start CareerLab looks for your FL2026 folder (the one with `FL_2026.exe`) and your
   saves folder, and asks if it can't find them.
3. CareerLab reads FL26's player database through a small read-only Sider module
   (`DBDump.lua`). If it isn't there yet, the setup screen installs it; then start the game
   once, wait for the main menu, close it, and press *Check again*.

Requirements: Windows 10/11, Football Life 2026 with Sider (it ships with the Smoke Patch).

## Using it

**Squads and players.** Pick the career slot at the top, then a club on the left (your club is
pinned first). Click a player to open his panel: abilities grouped like the game (Ataque,
Físico, Defesa, Goleiro) with rating bars, skills as chips, shirt number, captaincy, move and
release. Your own player is marked with a star.

![Your player](docs/screenshots/02-your-player.png)

**Sync a club with the real world.** *Sync real squad* fetches the club's current squad from
efootballdb and shows what would change. Untick anything you want to keep as it is. Players
FL26 lacks are created with their real ratings; players FL26 knows under another ID are
recognised by name, not duplicated.

![Club sync](docs/screenshots/03-club-sync.png)

**Review, then apply.** Every edit is staged first. *Review & apply* lists them (undo one, or
*Undo all*), checks the edits against the save, and only then writes. Close the game before
applying: CareerLab refuses to write while it runs.

![Review and apply](docs/screenshots/04-review-and-apply.png)

**Sync a whole league.** *Sync league* plans every club of a league at once. A player who
changed clubs inside the league is moved, never lost; clubs keep at least 23 players; clubs
whose real squad eFootball doesn't license (invented names) are left as FL26 has them.

![League sync](docs/screenshots/05-league-sync.png)

**Backups.** Every apply first saves the career as it was, beside your saves in a `backup`
folder. Each backup says what restoring it would undo, with the full list of edits.

![Backups](docs/screenshots/06-backups.png)

**Search.** The search box finds any player in FL26's database: where he plays in your career,
or whether he is free. A player the career has never had can be created at the open club.

![Search](docs/screenshots/07-search.png)

## How it works

A career save refers to players by `(handle, player ID)` pairs; the handle points into a
hidden **player registry** inside the save, and the registry record decides who the player
is in that career (position, ratings, age, club). CareerLab decrypts the save, edits the
squad tables, the registry and the manager records directly, validates the result, and
re-encrypts it. Players FL26 lacks borrow the ID of an obscure database player that is
renamed in the option file. Everything was proven in game first; the evidence is in
[LIMITS.md](LIMITS.md).

## Limits

- Become a Legend only (not Master League).
- Set-piece takers can't be set: the AI manager picks them in BAL.
- The captain wears the armband only when the manager starts him.
- Players new to FL26 get a borrowed face from a player of the same nationality.
- About 2,500 new players fit in one career (registry capacity).
- Squad data is only as current as eFootball's weekly update.

## For developers (and AI assistants)

Start with [CLAUDE.md](CLAUDE.md) and [docs/](docs/): architecture, save format, testing,
data sources, build and release, and the lessons from what didn't work.

| | |
|---|---|
| `engine/fl26/` | Python engine: save format + JSON-lines RPC server |
| `app/` | Electron app (plain JS, no build step) |
| `harness/` | Drives the game and the app for verification; `readme_shots.py` regenerates these screenshots |
| `lab/` | Experiment scripts behind LIMITS.md |
| `FEATURES.md` | Feature list, status and next steps |

```
cd engine && python -m pip install -r requirements-dev.txt && python -m pytest -q
cd app && npm install && npx electron .
python build.py                      # tests -> frozen engine -> dist/CareerLab-Setup-<version>.exe
git tag v0.3.0 && git push origin v0.3.0   # GitHub Actions builds and publishes a Release
```

Personal project, not affiliated with Konami, PES Smoke Patch or efootballdb. Football Life
2026 data belongs to its owners.
