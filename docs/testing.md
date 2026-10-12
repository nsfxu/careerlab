# Testing and verification

Three levels. A save-format change is only "done" after the third.

## 1. Unit tests (offline)

```
cd engine && python -m pytest -q
```

Some tests read the golden saves in `testdata/` (not in git: `BL00000000.golden`,
`EDIT00000000.golden`) and skip when they are missing. Add a test for every bug fixed,
especially silent ones (e.g. `test_no_field_name_collisions`: a duplicate dict key once
overwrote the Heading ability).

## 2. The app, driven over CDP

Start the app with a debugging port and evaluate JavaScript in the renderer:

```
cd app && npx electron . --remote-debugging-port=9333
python harness/ui.py "document.querySelector('#squad-name').textContent"
python harness/ui.py "(async()=>{ setSideTab('leagues'); document.querySelector('.league-row.mine').click(); document.querySelector('.league-sync-big').click(); ... })()"
python harness/winshot.py CareerLab out.png      # screenshot (exact window title match)
```

- Only one app may own port 9333: stop old instances first, or CDP answers from a stale one.
- `window.confirm` blocks; override it in the test: `window.confirm = () => true`.
- The window can open partly off-screen: move it with `SetWindowPos` before a screenshot.
- The engine child keeps old code until the app restarts; reloading the page only reloads the UI.
- The packaged app accepts the same flag: `dist\win-unpacked\CareerLab.exe --remote-debugging-port=9333`.

## 3. In game (`harness/game.py`)

```
python harness/game.py launch        # snapshots the save folder, starts Sider + FL_2026.exe
python harness/game.py shot s1 640   # screenshot to harness/shots/s1.png
python harness/game.py keys right wait0.7 enter
python harness/game.py waitfor title 120 | until down balmenu_cont | advance 3
python harness/game.py quit          # also checks the user's save is unchanged
```

- Input is DirectInput scan codes via SendInput; the game needs the foreground.
- **Never use blind fixed waits for navigation**: keys are dropped during loads. Look at
  a screenshot (or `waitfor`/`until` against references in `harness/shots/ref/`) before
  each Enter that matters. References go stale when the game's menus change; refresh with
  `game.py ref <name>` while the screen shows the state.
- **Load the test career explicitly**: Rumo ao Estrelato > Carregar > confirm slot 1 on
  screen. "Continuar" loads the most recent save, which may be the user's (slot 2).
- `advance N` skips matches and verifies "Pular partida" on screen each time: playing a match
  live by accident has happened three times.

### Menu map (Portuguese)

- Main menu (vertical): Football Life 2026 / Liga Master / **Rumo ao Estrelato** / Controles de
  áudio / Configurações / about. Enter after the intro.
- BAL menu: Continuar / Novo / Carregar.
- Career hub tabs: Avançar o tempo / Menu do jogador / Negociação / [crest] / Informações do
  time (Calendário, Plano de jogo, …) / Base de dados / Sistema. The tab cursor only appears
  after pressing Up.
- Base de dados > Info. do time > league list (Brasileirão Série A is ~20 downs) > club >
  Lista de jogadores (player cards with face, style, age, nationality).
- Esc on the hub asks "return to main menu?".

## Test career state

Slot 1 (`BL00000000`) holds a synced Cruzeiro + Brasileirão and Arsenal sync. Backups of every
step are in `...\2026\backup\BL00000000\`; `testdata/*.golden` are the originals.
