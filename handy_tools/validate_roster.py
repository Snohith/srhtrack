"""Read-only roster validator.

Checks the Excel workbook and confirms alias entries still point at rostered
people.  It never writes the workbook.

    python -m handy_tools.validate_roster
"""
from __future__ import annotations

import argparse
import sys

from helpers.config import load_env
from our_teams.players import (
    PLAYER_ALIASES,
    RosterError,
    load_master_roster_from_excel,
)


def validate(path=None):
    load_env()
    roster = load_master_roster_from_excel(path)
    names = []
    rows = 0
    for team_key, team in roster.items():
        rows += len(team["players"])
        names.extend(player["name"] for player in team["players"])
        print(f"{team['franchise_name']}: {len(team['players'])} row(s)")
    unique_names = set(names)
    unknown_aliases = sorted(set(PLAYER_ALIASES) - unique_names)
    if unknown_aliases:
        raise RosterError(
            "Alias entries reference people who are not in the roster: "
            + ", ".join(unknown_aliases)
        )
    print(f"Roster OK: {len(roster)} teams, {rows} rows, {len(unique_names)} unique people.")
    return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate the Sunrisers roster workbook (read-only).")
    parser.add_argument("path", nargs="?", help="optional workbook path")
    args = parser.parse_args(argv)
    try:
        validate(args.path)
        return 0
    except RosterError as exc:
        print(f"Roster error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
