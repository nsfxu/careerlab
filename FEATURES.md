# CareerLab — feature list

**Name:** CareerLab. **Theme:** dark, like FL26's own menus — charcoal background, deep red
accents, red-bordered panels; position badges in the game's colours (GO yellow, ZC/LD/LE
blue, VOL/MLG green, PTE/PTD/CA red); club colours as a small accent. Dark only for now.

Desktop app (Electron) for editing a **Football Life 2026 Become a Legend career that is
already in progress**. Every feature below is backed by an experiment verified in game
(see [LIMITS.md](LIMITS.md) for the evidence, E01–E16).

Status: **Ready** = mechanism proven, needs only UI · **Partial** = works, a piece is still
undecoded · **Later** = needs more research first.

---

## 1. Open a career

| Feature | Status |
|---|---|
| Pick a BAL save (`BL0000000x`); show career date, club, created character | Ready |
| Pick an option file (`EDIT00000000`) as the source for names, squads, coaches | Ready |
| Refuse to open or write while the game is running | Ready |
| Health check on open: squad consistency, duplicate players, broken references | Ready |

## 2. Squads and transfers

| Feature | Status |
|---|---|
| Browse every club's squad as the career holds it (names, positions, ratings) | Ready |
| Search a player across the whole career: club, handle, reachable or not | Ready |
| Move a player from one club to another | Ready |
| Release a player | Ready |
| **Add a player the career has never known** (added to the database after the career began) | **Done** (app, from efootballdb) |
| New players get their real profile (position, abilities, style, age, nationality) from a donor career | Ready |
| Squads up to 40 players (the old "starting size" cap was wrong) | Ready |
| **Sync a whole league** to efootballdb: every club in one plan, moves inside the league, review → apply | **Done** (skips clubs with invented squads, keeps squads at 23+) |
| Sync the whole league to an option file | Ready |
| **Sync a club to its real-world squad** (efootballdb.com, IDs match FL26): diff, then add / release / renumber / captain in one go | **Done** |
| **Real players missing from the game** (e.g. academy promotions): rename a spare database record, pick a face donor, set stats, add to the career | **Done** (app; lookalike face) |
| Repair the game's own duplicates (a player listed twice in one squad) | **Done** (2.0; 11 → 0 on the rollover save) |
| **Squad tidy tools**: renumber a squad (keepers 1/12/23, no clashes), sort by position, trim an oversized squad | Ready |
| **Reset a club to the database**: put a squad back to what the option file says | Ready |

## 3. Player editor

| Feature | Status |
|---|---|
| Edit the 25 abilities of any player (game recalculates the overall) | Ready |
| Edit age, form, weak foot | Ready |
| Edit skills, playing style, position proficiency, registered position, weak foot, form, age | **Done** (2.0; style names verified E23) |
| Build a new player's profile from scratch (no donor career) | Ready — full block decoded; efootballdb supplies the values |

## 4. Created character (your BAL player)

| Feature | Status |
|---|---|
| Edit all abilities | Ready |
| Add / remove skills | Ready |
| Edit height, weight, foot, positions, playing style, weak foot, form, injury resistance | **Done** (2.0, verified E23) |
| Condition and contract: form, injury days, stamina, salary, market value | Partial — writes work, BAL has no screen to confirm salary/contract |
| Move him to another club | Later |

## 5. Managers and tactics

| Feature | Status |
|---|---|
| See every club's manager | Ready |
| **Change a manager and bring his tactics** (full swap) | Ready |
| Change a manager but **keep the club's tactics** (name + ID only) | Ready |
| Hire a coach without a club (669-coach pool) | Ready |
| Copy another club's formations and tactics, keeping the manager | **Done** (2.0, verified E23) |
| Formation editor: pick one of the three presets, positions | Ready |
| Tactical choices (attacking style, build-up, attacking area, pressuring…) | Ready (verified E18) |
| Defensive line / compactness sliders | Partial — written, not shown on the screen tested |
| Shirt numbers | **Done** (editor + real numbers in sync) |
| Captain | **Done** (worn when he starts) |
| Penalty / corner / free-kick takers | Not possible in BAL — the AI manager picks them by rating |

## 6. Safety (built in, not optional)

| Feature | Status |
|---|---|
| Every edit is staged first; nothing writes until **Apply** | Ready |
| Plan view: what will change, and why each skipped item was skipped | Ready |
| Automatic backup before every write, verified by re-reading the file | Ready |
| One-click restore of any backup | Ready |
| Validator gate: refuse a write that introduces new errors | Ready |
| Created character is never touched by bulk operations | Ready |

## 7. Tools

| Feature | Status |
|---|---|
| Export squads to CSV (club or career) | **Done** (2.0) |
| Compare two saves (what the game changed between them) | Ready |
| **Player career stats viewer**: matches, goals, history per player, read from the save | Later — layout not yet decoded |
| **Career timeline**: snapshot every autosave the game writes, show what happened between them (AI transfers, manager changes, player development) | Ready — save diff exists |

## 8. Workflow

| Feature | Status |
|---|---|
| **Edit packs**: save a set of edits as a file, reapply it to another career or slot, share it | Ready — staging already produces the edit list |
| **Per-edit undo** in the staged list (not only whole-backup restore) | Ready |
| **Portuguese / English interface**, position labels matching the game (ZC, VOL, PTE…) | Ready |

## 9. Verify in game

| Feature | Status |
|---|---|
| **Verify button**: after Apply, launch the game, load the career, open the edited squad and show a screenshot | Ready — the test harness already does this |
| **In-game companion (Sider module)**, like the substitution mod: reads the career live from memory and reports back to the app which edits loaded correctly (no screenshots needed); optional overlay line confirming the active edits | Later — builds on BALSubProbe / BALSquadEdit |

