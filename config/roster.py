"""
Master Roster Registry dynamically loaded from squadofsunrisers.xlsx.
Includes NaN row filtering, regex word boundary matching, and player deduplication.
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

def match_player_in_text(text):
    """
    Finds Sunrisers players mentioned in text using strict regex.
    Deduplicates results so each player is matched at most once per text snippet.
    """
    matches = []
    matched_names = set()
    text_clean = text.lower()
    
    for fp in FALSE_POSITIVE_PHRASES:
        if fp in text_clean and "travis head" not in text_clean:
            text_clean = text_clean.replace(fp, "")

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
            else:
                name_parts = p_name.split()
                if len(name_parts) >= 2:
                    last_name = name_parts[-1]
                    common_words = {"head", "wood", "king", "reddy", "green", "brown", "smith", "baker", "cross"}
                    if last_name.lower() not in common_words:
                        last_pattern = r'\b' + re.escape(last_name.lower()) + r'\b'
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
    return matches
