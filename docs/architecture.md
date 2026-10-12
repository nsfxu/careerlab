# Architecture

```
┌──────────────── Electron (app/) ────────────────┐      ┌────────── Python engine (engine/fl26) ──────────┐
│ renderer/app.js  ── window.cl.call(method, …) ──┼─IPC─▶│ rpc.py   JSON lines on stdin/stdout             │
│ (UI, no save knowledge)                         │      │   └─ Session (session.py): views, staging, apply│
│ main.js  spawns the engine, routes "engine" IPC │◀─────┤        ├─ Career / Registry / Managers / created │
│ preload.js exposes call / reveal / pickFolder   │      │        ├─ efdb (squads), profiles (new players) │
└─────────────────────────────────────────────────┘      │        └─ safewrite (the only write path)       │
                                                         └──────────────────────────────────────────────────┘
```

- **The renderer knows nothing about the save format.** Everything comes from engine calls.
- **One long-lived engine process** per app window. Dev: `python -m fl26.rpc` (cwd `engine/`).
  Packaged: `resources/engine/careerlab-engine.exe` (PyInstaller onedir, *console* build:
  the protocol is stdio; Electron hides the window).
- **Protocol** (`rpc.py`): `{"id", "method", "params"}` in, `{"id", "ok", "result"|"error"}`
  out, one JSON object per line, UTF-8 both ways (stdio is reconfigured; Windows pipes
  default to the ANSI code page). `print()` inside the engine goes to stderr so it can
  never corrupt the pipe. Methods are the public methods of `rpc.Server`.

## Engine modules

| Module | Role |
|---|---|
| `crypto.py` | `Save.load/encrypt`: pesXdecrypter ported to Python (MT19937 keystream, numpy). Round trip is byte-identical. |
| `career.py` | The club squad table (40 slots per club block), handle/ID pairs, `release`, `add`, `club_of`, namespaces |
| `registry.py` | The player registry (zlib section, 156-byte records); `append`, `commit` recompresses and fixes the directory |
| `attributes.py` | Bit map of a registry record: abilities, positions, skills, style, age, form, weak foot; efootballdb style mapping |
| `created.py` | The user's created player (a full runtime-layout struct, 125 fields; registry record 0 is only a mirror) |
| `managers.py` | Per-club manager records: coach, tactics presets, stored lineup, captain; slot remapping on release/add |
| `database.py` | FL26's base database from the Sider dump (names, teams, assignments) + option-file names; club identification |
| `editfile.py` | `EDIT00000000` (option file) player table: rename a spare player |
| `profiles.py` | Build a registry record from efootballdb data; spare-ID picking; face donors |
| `efdb.py` | efootballdb client (team squads, players, league list), cached in `%LOCALAPPDATA%\CareerLab\efdb-cache` |
| `pesmaster.py` | pesmaster.com squad page parser, the second opinion in club sync |
| `i18n.py` | Engine text in English and pt-BR (`tr()`), set by the `set_language` RPC |
| `validate.py` | Consistency checks; `new_problems(before, after)` is the apply gate |
| `safewrite.py` | Game-running check, backup (+ `.json` description), write, verify, restore |
| `config.py` | Game folder, saves folder, dump location (`%LOCALAPPDATA%\CareerLab\config.json`), DBDump module install |
| `session.py` | Everything the UI uses: views, sync plans (club and league), staging, `describe`, `preview`, `apply`, backups |

## Edit lifecycle

1. The UI builds an op, e.g. `{"op": "move", "pid", "from", "to", "label", "source"?}`, and
   calls `stage` (or `stage_many` for a league). `_check` validates it (40-player cap, the
   created character, records that must exist).
2. `preview` replays all staged ops on a scratch load and returns validator differences.
3. `apply` replays them on a fresh load, refuses on new problems, writes the option file first
   if spare IDs were lent, then the career; both through `safewrite` with a description from
   `describe()`. `spares.json` is updated only after the write succeeds.

Op kinds: `move release add new attr created manager_swap manager_set shirt renumber captain`.
`label` (human text) and `source` ("Cruzeiro EC sync") are kept with the op and end up in the
backup description; keys in `Session.UI_ONLY` are stripped.

Runs of `move` ops are applied as all departures, then all arrivals (`_expand_moves`), so a full
squad can let a player go before receiving one. Releases and adds remap the manager's
squad-slot references (lineup, captain).

## Adding a feature

1. Prove the mechanism in game first (a `lab/eNN_*.py` script + an entry in `LIMITS.md`).
2. Engine: the logic in a module, an op kind in `Session._check` + `_apply_ops` if it edits,
   a method in `rpc.Server` if the UI needs it. A unit test.
3. UI: call it from `app.js`; give every staged op a `label`.
4. Verify through the app over CDP, then in game with the harness.
5. Update `FEATURES.md` (status) and `LIMITS.md` (evidence).

## Files outside the repo

- `%LOCALAPPDATA%\CareerLab\config.json`: game/saves folders
- `%LOCALAPPDATA%\CareerLab\spares.json`: `{real eFootball ID: spare FL26 ID}` for players FL26 lacks (install-wide, like the option file)
- `%LOCALAPPDATA%\CareerLab\efdb-cache\`: efootballdb responses (teams 24 h, players 7 days, leagues 7 days)
- `<game>\SiderAddons\dbdump\`: the database dump the engine reads (newest `<table>.copyN.raw`)
