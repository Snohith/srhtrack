"""
Master Roster Registry dynamically loaded from squadofsunrisers.xlsx.
Includes strict Regex matching for all 73 squad members AND 4 Franchise Team Names.
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
        
        # Skip invalid / empty / NaN player rows
        if not player or player.lower() == "nan" or pd.isna(row.get("Player")):
            continue

        raw_team = str(row.get("Team", "")).strip()
        role = str(row.get("Role", "")).strip()
        country = str(row.get("Country", "")).strip()
        unnamed = str(row.get("Unnamed: 4", "")).strip()

        if unnamed and unnamed != "nan":
            if role == "Captain":
                role = country
                country = unnamed

        # Map to canonical franchise key
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

        is_captain = (role == "Captain" or "captain" in role.lower())
        roster_dict[key]["players"].append({
            "name": player,
            "role": role,
            "country": country,
            "captain": is_captain
        })

    return roster_dict

MASTER_ROSTER = load_master_roster_from_excel()

# Blacklisted false-positive phrases
FALSE_POSITIVE_PHRASES = ["head coach", "head of", "head-to-head", "head coach's", "woodwork"]

# Surnames that MUST require Full Name matching to prevent misattribution
COMMON_SURNAMES = {
    "sharma", "kumar", "patel", "singh", "ali", "ahmed", "wilson", 
    "smith", "baker", "cross", "head", "wood", "king", "reddy", "green", "brown"
}

# Franchise Team Name Patterns
FRANCHISE_PATTERNS = [
    {"name": "Sunrisers Hyderabad", "pattern": r'\b(sunrisers hyderabad|srh)\b'},
    {"name": "Sunrisers Eastern Cape", "pattern": r'\b(sunrisers eastern cape|sec)\b'},
    {"name": "Sunrisers Leeds Men", "pattern": r'\b(sunrisers leeds men|sunrisers leeds)\b'},
    {"name": "Sunrisers Leeds Women", "pattern": r'\b(sunrisers leeds women)\b'},
]

def match_player_or_franchise_in_text(text):
    """
    Finds Sunrisers players OR franchise team names mentioned in text.
    1. Checks all 73 squad members.
    2. If no player name matches, checks for mentions of any of the 4 Franchise Team Names.
    """
    matches = []
    matched_names = set()
    text_clean = text.lower()
    
    for fp in FALSE_POSITIVE_PHRASES:
        if fp in text_clean and "travis head" not in text_clean:
            text_clean = text_clean.replace(fp, "")

    # 1. Match Player Names (73 Squad Members)
    for team_key, data in MASTER_ROSTER.items():
        for p in data["players"]:
            p_name = p["name"]
            if p_name in matched_names:
                continue

            # Full Name Matching
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
            else:
                # Unique Surname Matching
                name_parts = p_name.split()
                if len(name_parts) >= 2:
                    last_name = name_parts[-1].lower()
                    if last_name not in COMMON_SURNAMES and len(last_name) >= 4:
                        last_pattern = r'\b' + re.escape(last_name) + r'\b'
                        if re.search(last_pattern, text_clean):
                            matched_names.add(p_name)
                            matches.append({
                                "player_name": p_name,
                                "team_key": team_key,
                                "franchise": data["franchise_name"],
                                "country": p["country"],
                                "role": p["role"],
                                "captain": p.get("captain", False)
                            })

    # 2. If no player matches, check Franchise Team Names
    if not matches:
        for fp in FRANCHISE_PATTERNS:
            if re.search(fp["pattern"], text_clean):
                matches.append({
                    "player_name": f"{fp['name']} Team Update",
                    "team_key": fp["name"],
                    "franchise": fp["name"],
                    "country": "Global",
                    "role": "Franchise Update",
                    "captain": False
                })

    # 3. Generic "Sunrisers" keyword fallback
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
