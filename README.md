# CareerLab

Editor for a **Football Life 2026 Become a Legend career already in progress**.

- `FEATURES.md` — what the app will do (agreed feature list)
- `LIMITS.md` — what is possible and how each claim was verified in game (E01–E16)
- `engine/fl26/` — save format engine: crypto, career squads, player registry,
  attributes, created character, managers/tactics, validator, safe writes
- `engine/tests/` — offline tests (`python -m pytest -q` from `engine/`)
- `harness/game.py` — drives the game for in-game verification (launch, navigate, screenshot)
- `lab/` — the experiment scripts behind LIMITS.md
- `testdata/` (not in git) — golden copies of the untouched test saves

## Run from source

```
cd app && npm install && npx electron .
```

The engine runs as a child process (`python -m fl26.rpc`, needs numpy).

## Build the installer

```
python build.py
```

Runs the tests, freezes the engine with PyInstaller (`build/dist/careerlab-engine/`) and
packages the app with electron-builder → `dist/CareerLab-Setup-<version>.exe` (per-user
install, no admin, no Python/Node needed on the target PC). The installer is unsigned, so
Windows SmartScreen asks "More info → Run anyway" the first time.

If electron-builder fails with *Cannot create symbolic link* (winCodeSign archive, macOS
files need symlink rights), extract the archive once by hand:
`7za x <cache>\winCodeSign\<n>.7z -o<cache>\winCodeSign\winCodeSign-2.6.0`
(`<cache>` = `%LOCALAPPDATA%\electron-builder\Cache`).

## First run on another PC

Settings live in `%LOCALAPPDATA%\CareerLab\config.json`. The app finds the game folder
(the one with `FL_2026.exe`) and the saves folder itself, or asks. The player database is
read from the dump that the read-only Sider module `DBDump.lua` writes to
`SiderAddons\dbdump`; if it is missing, the setup screen installs the module (adds one
`lua.module` line to `sider.ini`, keeping a backup) and asks to start the game once.
