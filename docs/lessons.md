# Lessons: dead ends and expensive mistakes

Read before experimenting. Each of these cost at least one full test cycle.

## Save format

- **The option file / CPK database does not change a running career's squads.** A livecpk
  override of `PlayerAssignment.bin` was served by Sider and had no effect; editing
  `EDIT00000000` only changes names and *new* careers. Careers snapshot their roster at creation.
- **Never keep a player's handle and change only the playerID.** The handle is what history,
  contracts and the registry key off: the slot renders blank. **Never invent a handle**
  (nothing resolves it → blank, and past the record count → crash on load).
- **A `(handle, pid)` pair is replicated many times in the save**; edit squads through
  `career.py`, not by patching one occurrence.
- **Registry record 0 is a mirror of the created character**; his real data is the runtime
  struct (`created.py`).
- **`block+0x144` mirrors the coach ID but is not what the screen shows**; the manager record is.
- **The club squad block's formation presets (`+0x314/+0x3B4`) are not live**; the manager
  record's are.
- **`manager+0x251` is not the captain** (`+0x24E` is). Set-piece taker bytes do nothing in
  BAL: the AI re-picks by rating.
- **Option-file records for IDs not in the base database are ignored** ("Jogadores", generic
  face). Use a spare database ID instead.
- **A duplicate key in a field dict silently overwrites** (`heading` the ability vs the skill,
  twice). The skill is `heading_skill`; a test guards it.
- **Releases shift squad slots**: the manager's lineup and captain bytes hold slots and must be
  remapped (`managers.slot_removed/slot_added`), or the armband moves to the wrong player.
- **A squad emptied by releases has no teammate to copy club context from**: take donors
  before applying (`donor` snapshot in `_apply_ops`).
- **An unmapped playing style used to inherit the template's** (a striker got "Goleiro
  ofensivo"). Unknown styles now map to none.

## Experiments

- **Choose a test subject whose value differs.** E14 "proved" tactics don't travel with the
  manager because the swapped-in coach also played 4-3-3; E16 with a 5-3-1-1 coach proved they do.
- **"The file changed" is not "the game shows it."** Every claim needs a screenshot from the game.
- **Diff technique that works**: save, advance one day, save, decrypt both, diff. Don't play
  matches in between.

## Harness

- **Blind key macros loaded the user's career once.** Confirm on screen before Enter; load slot
  1 via Carregar.
- **The advance loop played matches live three times**: the "down" to *Pular partida* gets
  dropped. Verify the popup on screen every match; national-team hubs are yellow; a
  single-option "Próximo" popup exists.
- **The game window opens at random positions**, and the taskbar overlapped captures: park it
  at (0,0) before each capture.
- **Window capture by title substring once grabbed the user's browser**: match exactly.
- **Copying files while the game runs gives stale saves**: the game writes on exit.

## Tooling

- Windows pipes default to the ANSI code page: force UTF-8 on the engine's stdio.
- Bash heredocs with nested quotes/backticks break in this environment: write patch scripts
  to a file and run them with Python.
- `button { display: inline-flex }` overrides the `hidden` attribute; CSS keeps
  `[hidden] { display: none !important }`.
- Two Electron instances on CDP port 9333 → `ui.py` talks to the stale one.
