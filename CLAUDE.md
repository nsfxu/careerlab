# CareerLab: notes for AI contributors

CareerLab edits a **Football Life 2026 (PES 2021 engine) Become a Legend career that is
already in progress**: squads, transfers, ratings, the user's own player, managers, real-world
squad sync from efootballdb.com. Windows only. Electron UI + Python engine.

## Golden rules (do not break)

1. **Never write a save while the game runs.** The game holds the career in memory and
   overwrites the file. Every write goes through `engine/fl26/safewrite.py`, which refuses
   while `FL_2026.exe` is running, backs up first, and verifies by re-decrypting.
2. **Every save edit is backed up** into `...\2026\backup\<slot>\<timestamp>-<label>` (the
   `backup` folder beside the game's `save` folder), with a `.json` description beside it.
   Do not add another write path.
3. **The user's real career is `BL00000001` (slot 2). Never touch it.** Slot 1
   (`BL00000000`) is the test career. Before loading anything in game, confirm slot 1 on
   screen (`Carregar` list); "Continuar" loads the most recent save, which may be the user's.
4. **Staged edits, one apply.** The UI stages edits; `Session.apply()` replays them on a
   fresh load, refuses if the validator finds a *new* problem, then writes. Keep it that way.
5. **The created character (ID ≥ 0x80000000) is never moved by squad tools**, and keeps his
   own shirt number in renumbers.
6. **The GitHub repo `nsfxu/careerlab` is private.** Do not make it public or publish
   anything from it without the user asking.
7. **Claims about the save format need in-game proof.** "The file changed" is not "the game
   shows it". `LIMITS.md` marks each finding `[game]` or `[file]`; keep doing that.
8. **UI tests go through CDP** (`harness/ui.py`), never by clicking on the user's screen.
   The user often works on monitor 3; monitors 1 and 2 are free for the game and app.

## Map

| Path | What |
|---|---|
| `engine/fl26/` | Save-format engine and the JSON-lines RPC server the app talks to |
| `engine/tests/test_engine.py` | Offline tests (`python -m pytest -q` in `engine/`); some need the test saves in `testdata/` |
| `app/` | Electron shell: `main.js` (spawns the engine), `preload.js`, `renderer/` (plain JS, no build step) |
| `harness/` | Drives the game and the app for verification: `game.py`, `ui.py` (CDP), `winshot.py` |
| `lab/` | One script per experiment (E01–E22) behind `LIMITS.md` |
| `LIMITS.md` | What is possible, how it was proven, experiment log |
| `FEATURES.md` | Agreed feature list, status, next steps |
| `docs/` | Architecture, save format, testing, data sources, build/release, lessons |
| `testdata/` (not in git) | Golden copies of the untouched test saves |

## Commands

```
cd engine && python -m pytest -q                    # tests
cd app && npx electron . --remote-debugging-port=9333   # run the app (dev), CDP on 9333
python harness/ui.py "<js expression>"              # evaluate JS in the running app
python harness/game.py launch | shot | keys ... | quit   # drive the game
python build.py                                     # tests -> frozen engine -> installer in dist/
```

## Read next

- [docs/architecture.md](docs/architecture.md): how the pieces fit, the RPC protocol, adding a feature
- [docs/save-format.md](docs/save-format.md): the career save, the registry, managers, option file
- [docs/testing.md](docs/testing.md): unit, UI (CDP) and in-game verification, menu map
- [docs/data-sources.md](docs/data-sources.md): efootballdb, pesmaster, the Sider database dump
- [docs/build-and-release.md](docs/build-and-release.md): installer, config, known build issues
- [docs/lessons.md](docs/lessons.md): dead ends and expensive mistakes; read before experimenting

## Style

Match the surrounding code: small modules, docstrings that say *why*, no build tooling in the
renderer, Portuguese game terms in the UI (positions ZC/VOL/PTE…, ability names) because they
must match what the user sees in FL26. Keep answers to the user short: result first.
