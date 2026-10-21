# Roster workbook

`data/squadofsunrisers.xlsx` is the **only** source of truth for who belongs to
the Sunrisers family. The application reads it at startup and during each
scheduled cycle; nothing in this repository writes to it.

## What it contains

Four franchises, 90 roster rows, 88 unique people:

| Team | League | Rows |
|---|---|---:|
| Sunrisers Hyderabad | IPL | 30 |
| Sunrisers Eastern Cape | SA20 | 20 |
| Sunrisers Leeds Men | The Hundred Men | 20 |
| Sunrisers Leeds Women | The Hundred Women | 20 |

A few people appear under more than one franchise (for example Mitch Marsh and
Brydon Carse). The matcher labels every franchise row, so one article can carry
both labels without duplicating the alert.

The workbook also contains head coaches and is where ownership/management names
are represented where applicable. Player and coach names that are not in this
workbook are not matched by the roster matcher; a small set of ownership names
is tracked separately in `our_teams/players.py`.

## Columns

| Column | Required | Purpose |
|---|---|---|
| `Team` | yes | One of the four franchise names. Must map to a known team. |
| `Player` | yes | Person’s name as it should appear in alerts. |
| `Role` | yes | Role text such as batter, bowler, captain, head coach. |
| `Country` | yes | Country the person represents. |
| `Notes` | no | Extra text; “captain” in role or notes sets the captain flag. |

The loader is strict: an unknown team, a missing team/name, or a duplicate
person in the same team produces a `RosterError` with a row number. A blank row
is ignored. A person may appear once per team.

## Editing rules

1. Edit the workbook directly; this is a deliberate manual step.
2. Keep the header row and the required column names.
3. Save as `.xlsx` at `data/squadofsunrisers.xlsx`.
4. Run the read-only validator.
5. Run the tests.

```bash
python -m handy_tools.validate_roster
python -m pytest -q
```

The validator confirms the workbook loads, prints the team/row counts, and
checks that every entry in `PLAYER_ALIASES` still points at a rostered person.
It never saves the file. CI runs the same command.

## How aliases work

Aliases live in `our_teams/players.py`. Full roster names match automatically.
The alias table adds conservative short forms such as `Klaasen`, `Cummins`,
`Abhishek`, and `Crawley`, plus context-required surnames that could otherwise
create false positives. If you add a person, add a roster row first; then add
any alias you need. An alias for a name that is not in the workbook fails the
validator.

## Why there is no refresh script

The old `handy_tools/refresh_player_list.py` rewrote the workbook. It was
removed so the roster has one owner and cannot be overwritten by a job. The
root-level duplicate workbook was also removed. Keep only this canonical file.
