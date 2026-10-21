"""Sunrisers roster and story matching.

The Excel workbook is the single source of truth for who is attached to which
franchise.  Nothing in this module writes the workbook, and a player listed
under two teams (Mitch Marsh, Brydon Carse) is matched to both franchises.
"""
from __future__ import annotations

import os
import re
import unicodedata

import openpyxl

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_ROSTER_PATH = os.path.join(PROJECT_ROOT, "data", "squadofsunrisers.xlsx")
ROSTER_PATH = os.environ.get("SUNRISERS_ROSTER_PATH", DEFAULT_ROSTER_PATH)

REQUIRED_COLUMNS = ("Team", "Player", "Role", "Country")


class RosterError(RuntimeError):
    """The roster workbook is missing or cannot be used."""


def _clean(value):
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() in ("nan", "none") else text


def _franchise_for_team(raw_team):
    team = _clean(raw_team).lower()
    if "leeds" in team and "women" in team:
        return "Leeds_Women", "Sunrisers Leeds Women", "The Hundred Women"
    if "leeds" in team:
        return "Leeds_Men", "Sunrisers Leeds Men", "The Hundred"
    if "eastern cape" in team:
        return "SEC", "Sunrisers Eastern Cape", "SA20"
    if "hyderabad" in team or team == "srh":
        return "SRH", "Sunrisers Hyderabad", "IPL"
    raise RosterError(f"Unknown team {raw_team!r} in the roster workbook.")


def load_master_roster_from_excel(path=None):
    """Load and validate the workbook.  Read-only; never saves the file."""
    workbook_path = (
        path
        or os.environ.get("SUNRISERS_ROSTER_PATH")
        or DEFAULT_ROSTER_PATH
    )
    if not os.path.exists(workbook_path):
        raise RosterError(
            f"Roster workbook not found: {workbook_path}. "
            "Put data/squadofsunrisers.xlsx back or set SUNRISERS_ROSTER_PATH."
        )
    try:
        workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    except Exception as exc:
        raise RosterError(f"Could not open roster workbook {workbook_path}: {exc}") from exc

    try:
        sheet = workbook.active
        rows = list(sheet.iter_rows(values_only=True))
    finally:
        workbook.close()
    if not rows:
        raise RosterError(f"Roster workbook {workbook_path} is empty.")

    headers = [_clean(cell) for cell in rows[0]]
    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise RosterError(
            f"Roster workbook {workbook_path} is missing column(s): {', '.join(missing)}."
        )
    index = {column: headers.index(column) for column in headers if column}

    roster = {}
    seen = set()
    for line_number, row in enumerate(rows[1:], start=2):
        team = _clean(row[index["Team"]] if index["Team"] < len(row) else "")
        name = _clean(row[index["Player"]] if index["Player"] < len(row) else "")
        if not team and not name:
            continue
        if not team or not name:
            raise RosterError(
                f"Roster workbook {workbook_path}, row {line_number}: "
                "Team and Player are both required."
            )
        team_key, franchise_name, league = _franchise_for_team(team)
        role = _clean(row[index["Role"]] if index.get("Role", 99) < len(row) else "")
        country = _clean(row[index["Country"]] if index.get("Country", 99) < len(row) else "")
        notes_index = index.get("Notes")
        notes = _clean(row[notes_index] if notes_index is not None and notes_index < len(row) else "")
        duplicate_key = (team_key, name.lower())
        if duplicate_key in seen:
            raise RosterError(
                f"Roster workbook {workbook_path}, row {line_number}: "
                f"{name} appears twice for {franchise_name}."
            )
        seen.add(duplicate_key)
        captain = "captain" in role.lower() or "captain" in notes.lower()

        roster.setdefault(
            team_key,
            {"franchise_name": franchise_name, "league": league, "players": []},
        )
        roster[team_key]["players"].append(
            {
                "name": name,
                "role": role,
                "country": country,
                "captain": captain,
                "notes": notes,
            }
        )

    if not roster:
        raise RosterError(f"Roster workbook {workbook_path} contains no players.")
    return roster


ROSTER_LOAD_ERROR = None


