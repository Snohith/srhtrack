"""
Master Roster Registry dynamically loaded from squadofsunrisers.xlsx.
Enforces strict full-name matching for all rostered squad members to eliminate surname misattributions (e.g. Mudassar Hussain matching Sakib Hussain).
"""
import os
import re
import pandas as pd
_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_PATH = os.path.join(_ROOT_DIR, "data", "squadofsunrisers.xlsx")
_LEGACY_PATH = os.path.join(_ROOT_DIR, "squadofsunrisers.xlsx")
EXCEL_PATH = _DATA_PATH if os.path.exists(_DATA_PATH) else _LEGACY_PATH
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
        if "Leeds Men" in raw_team or raw_team == "Sunrisers Leeds" or ("Leeds" in raw_team and "Women" not in raw_team):
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
    # ── Sunrisers Hyderabad (IPL) ───────────────────────────────────────────
    {"name": "Salil Arora", "pattern": r'\b(salil arora|salil)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "Wicket-keeper batter"},
    {"name": "Heinrich Klaasen", "pattern": r'\bklaasen\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "South Africa", "role": "Wicket-keeper batter"},
    {"name": "Pat Cummins", "pattern": r'\bcummins\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "Australia", "role": "All-rounder / Captain"},
    {"name": "Travis Head", "pattern": r'\btravis head\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "Australia", "role": "Opening batter"},
    {"name": "Abhishek Sharma", "pattern": r'\b(abhishek sharma|abhishek)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "All-rounder"},
    {"name": "Ishan Kishan", "pattern": r'\b(ishan kishan|ishan)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "Wicket-keeper batter"},
    {"name": "Nitish Kumar Reddy", "pattern": r'\b(nitish kumar reddy|nitish reddy)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "All-rounder"},
    {"name": "Harshal Patel", "pattern": r'\b(harshal patel|harshal)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "All-rounder / Pace bowler"},
    {"name": "Liam Livingstone", "pattern": r'\blivingstone\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "England", "role": "All-rounder"},
    {"name": "Gerald Coetzee", "pattern": r'\bcoetzee\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "South Africa", "role": "Fast bowler"},
    {"name": "Kamindu Mendis", "pattern": r'\b(kamindu mendis|kamindu)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "Sri Lanka", "role": "All-rounder"},
    {"name": "Dilshan Madhushanka", "pattern": r'\b(dilshan madhushanka|dilshan madushanka|madhushanka|madushanka)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "Sri Lanka", "role": "Fast bowler"},
    {"name": "Jaydev Unadkat", "pattern": r'\bunadkat\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "Fast bowler"},
    {"name": "R Smaran", "pattern": r'\b(r smaran|smaran ravichandran|smaran)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "Batter"},
    {"name": "RS Ambrish", "pattern": r'\b(rs ambrish|r\.s\. ambrish|ambrish)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "All-rounder / Bowler"},
    {"name": "Daniel Vettori", "pattern": r'\b(daniel vettori|dan vettori|vettori)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "New Zealand", "role": "Head Coach"},
    {"name": "Harsh Dubey", "pattern": r'\b(harsh dubey)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "India", "role": "All-rounder"},
    {"name": "Eshan Malinga", "pattern": r'\b(eshan malinga)\b', "team_key": "SRH", "franchise": "Sunrisers Hyderabad", "country": "Sri Lanka", "role": "Bowler"},

    # ── Sunrisers Eastern Cape (SA20) ───────────────────────────────────────
    {"name": "Quinton De Kock", "pattern": r'\b(quinton de kock|quinton de-kock|de kock|de-kock)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Wicket-keeper batter"},
    {"name": "Tristan Stubbs", "pattern": r'\bstubbs\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Wicket-keeper batter / Captain"},
    {"name": "Marco Jansen", "pattern": r'\bjansen\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "All-rounder"},
    {"name": "Anrich Nortje", "pattern": r'\bnortje\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Bowler"},
    {"name": "Matthew Breetzke", "pattern": r'\bbreetzke\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Wicket-keeper batter"},
    {"name": "Jordan Hermann", "pattern": r'\b(jordan hermann|hermann)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Batter"},
    {"name": "Rishad Hossain", "pattern": r'\brishad\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "Bangladesh", "role": "Bowler"},
    {"name": "Lutho Sipamla", "pattern": r'\bsipamla\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Bowler"},
    {"name": "Senuran Muthusamy", "pattern": r'\bmuthusamy\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "All-rounder"},
    {"name": "Patrick Kruger", "pattern": r'\b(patrick kruger|kruger)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "All-rounder"},
    {"name": "Mitch Marsh", "pattern": r'\b(mitch marsh|mitchell marsh)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "Australia", "role": "All-rounder"},
    {"name": "Mitch Van Buuren", "pattern": r'\b(mitch van buuren|mitchell van buuren|van buuren)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Batter"},
    {"name": "Adrian Birrell", "pattern": r'\b(adrian birrell|birrell)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Head Coach"},
    {"name": "Adam Milne", "pattern": r'\b(adam milne)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "New Zealand", "role": "Bowler"},
    {"name": "Lewis Gregory", "pattern": r'\b(lewis gregory)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "England", "role": "All-rounder"},
    {"name": "James Coles", "pattern": r'\b(james coles)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "England", "role": "All-rounder"},
    {"name": "Nandre Burger", "pattern": r'\b(nandre burger)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "South Africa", "role": "Bowler"},
    {"name": "Craig Overton", "pattern": r'\b(craig overton)\b', "team_key": "SEC", "franchise": "Sunrisers Eastern Cape", "country": "England", "role": "All-rounder"},

    # ── Sunrisers Leeds Men (The Hundred) ───────────────────────────────────
    {"name": "Zak Crawley", "pattern": r'\b(zak crawley|crawley)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Captain / Batter"},
    {"name": "Harry Brook", "pattern": r'\b(harry brook|brook)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Batter"},
    {"name": "Ryan Rickelton", "pattern": r'\b(ryan rickelton|rickelton)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "South Africa", "role": "Wicket-keeper batter"},
    {"name": "Dan Lawrence", "pattern": r'\b(dan lawrence)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Batter"},
    {"name": "Brydon Carse", "pattern": r'\b(brydon carse|carse)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Pace bowler / All-rounder"},
    {"name": "Matthew Potts", "pattern": r'\b(matthew potts|matty potts|potts)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Pace bowler"},
    {"name": "Reece Topley", "pattern": r'\b(reece topley|topley)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Pace bowler"},
    {"name": "Nathan Ellis", "pattern": r'\b(nathan ellis)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "Australia", "role": "Pace bowler"},
    {"name": "Abrar Ahmed", "pattern": r'\b(abrar ahmed|abrar)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "Pakistan", "role": "Spin bowler"},
    {"name": "Matty Revis", "pattern": r'\b(matty revis|matt revis|revis)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "All-rounder"},
    {"name": "Liam Patterson-White", "pattern": r'\b(liam patterson-white|patterson-white)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Spin bowler / All-rounder"},
    {"name": "Tom Lawes", "pattern": r'\b(tom lawes|lawes)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Pace bowler"},
    {"name": "Tom Alsop", "pattern": r'\b(tom alsop|alsop)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "Wicket-keeper batter"},
    {"name": "Benny Howell", "pattern": r'\b(benny howell|howell)\b', "team_key": "Leeds_Men", "franchise": "Sunrisers Leeds Men", "country": "England", "role": "All-rounder"},

    # ── Sunrisers Leeds Women (The Hundred) ─────────────────────────────────
    {"name": "Dani Gibson", "pattern": r'\b(dani gibson|danielle gibson|gibson)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "England", "role": "Captain / All-rounder"},
    {"name": "Phoebe Litchfield", "pattern": r'\b(phoebe litchfield|litchfield)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "Australia", "role": "Batter"},
    {"name": "Annabel Sutherland", "pattern": r'\b(annabel sutherland|sutherland)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "Australia", "role": "All-rounder"},
    {"name": "Deepti Sharma", "pattern": r'\b(deepti sharma|deepti)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "India", "role": "All-rounder"},
    {"name": "Lauren Winfield-Hill", "pattern": r'\b(lauren winfield-hill|winfield-hill|lauren winfield)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "England", "role": "Wicket-keeper batter"},
    {"name": "Kate Cross", "pattern": r'\b(kate cross)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "England", "role": "Pace bowler"},
    {"name": "Jess Jonassen", "pattern": r'\b(jess jonassen|jonassen)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "Australia", "role": "Spin bowler"},
    {"name": "Bryony Smith", "pattern": r'\b(bryony smith)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "England", "role": "Batter"},
    {"name": "Tilly Kesteven", "pattern": r'\b(tilly kesteven|kesteven)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "England", "role": "Batter"},
    {"name": "Rachel Slater", "pattern": r'\b(rachel slater|slater)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "Scotland", "role": "Pace bowler"},
    {"name": "Hannah Baker", "pattern": r'\b(hannah baker)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "England", "role": "Spin bowler"},
    {"name": "Darcey Carter", "pattern": r'\b(darcey carter)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "Scotland", "role": "Batter / All-rounder"},
    {"name": "Chloe Skelton", "pattern": r'\b(chloe skelton)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "England", "role": "Spin bowler"},
    {"name": "Claudie Cooper", "pattern": r'\b(claudie cooper)\b', "team_key": "Leeds_Women", "franchise": "Sunrisers Leeds Women", "country": "England", "role": "Spin bowler"},
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
