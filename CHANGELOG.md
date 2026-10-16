# Changelog

## 2.5.0 — 2026-10-15

- **National teams: sync with the FL26 database** (*FL26 squad* button): brings a national
  squad to the one in FL26's own database (your patch's call-up): call-ups in the database's
  order, drops, shirt numbers. A meter shows the squad size after the sync (18–23); database
  squads of 26 get their first 23 ticked; dual nationals listed by the database are allowed;
  your own player stays unless you tick him. Verified in game: the friendly's game plan used
  the synced squad.
- The FL26 squad sync can also fix **ages**: database age + the seasons the career has run
  (worked out from the save itself), offered where they differ by 2+ years — mostly regens
  that reuse a retired player's ID (Marquinhos 17 → 36, Messi 17 → 43 in a 2030 career).
- Fixed: calling up a player without a club failed when applying ("has no handle in this
  career").

## 2.4.0 — 2026-10-12

- **Review window redone**: a summary of the staged edits by kind (transfers, player edits,
  squad, managers & tactics, national teams) with icons; edits grouped by player (portrait),
  club (crest) or sync batch, each group with its own Undo; an icon per kind of edit;
  "34 → 27" shown as old value → new value; big sync batches start folded.
- Free agents and call-up lists: portraits no longer cut off, each player's country flag, the
  rating as a coloured badge, a green "Staged ✓" once signed.
- Club sync window: a summary row (moving in, free agents, new, leaving, numbers, already
  matching); each section in its own box with a coloured icon and an "All" checkbox; the
  source club's crest on moves; whole rows clickable; old → new shirt numbers; the options in
  an Options box and the notes (real coach, set-piece takers) as a list with icons.
- "Move in" no longer takes a player's national team for his current club.
- Changing the same value again replaces the staged edit instead of adding another (typing a
  new age was staged once per keystroke); setting a value back to what the save has removes
  the edit.

## 2.3.0 — 2026-10-12

- **National teams** (*Nations* tab): every national squad of the career (140 in the test
  save), named from its players' nationality, your country first. A national team opens like
  a squad; *Call up* lists the players of that nationality (strongest first, with their club)
  and *Drop from squad* removes one, your own player included. Call-ups only change the squad
  list (players keep their clubs) and squads stay between 18 and 23. The game picks a new
  squad before every international window, so an edit lasts until the next call-up (tested in
  game: an edit made after the call-up is used in that window's friendly).
- Applying edits shows a progress bar with the current step (reading, applying edit n of N,
  checking, backing up and writing, reloading); the review window can't be closed mid-apply.
- Settings reorganised: General / Game and saves / Tools / About sections; each folder and the
  database show a Found / Missing / Action needed label; long paths stay on one line (end
  visible, full path on hover) with an *Open folder* button; the setup explanation and
  *Check again* only appear while something is missing, otherwise a plain *Done*; version and
  updates have their own About row.
- Error messages no longer start with "Error invoking remote method".

## 2.2.0 — 2026-10-12

- New title bar: CareerLab draws its own window (custom minimize / maximize / close buttons,
  drag anywhere on the bar, double-click to maximize) with an angled red brand plate.
- The save picker, player name and club are one career switcher (crest, player, club and
  slot; click it for the list of saves).
- Quieter header: the game status is a small icon with a green dot while the game is closed
  and a red "Game running" label only when saving is blocked; Backups and Settings are icon
  buttons (names on hover).
- **Leagues tab** beside Clubs: every league of the career (yours first) with FL26's own
  league emblems. Clicking a league shows it in the middle panel: its clubs (click one to open
  its squad), managers, squad sizes and a *Sync league* button. It replaces the title bar's
  "Sync league" button.
- **Tabs** over the middle panel, like VS Code: every club and league you open gets a tab. A
  single click opens a preview tab (italic) that the next click replaces; double-click (or
  staging an edit for that club) keeps it. A dot marks clubs with staged edits. Close with
  the ×, a middle-click or Ctrl+W; Ctrl+Tab / Ctrl+Shift+Tab switch; drag to reorder. The
  tabs are remembered per save.

## 2.1.0 — 2026-10-12

- **Game images**: player portraits, club crests and manager photos, read from your own FL26
  install (nothing is downloaded or shipped) — in the club list, squad table, squad header and
  player panel; also in search results, the club and league sync dialogs, the club pickers and
  the career chip; the player panel header shows a large portrait over a faded club crest.
- Position map drawn like FL26's player card: the game's pitch zones and markings, A in solid
  teal, B in light teal; names on hover, click cycles C/B/A.
- The club list can be collapsed to a slim strip (icon in its header; click the strip to bring
  it back).
- The edge between the squad table and the player panel can be dragged to resize them
  (double-click resets); the width is remembered.
- Squad table columns sort on click (#, Pos, Name, Age, Ovr): first click biggest-first for
  ratings/age and lowest-first for number/name/position, second reverses, third restores
  the squad order; remembered between clubs. Your pinned player stays on top. The speed
  (Vel) column is gone.
- Your own player is pinned at the top of his club's squad table ("Your player" / "All
  players"), like your club in the club list.
- The player panel only opens when a player is selected (× closes it), so the squad table
  uses the full width otherwise.

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