def reload_roster(path=None):
    """Reload from the workbook (the sole source of truth), read-only."""
    global PLAYERS_BY_TEAM, ROSTER_PATH, ROSTER_LOAD_ERROR
    ROSTER_PATH = (
        path
        or os.environ.get("SUNRISERS_ROSTER_PATH")
        or DEFAULT_ROSTER_PATH
    )
    try:
        PLAYERS_BY_TEAM = load_master_roster_from_excel(ROSTER_PATH)
        ROSTER_LOAD_ERROR = None
    except RosterError as exc:
        PLAYERS_BY_TEAM = {}
        ROSTER_LOAD_ERROR = exc
    return PLAYERS_BY_TEAM


PLAYERS_BY_TEAM = reload_roster()


def _ensure_roster():
    if ROSTER_LOAD_ERROR is not None:
        raise ROSTER_LOAD_ERROR
    if not PLAYERS_BY_TEAM:
        raise RosterError("The Sunrisers roster is empty.")


def player_entries():
    """Flat roster rows; a player on two teams appears twice."""
    _ensure_roster()
    entries = []
    for team_key, team in PLAYERS_BY_TEAM.items():
        for player in team["players"]:
            entries.append(
                {
                    "name": player["name"],
                    "team_key": team_key,
                    "franchise": team["franchise_name"],
                    "role": player["role"],
                    "country": player["country"],
                    "captain": player["captain"],
                }
            )
    return entries


# Extra name forms.  Franchises are always looked up from the roster, so this
# table cannot drift from the workbook.  Bare surnames are only listed when
# they are distinctive enough to be useful.
PLAYER_ALIASES = {
    "Salil Arora": [r"\bsalil\b"],
    "Heinrich Klaasen": [r"\bklaasen\b"],
    "Pat Cummins": [r"\bcummins\b"],
    "Abhishek Sharma": [r"\babhishek\b(?!\s+(porel|nayar))"],
    "Ishan Kishan": [r"\bishan\b(?!\s+porel)"],
    "Harshal Patel": [r"\bharshal\b"],
    "Liam Livingstone": [r"\blivingstone\b"],
    "Gerald Coetzee": [r"\bcoetzee\b"],
    "Kamindu Mendis": [r"\bkamindu\b"],
    "Dilshan Madhushanka": [r"\b(madhushanka|madushanka)\b"],
    "Jaydev Unadkat": [r"\bunadkat\b"],
    "Nitish Kumar Reddy": [r"\bnitish reddy\b"],
    "R Smaran": [r"\b(r smaran|smaran ravichandran|smaran)\b"],
    "RS Ambrish": [r"\b(rs ambrish|r\.s\. ambrish|ambrish)\b"],
    "Daniel Vettori": [r"\bvettori\b"],
    "Dan Vettori": [r"\bvettori\b"],
    "Quinton De Kock": [r"\b(quinton de kock|de kock|de-kock)\b"],
    "Tristan Stubbs": [r"\bstubbs\b"],
    "Marco Jansen": [r"\bjansen\b"],
    "Anrich Nortje": [r"\bnortje\b"],
    "Matthew Breetzke": [r"\bbreetzke\b"],
    "Jordan Hermann": [r"\bhermann\b"],
    "Rishad Hossain": [r"\brishad\b"],
    "Lutho Sipamla": [r"\bsipamla\b"],
    "Senuran Muthusamy": [r"\bmuthusamy\b"],
    "Patrick Kruger": [r"\bkruger\b"],
    "Mitch Marsh": [r"\b(mitch marsh|mitchell marsh)\b"],
    "Mitch Van Buuren": [r"\b(mitch van buuren|mitchell van buuren|van buuren)\b"],
    "Adrian Birrell": [r"\bbirrell\b"],
    "Lewis Gregory": [r"\blewis gregory\b"],
    "James Coles": [r"\bjames coles\b"],
    "Nandre Burger": [r"\bnandre burger\b"],
    "Craig Overton": [r"\bcraig overton\b"],
    "Zak Crawley": [r"\bcrawley\b"],
    "Harry Brook": [r"\bbrook\b"],
    "Ryan Rickelton": [r"\brickelton\b"],
    "Dan Lawrence": [r"\bdan lawrence\b"],
    "Brydon Carse": [r"\bcarse\b"],
    "Matthew Potts": [r"\b(matthew potts|matty potts|potts)\b"],
    "Reece Topley": [r"\btopley\b"],
    "Nathan Ellis": [r"\bnathan ellis\b"],
    "Abrar Ahmed": [r"\babrar\b"],
    "Matty Revis": [r"\b(matty revis|matt revis|revis)\b"],
    "Liam Patterson-White": [r"\bpatterson-white\b"],
    "Tom Lawes": [r"\blawes\b"],
    "Tom Alsop": [r"\balsop\b"],
    "Benny Howell": [r"\bhowell\b"],
    "Ed Barnard": [r"\bed barnard\b"],
    "Charlie Allison": [r"\bcharlie allison\b"],
    "Graham Clark": [r"\bgraham clark\b"],
    "James Fuller": [r"\bjames fuller\b"],
    "Dani Gibson": [r"\b(dani gibson|danielle gibson|gibson)\b"],
    "Phoebe Litchfield": [r"\blitchfield\b"],
    "Annabel Sutherland": [r"\bsutherland\b"],
    "Deepti Sharma": [r"\bdeepti\b"],
    "Lauren Winfield-Hill": [r"\b(lauren winfield-hill|winfield-hill|lauren winfield)\b"],
    "Kate Cross": [r"\bkate cross\b"],
    "Jess Jonassen": [r"\bjonassen\b"],
    "Bryony Smith": [r"\bbryony smith\b"],
    "Tilly Kesteven": [r"\bkesteven\b"],
    "Rachel Slater": [r"\bslater\b"],
    "Hannah Baker": [r"\bhannah baker\b"],
    "Darcey Carter": [r"\bdarcey carter\b"],
    "Chloe Skelton": [r"\bskelton\b"],
    "Claudie Cooper": [r"\bclaudie cooper\b"],
}