---

## 10. Install

| Feature | Status |
|---|---|
| **Windows installer** (per-user, no Python/Node needed): `python build.py` → `dist/CareerLab-Setup-<version>.exe` | **Done** (unsigned) |
| First-run setup: finds the game and saves folders, installs the database reader (DBDump.lua) if missing | **Done** |

## 11. Next steps (agreed 2026-10-11)

| Step | Notes |
|---|---|
| **GitHub workflow with tags and releases** (**Done** 2026-10-12) | Pushing a tag `v*` runs Actions on a Windows runner: tests, then PyInstaller, then electron-builder; the installer and `latest.yml` go to a GitHub Release. The version comes from the tag. |
| **Auto-update from GitHub Releases** (**Done** 1.0.0) | `electron-updater` checks on start, downloads in the background and offers "Restart to update". Decided: the repo is public (MIT) and the app updates from its Releases. |
| **Docs review for AI contributors** (**Done** 2026-10-12) | A `CLAUDE.md` / `docs/` set: architecture (engine to RPC to Electron), save format map (pointers to LIMITS.md), safety rules (backups, game-running check, never touch the user's career), how to test (unit tests, CDP UI tests, in-game harness), build and release, and the mistakes not to repeat. |
| **README review with screenshots** (**Done** 2026-10-12) | What CareerLab does, install, first-run setup, each feature with a screenshot (squad view, player panel, club sync, league sync, review and backups), plus limits and FAQ. Screenshots are captured automatically over CDP so they stay up to date. |
| **Undo all changes** (**Done** 2026-10-12) | One button in the review dialog (and the top bar) that clears every staged edit at once, after a confirm. Per-edit Undo stays. |
| **More descriptive backups** (**Done** 2026-10-12) | Each backup records what the apply changed: a summary ("Brasileirão sync: 15 moves, 64 new players, 110 releases"), the clubs it touched and the full edit list, stored in a small `.json` file beside the backup. The backups dialog shows the summary and expands to the full list; backups made before a restore or by experiments are labelled as such. |
| **Portuguese (pt-BR) / English interface** (**Done** 1.0.0) | Switched in Settings by clicking the Brazilian or US flag; remembered between sessions. All UI text moves into string tables. Game terms (positions, abilities, skills) already follow FL26's Portuguese and stay matched to the game in both languages. |
| **pesmaster.com as a second squad source** (**Done** 1.0.0) | `https://www.pesmaster.com/<club>/efootball-2022/team/<teamID>/`. First probe (2026-10-11): the team ID is FL26's (Cruzeiro 274), and the player links carry the same player IDs. All 28 Cruzeiro players match efootballdb's squad exactly, including the 5 academy players FL26 lacks. The page is HTML (740 KB), so it needs parsing rather than a JSON API. To research: player pages (ratings, positions, skills), how quickly it follows transfers compared with efootballdb, coach and tactics data, and whether it lists real names for the clubs where efootballdb shows invented ones (Clube do Remo). Use: a cross-check in the sync dialog ("efootballdb and pesmaster disagree on 2 players"), and a fallback when efootballdb is down or behind. Same politeness rules: on request only, one page per club, cached. |

## Known limits (shown in the app, not hidden)

- **Registry capacity**: about 2,500 more new players per career.
- **New player profiles** need a donor: a career created with a database that contains
  him (your Master League save covers 1,586 players this career lacks).
- **Become a Legend only.** Master League is out of scope for now.
- The game itself creates a few duplicates at season rollover; the app flags them but
  does not blame the user's edits.

## Research needed: where do squad updates come from?

Two features depend on a reliable, up-to-date source of real squads, still to be chosen:
- **Sync a club to its real-world squad** (section 2)
- **Transfer-window helper**: when the career reaches a window, suggest syncing to the
  latest option file or real squads (pairs with the career timeline)

**Decision (researched 2026-10-11): efootballdb.com is the source; pesdb.net is a cross-check.**

- **IDs match FL26 exactly** — team IDs (Cruzeiro 274, Vasco 136, Corinthians 1247…) and
  player IDs (all 23 Cruzeiro players that exist in FL26). Sync is an ID lookup, no name matching.
- **One JSON call per club:** `https://api.efootballdb.com/api/2022/teams/<teamID>` returns
  the squad (shirt numbers, captain, penalty/corner/free-kick takers), the coach, the team's
  tactics + formations, and every player's full record (165 fields: positions, abilities,
  age, height, contract, market value, loan club…). No login needed.
- **Players missing from FL26 come with full stats** — Cruzeiro's 5 (Marcelo, Kauã Moraes,
  Vitor Lamounier, Rayan Lelis, Ruan Índio) are exactly the academy players from August.
  Their profiles can be built from this data, no donor career needed.
- Competition lists: `https://www.efootballdb.com/_next/data/<buildId>/en/teams.json`
  (build ID read from the home page; changes on each site deploy) — Brasileirão = 149,
  Série B = 588, 20 clubs each.
- **pesdb.net**: same IDs (`/efootball/players/fabricio-bruno-111809`), HTML only, oriented to
  Dream Team cards, no squad API → use only to double-check a player.
- Be polite: fetch only on user request, one call per club, cache results. Terms of use
  not stated on the site — keep it a personal tool.
- Still to check: how fast efootballdb follows real transfers (it mirrors Konami's weekly
  eFootball data, so it is only as current as eFootball itself).

## To think about later

- Contracts and loans for any player (end dates and loan club partly decoded)
- Request-substitution mod (BALRequestSub) as a switch inside the app
- Create a custom manager in the coach pool, then hire him

## Not in the first version

- Master League support
- Created character club transfers
- Club finances, youth squad
- Live editing while the game runs
