"""
Master Roster Registry dynamically loaded from squadofsunrisers.xlsx.
Enforces strict full-name matching for all rostered squad members to eliminate surname misattributions (e.g. Mudassar Hussain matching Sakib Hussain).
"""
import os
import re
import pandas as pd
EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "squadofsunrisers.xlsx")
def load_master_roster_from_excel():
    """Dynamically loads and cleans squad data from squadofsunrisers.xlsx."""
    if not os.path.exists(EXCEL_PATH):
        return {}
    df = pd.read_excel(EXCEL_PATH)
    roster_dict = {}
    for _, row in df.iterrows():
        player = str(row.get("Player", "")).strip()
        if not player or player.lower() == "nan" or pd.isna(row.get("Player")):
            continue
        raw_team = str(row.get("Team", "")).strip()
        role = str(row.get("Role", "")).strip()
        country = str(row.get("Country", "")).strip()
        unnamed = str(row.get("Unnamed: 4", "")).strip()
        raw_role = role
        is_captain = (raw_role == "Captain" or "captain" in raw_role.lower())
        if unnamed and unnamed != "nan":
            if raw_role == "Captain":
                role = country
                country = unnamed
        if "Leeds Men" in raw_team:
            key = "Leeds_Men"
            franchise_name = "Sunrisers Leeds Men"
            league = "The Hundred"
        elif "Leeds Women" in raw_team:
            key = "Leeds_Women"
            franchise_name = "Sunrisers Leeds Women"
            league = "The Hundred Women"
        elif "Eastern Cape" in raw_team:
            key = "SEC"
            franchise_name = "Sunrisers Eastern Cape"
            league = "SA20"
        else:
            key = "SRH"
            franchise_name = "Sunrisers Hyderabad"
            league = "IPL"
        if key not in roster_dict:
            roster_dict[key] = {
                "franchise_name": franchise_name,
                "league": league,
                "players": []
            }
        roster_dict[key]["players"].append({
            "name": player,
            "role": role,
            "country": country,
            "captain": is_captain
        })
    return roster_dict
MASTER_ROSTER = load_master_roster_from_excel()
FALSE_POSITIVE_PHRASES = [
    "padres trade", "cooper kupp", "coles bay", "baseball", "nfl", "nba", "mlb"
]
FRANCHISE_PATTERNS = [
    {
        "name": "Sunrisers Hyderabad",
        "full_patterns": [r'\bsunrisers hyderabad\b'],
        "abbreviations": ["SRH"],
    },
    {
        "name": "Sunrisers Eastern Cape",
        "full_patterns": [r'\bsunrisers eastern cape\b'],
        "abbreviations": ["SEC"],
    },
    {
        "name": "Sunrisers Leeds Women",
        "full_patterns": [r'\bsunrisers leeds women\b'],
        "abbreviations": [],
    },
    {
        "name": "Sunrisers Leeds Men",
        "full_patterns": [r'\bsunrisers leeds men\b', r'\bsunrisers leeds\b'],
        "abbreviations": [],
    },
]
PLAYER_ALIASES = [
    {"name": "Salil Arora", "pattern": r'\b(salil arora|salil)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "Wicket-keeper batter"},
    {"name": "Heinrich Klaasen", "pattern": r'\bklaasen\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "South Africa", "role": "Wicket-keeper batter"},
    {"name": "Pat Cummins", "pattern": r'\bcummins\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "Australia", "role": "All-rounder / Captain"},
    {"name": "Travis Head", "pattern": r'\btravis head\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "Australia", "role": "Opening batter"},
    {"name": "Liam Livingstone", "pattern": r'\blivingstone\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "England", "role": "All-rounder"},
    {"name": "Gerald Coetzee", "pattern": r'\bcoetzee\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "South Africa", "role": "Fast bowler"},
    {"name": "Dilshan Madushanka", "pattern": r'\bmadushanka\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "Sri Lanka", "role": "Fast bowler"},
    {"name": "Jaydev Unadkat", "pattern": r'\bunadkat\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "Fast bowler"},
    {"name": "Quinton de Kock", "pattern": r'\b(de kock|de-kock)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Wicket-keeper batter"},
    {"name": "Tristan Stubbs", "pattern": r'\bstubbs\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Wicket-keeper batter / Captain"},
    {"name": "Marco Jansen", "pattern": r'\bjansen\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "All-rounder"},
    {"name": "Anrich Nortje", "pattern": r'\bnortje\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Bowler"},
    {"name": "Matthew Breetzke", "pattern": r'\bbreetzke\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Wicket-keeper batter"},
    {"name": "Rishad Hossain", "pattern": r'\brishad\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "Bangladesh", "role": "Bowler"},
    {"name": "Lutho Sipamla", "pattern": r'\bsipamla\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Bowler"},
    {"name": "Senuran Muthusamy", "pattern": r'\bmuthusamy\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "All-rounder"},
]
def match_player_or_franchise_in_text(text):
    """
    Finds Sunrisers players OR franchise team names mentioned in text.
    Includes strict full-name matching and single-name distinctive first/last name aliases.
    """
    text_clean = text.lower()
    text_original = text  
    for fp in FALSE_POSITIVE_PHRASES:
        if fp in text_clean:
            return []
    matches = []
    matched_names = set()
    for team_key, data in MASTER_ROSTER.items():
        for p in data["players"]:
            p_name = p["name"]
            if p_name in matched_names:
                continue
            pattern = r'\b' + re.escape(p_name.lower()) + r'\b'
            if re.search(pattern, text_clean):
                matched_names.add(p_name)
                matches.append({
                    "player_name": p_name,
                    "team_key": team_key,
                    "franchise": data["franchise_name"],
                    "country": p["country"],
                    "role": p["role"],
                    "captain": p.get("captain", False)
                })
    for alias in PLAYER_ALIASES:
        p_name = alias["name"]
        if p_name not in matched_names and re.search(alias["pattern"], text_clean):
            matched_names.add(p_name)
            matches.append({
                "player_name": p_name,
                "team_key": alias["team_key"],
                "franchise": alias["franchise"],
                "country": alias["country"],
                "role": alias["role"],
                "captain": False
            })
    if not matches:
        for fp in FRANCHISE_PATTERNS:
            full_name_match = any(
                re.search(pattern, text_clean) for pattern in fp["full_patterns"]
            )
            abbreviation_match = any(
                re.search(r'\b' + re.escape(abbr) + r'\b', text_original)
                for abbr in fp["abbreviations"]
            )
            if full_name_match or abbreviation_match:
                matches.append({
                    "player_name": f"{fp['name']} Team Update",
                    "team_key": fp["name"],
                    "franchise": fp["name"],
                    "country": "Global",
                    "role": "Franchise Update",
                    "captain": False
                })
    if not matches and re.search(r'\bsunrisers\b', text_clean):
        matches.append({
            "player_name": "Sunrisers Franchise Update",
            "team_key": "Sunrisers Hyderabad",
            "franchise": "Sunrisers Hyderabad",
            "country": "Global",
            "role": "Franchise Update",
            "captain": False
        })
    return matches