# Single-word aliases that are also ordinary words or common surnames.
CONTEXT_REQUIRED_ALIASES = {
    "Pat Cummins", "Marco Jansen", "Jordan Hermann", "Annabel Sutherland",
    "Harry Brook", "Matthew Potts", "Benny Howell", "Dani Gibson", "Rachel Slater",
}

TEAM_PATTERNS = [
    {
        "franchise": "Sunrisers Hyderabad",
        "patterns": [r"\bsunrisers hyderabad\b", r"\bsrh\b"],
        "abbreviations": [],
    },
    {
        "franchise": "Sunrisers Eastern Cape",
        "patterns": [r"\bsunrisers eastern cape\b"],
        "abbreviations": [r"\bsec\b"],
    },
    {
        "franchise": "Sunrisers Leeds Men",
        "patterns": [],
        "abbreviations": [],
    },
    {
        "franchise": "Sunrisers Leeds Women",
        "patterns": [],
        "abbreviations": [],
    },
]

LEEDS_PATTERNS = [r"\bsunrisers leeds\b", r"\bnorthern superchargers\b"]

TRACKED_TOPICS = [
    {
        "name": "Kavya Maran",
        "pattern": r"\bkavya maran\b|\bkavya\b",
        "franchise": "Sunrisers Hyderabad",
        "role": "CEO / Owner",
        "kind": "person",
    },
    {
        "name": "Kalanithi Maran",
        "pattern": r"\bkalanithi maran\b",
        "franchise": "Sunrisers Hyderabad",
        "role": "Chairman / Founder",
        "kind": "person",
    },
    {
        "name": "Sun Group",
        "pattern": r"\bsun group\b",
        "franchise": "Sunrisers Hyderabad",
        "role": "Ownership",
        "kind": "topic",
    },
    {
        "name": "Sun TV Network",
        "pattern": r"\bsun tv network\b",
        "franchise": "Sunrisers Hyderabad",
        "role": "Ownership",
        "kind": "topic",
    },
]

SPORTS_TO_IGNORE = [
    "padres trade", "cooper kupp", "coles bay", "baseball", "nfl", "nba", "mlb",
]

CRICKET_CONTEXT = re.compile(
    r"\b(cricket|ipl|sa20|the hundred|t20|odi|test|wicket|batting|bowling|"
    r"squad|auction|retention|series|tournament|match|sunrisers|hyderabad|"
    r"eastern cape|leeds|superchargers|bcci|runs|wickets|signing|signed|"
    r"injury|injured|fitness|coach|coaching|captain|owner|fixture|innings|"
    r"fifty|century|hat-trick|bowler|batter|all-rounder|allrounder|playoff|"
    r"qualifier|debut|ruled out|wpl|wbb|bbl|cpl|psl|ilt20|mlc|county|blast)\b"
)


