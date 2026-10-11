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
