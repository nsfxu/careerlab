# Editing an existing BAL career — what is and isn't possible

Living record. Every claim is tagged with how it is known:
**[game]** verified in game by the harness, **[file]** proven from the save bytes,
**[old]** carried over from the August/October sessions, not yet re-verified.

## The model in one paragraph

A career refers to players by `(u32 handle, u32 playerID)`. The handle's low 16 bits are an
index into the **player registry**, a zlib-compressed table near the end of the save with
one 156-byte record per index. **The record decides who the player is and what he is like**
(position, abilities, style, age, nationality, club, contract). The database supplies only
the name and the face. The playerID written next to a handle is ignored. **[game]+[file]**

## What works

| Edit | Status |
|---|---|
| Move any player who has a record into any club (release + add) | **works** [game] |
| Release a player | **works**, line-up unaffected [game] |
| Add a player the career has a record for but no squad reference (2,864 in slot 1) | **works** — use his record index as the handle [game] |
| **Add a player added to the database after the career began** (1,881 in slot 1) | **works** — append a registry record [game] |
| New player with his real profile (position, rating, style, age, nationality) | **works** — copy the record a *younger career* (ML00000000) got from the game, keep the club context of a teammate, age += season gap [game] |
| New players survive a simulated match, the game's autosave and a transfer window | **works** — the AI even transferred one of them [game] |
| Whole-league sync from an option file | works [old] |

## Hard limits found

- Handle index past the registry count → **the game crashes loading the career.** [game]
- Handle index of an existing record → that record's player, whatever playerID you write. [game]
- Registry capacity: 30,001 records (slot 1 uses 27,426) → ~2,575 new players max. [file]
- A new player's *abilities* can only come from a record the game wrote: a donor career
  created with a database that contains him. Players in neither career's database cannot
  be given a correct profile yet (the 32-byte ability block is not decoded). [file]

## Record layout (156 bytes) — decoded so far

| Offset | Field | Evidence |
|---|---|---|
| 0x00–0x1F | ability/position/style block; age = byte 0x12 bits 2–7 | E05, E07 [game] |
| 0x20 | handle (tag<<16 \| own index) | all 27,423 records [file] |
| 0x24 | playerID | [file] |
| 0x28–0x63 | 15 competition registrations (u16 id, u16 flags) | identical across a club [file] |
| 0x74 | per-player value (market value / salary?) | [file] |
| 0x7C / 0x80 | loan club / current club, `teamID<<14 \| …` (`0x00448078` = Cruzeiro) | [file] |
| 0x84 / 0x88 | contract end / joined, packed `day<<24 \| month<<16 \| year` | [file] |
| 0x90 | nationality (u16; 146 Brazil, 92 Tunisia) | E07 [game] |

Section framing: directory `?,1,3,COUNT,clubs,CONTAINER SIZE,TAIL SIZE,0` 0x24 bytes before
marker `20110912`; chunks of 256 KB, each `{BE usize, BE csize, BE next-offset}` + zlib.

## Squads

- The squad length is stored three times (pairs, shirts, count @+0x2DA); all must agree. [old]
- ~~A club cannot exceed the squad length it started with~~ **DISPROVEN (E08).** Cruzeiro
  started at 28 and was taken to 32 and 35: every player listed with name and rating, a
  match simulated, and the game's autosave kept all 35. The only limit is the block's 40
  slots. The old blank 34th man at Arsenal must have had another cause. [game]

## Player attributes — SOLVED (E09)

Abilities live in the registry record's first 32 bytes as 6-bit fields holding value−40,
packed five per u32 (map in `engine/fl26/attributes.py`, solved from 8 players' in-game
pages). Writing them works and the game recomputes the overall: Leo Aragão's GK values
set to 50/60/70/55 showed exactly, overall 80 → 60. [game]

## Created character — SOLVED (E10)

He is not edited through registry record 0 (that is a mirror; editing it changed
nothing). The save holds his full player record in the game's runtime layout — the same
struct the Cheat Engine table describes (ID +0x30, name +0x38, all 125 CT fields).
Velocidade 93→99, Finalização 78→95 and the Toque duplo skill all appeared; overall
86→88. Map in `engine/fl26/created.py`. [game]

## Manager — SOLVED (E11, E12)

A per-club manager table: 0x258-byte records at 0x133A30 (BL0), one per club block,
`+0 club index, +4 coach ID, +8 name`, rest probably tactics. 730/730 consistent. The
screen reads this name — `block+0x144` mirrors the coach ID only. Swapping Cruzeiro's and
Arsenal's records made Cruzeiro show "Mikel Arteta". [game] E12 writes an option-file
coach (Tite) by ID + name; verified in the rollover run below.