def _name_pattern(name):
    parts = [part for part in re.split(r"[\s\-]+", name) if part]
    return r"\b" + r"[\s\-]+".join(re.escape(part.lower()) for part in parts) + r"\b"


def _has_cricket_context(text):
    return bool(CRICKET_CONTEXT.search(text))


def find_our_players_in_story(text):
    """Return every roster row / tracked topic mentioned in the text.

    A player attached to two franchises produces two matches.  Team-name hits
    produce one team match per franchise.  No match means the story is not
    relevant to Sunrisers and must be dropped by the collector.
    """
    _ensure_roster()
    lowered = unicodedata.normalize("NFKC", str(text or "")).lower()
    if not lowered.strip():
        return []
    if any(phrase in lowered for phrase in SPORTS_TO_IGNORE) and not _has_cricket_context(lowered):
        return []

    entries = player_entries()
    entries_by_name = {}
    for entry in entries:
        entries_by_name.setdefault(entry["name"], []).append(entry)

    matches = []
    matched = set()

    def add(entry, kind):
        key = (entry["name"], entry["franchise"])
        if key in matched:
            return
        matched.add(key)
        matches.append(
            {
                "player_name": entry["name"],
                "team_key": entry["team_key"],
                "franchise": entry["franchise"],
                "country": entry.get("country", ""),
                "role": entry.get("role", ""),
                "captain": entry.get("captain", False),
                "kind": kind,
            }
        )

    for entry in entries:
        if re.search(_name_pattern(entry["name"]), lowered):
            add(entry, "player")

    context_ok = _has_cricket_context(lowered)
    for name, patterns in PLAYER_ALIASES.items():
        if name not in entries_by_name:
            continue
        if name in CONTEXT_REQUIRED_ALIASES and not context_ok:
            continue
        if any(re.search(pattern, lowered) for pattern in patterns):
            for entry in entries_by_name[name]:
                add(entry, "player")

    for topic in TRACKED_TOPICS:
        if re.search(topic["pattern"], lowered):
            matches.append(
                {
                    "player_name": topic["name"],
                    "team_key": "SRH",
                    "franchise": topic["franchise"],
                    "country": "",
                    "role": topic["role"],
                    "captain": False,
                    "kind": topic["kind"],
                }
            )

    for team in TEAM_PATTERNS:
        if team["franchise"].startswith("Sunrisers Leeds"):
            continue
        if any(re.search(pattern, lowered) for pattern in team["patterns"]):
            add(
                {
                    "name": team["franchise"],
                    "team_key": team["franchise"],
                    "franchise": team["franchise"],
                },
                "team",
            )
        if context_ok and any(re.search(pattern, lowered) for pattern in team["abbreviations"]):
            add(
                {
                    "name": team["franchise"],
                    "team_key": team["franchise"],
                    "franchise": team["franchise"],
                },
                "team",
            )

    leeds_hit = any(re.search(pattern, lowered) for pattern in LEEDS_PATTERNS)
    if leeds_hit:
        women = "women" in lowered
        men = re.search(r"\bmen\b", lowered) is not None
        if women and not men:
            targets = ("Sunrisers Leeds Women",)
        elif men and not women:
            targets = ("Sunrisers Leeds Men",)
        else:
            targets = ("Sunrisers Leeds Men", "Sunrisers Leeds Women")
        for franchise in targets:
            add(
                {"name": franchise, "team_key": franchise, "franchise": franchise},
                "team",
            )

    if not matches and re.search(r"\bsunrisers\b", lowered):
        add(
            {"name": "Sunrisers", "team_key": "Sunrisers", "franchise": "Sunrisers"},
            "team",
        )

    matches.sort(key=lambda item: (item["franchise"], item["player_name"]))
    return matches


# Backwards-compatible names used by older notes and scripts.
MASTER_ROSTER = PLAYERS_BY_TEAM
PLAYER_NICKNAMES = PLAYER_ALIASES
FRANCHISE_PATTERNS = TEAM_PATTERNS
TEAM_NAME_PATTERNS = TEAM_PATTERNS
FALSE_POSITIVE_PHRASES = SPORTS_TO_IGNORE
match_player_or_franchise_in_text = find_our_players_in_story
load_players_from_excel = load_master_roster_from_excel
