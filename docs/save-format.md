# The career save (Become a Legend)

Summary for working on the engine. Evidence and the full experiment log: [LIMITS.md](../LIMITS.md).
Saves live in `Documents\KONAMI\eFootball PES 2021 SEASON UPDATE\2026\save\` (`BL0000000n`
= BAL slot n+1, `EDIT00000000` = option file, shared by every career).

## Encryption

pesXdecrypter scheme (PES 2021 master key), ported to pure Python in `crypto.py`. Always check
`Save.verify_roundtrip` style equality after writing (safewrite does: it re-decrypts the
written file and compares the payload).

## The model in one paragraph

A career refers to players by `(u32 handle, u32 playerID)` pairs. The handle's low 16 bits
index the **player registry**. The registry record decides who the player is in this career
(position, abilities, style, age, nationality, club, contract). FL26's database only supplies
the name and the face. The playerID next to a handle is ignored for the profile.

## Club squad table (`career.py`)

Starts at `0x19C`, one `0x690`-byte block per club (730 in slot 1), 40 slots each:
pairs, then a u16 shirt-number array at `+0x14E`, the squad count at `+0x2DA`, own index at
`+0x140`, `+0x144` mirrors the coach ID. The three length fields must agree. The cap is the
40 slots (the old "starting size" limit was wrong). Which block is which club is not stored
plainly: `database.identify_blocks` votes using registry club fields and database assignments.
National teams have no fixed ID range (Brazil 45, Ghana 1058, Serbia 1550): the database
team record flags them (`+0x47` bit 7, 142 teams) and holds their Portuguese name at
`+0x37C`. Their squad blocks hold the game's own call-ups (re-picked before every
international window), so `database.identify_nationals` names them by the one nationality
their members share (registry `+0x90`), matched to the national team most of whose database
players have it. Call-ups/drops (`callup`/`drop` edits) change only the squad list, never the
record's club context.

## Player registry (`registry.py`, `attributes.py`)

zlib section near the end; marker `20110912` (big-endian), directory 0x24 bytes before it:
`?, 1, 3 (BAL), RECORD COUNT, clubs, CONTAINER SIZE, TAIL SIZE, 0`. 256 KB chunks
`{BE usize, BE csize, BE next}`. Capacity 30,001 records (about 2,500 free in slot 1).

Record (156 bytes): `0x00–0x1F` profile bits (abilities as 6-bit value−40, 13 position
ratings 0/1/2, 41 skill flags, playing style 5 bits at bit 166 in FL26 numbering, age at bit
146, form, weak foot); `0x20` handle; `0x24` player ID; `0x28–0x63` competition registrations;
`0x7C/0x80` loan/current club (`teamID<<14`); `0x84/0x88` contract/joined dates; `0x90`
nationality. A handle past the record count **crashes the game** on load.

Adding a player the career never knew = append a record (template: a teammate's record for the
club context) and add `(handle, pid)` to the squad. Players FL26 itself lacks need a **spare
database ID** (an obscure clubless player whose record is rewritten and who is renamed in the
option file; the game ignores option-file records for IDs not in its base database).

## Created character (`created.py`)

The user's player (ID `0x800000BA`, "Giu") has a full struct in the runtime layout of the
user's Cheat Engine table (ID `+0x30`, name `+0x38`, 125 fields incl. skills). Located by
ID + valid name text. Registry record 0 is only a mirror: editing it does nothing.

## Managers and tactics (`managers.py`)

One `0x258`-byte record per club block (base found by pattern, e.g. `0x133A30`): `+0` block
index, `+4` coach ID, `+8` name. Three formation/tactics presets at `+0x40/+0xE0/+0x180`
(option-file game plan layout), the stored lineup at `+0x220` (squad slots, `0xFF` padded),
role bytes `+0x248..+0x251`. **Captain = `+0x24E`** (worn only when he starts). Set-piece
taker bytes have no effect in BAL (the AI picks by rating). Swapping records moves the
manager *with* his tactics; writing ID + name keeps the club's tactics.

## Option file (`editfile.py`)

Player table: count u16 at `0x60`, records at `0x7C`, stride `0x138`. A record equals the
database record minus its 14-byte header; appearance block (72 B) at `+0xF0`; name-edited flag
`+0x1F` bit 7; nationality u16 at `+0x08`. Editing it changes new careers and names, **not**
squads of a running career.

## Game behaviour to expect

- Retired players come back as 16-year-old "regens" with the same name and ID.
- At season rollover the game itself lists a few players twice in their club; not our bug.
- Edited values are treated as real: they develop over seasons and survive the game's saves.