**Tactics DO travel with the manager (E16)** — E14's "no" was a flawed test: in FL26's data
Amorim uses the same 4-3-3 shape as Cruzeiro. Swapping in Oliver Glasner (Crystal Palace)
turned Cruzeiro into his 5-3-1-1 with three centre-backs; the AI re-picked the XI (Giu to CF).

Manager record layout (0x258): `+0 club index, +4 coach ID, +8 name`, then **three formation
presets at +0x40, +0xE0, +0x180** (0xA0 each, same layout as the option file's game plan:
11 position codes + 11 coordinate pairs per phase, three phases 0x21 apart, tactical bytes
after). Position codes: 0 GK, 1 CB, 2 LB, 3 RB, 4 DMF, 5 CMF, 6 LMF, 7 RMF, 8 AMF, 9 LWF,
10 RWF, 11 SS, 12 CF. So a manager change can bring his tactics, or keep the club's by
writing only ID + name (E12), and a formation can be written on its own.

Not the live formation (E15): the two presets inside the club squad block (+0x314, +0x3B4).
Copying Palace's there changed nothing on screen. Also found: a pool of 669 coach records
(same 0x258 layout) around 0x190000 in BL0 — likely every coach incl. unemployed ones,
the natural source for "hire this manager". [game]

## Season rollover — SURVIVES (E13)

The test career was simulated from August 2030 into the 2031 pre-season (~30 matches, a
transfer window, national-team call-ups, season end) with every edit in place. After the
game's own saves:
- all three new players still at Cruzeiro, aged by one year (24→25, 33→34)
- Cruzeiro's 35/36-man squad intact and consistent
- Tite (option-file coach written in E12) still Cruzeiro's manager; Arsenal still has
  the swapped-in Leonardo Jardim
- Giu keeps Velocidade 99, Finalização 95, Toque duplo; aged 22→23
- Leo Aragão's edited GK values kept and *developed* (+1 each) — the game treats edited
  values as his real ones [game]

**Game-made defect found:** at rollover the game itself listed 11 players twice in their
own club (same handle twice; Chilean/Colombian clubs nobody edited). The app must not
treat pre-existing duplicates as its own errors, and can offer a "repair" that removes
the second copy. Impact in game unknown.

## Still open

- Skills / playing style / positions inside the registry block (abilities done).
- Tactical sliders inside a preset (attacking style, build-up, line, compactness) — offsets
  known from the option file, not yet verified in a career.

## Save safety

- Pure-Python decrypt/encrypt, byte-identical round trip on all saves. [file]
- Registry repack round-trips (game's zlib output differs; any valid stream loads). [game]
- Validator: zero errors on every healthy save, flags the 384 duplicates in the damaged
  August snapshot. [file]
- Slot 1 (BL00000000) is the test bed; slot 2 is parked in `_archive\PARKED-user-career`.

## Experiments log

| id | change | result |
|---|---|---|
| E01 | 3 unknown players, indices 0x7001-0x7003 | crash on load |
| E01v0 | 1 unknown player, `E5F2:7001` | crash on load |
| E02 | unknown player, free in-range `E5F2:4A41` | loads; slot blank |
| E02ctl | release Jonathan Jesus only | clean |
| E03 | Sahnoune (own tag-0 handle) + 2 unknown with in-range indices | Sahnoune ok; others = Melikov, Venuti |
| P1 | 12 orphan indices | 12 real players, each consistent with registry order |
| E04 | Rhuan Gabriel, new record cloned from a pool record | **listed at Cruzeiro, real face** |
| E05 | 3 new players, same template | all MLG 76 Italian age 24 → block decides profile |
| E06 | donor (ML) block + teammate record | right position/rating; nationality wrong |
| E07 | donor record + teammate club context + age shift | **fully correct**; survives sim match + autosave; AI transferred one |
| E08 | Cruzeiro 27 → 32 → 35 with existing records | all listed; sim match; autosave keeps 35 |
| E09 | registry abilities: Giu (record 0) speed/finishing; Leo GK four values | Leo exact; Giu unchanged (record 0 is a mirror) |
| E10 | Giu's own save record (CT layout): speed 99, finishing 95, Double Touch | all shown; overall 86→88 |
| E11 | swap manager records Cruzeiro ↔ Arsenal | Cruzeiro shows Mikel Arteta |
| E12 | Cruzeiro manager := Tite (option-file coach) | shown; survives rollover |
| E14 | full manager swap Cruzeiro ↔ Man United (Amorim) | stays 4-3-3 — but Amorim's data is 4-3-3 too: inconclusive |
| E15 | Palace's presets into Cruzeiro's *club block* | no change: club-block presets are not the live formation |
| E16 | full manager swap Cruzeiro ↔ Crystal Palace (Glasner) | **Cruzeiro becomes 5-3-1-1, three CBs** |
| E13 | ~30 skipped matches Aug 2030 → Jan 2031 | all edits survive; game adds 11 duplicates on its own |
