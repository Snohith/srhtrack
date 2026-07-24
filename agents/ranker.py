"""
News Importance Ranker & Categorizer for @SRHXtra (V2.0 — Phase 1 Upgrade).

V2.0 changes:
  - Massively expanded keyword maps (batting, bowling, fielding, selection, injury, records)
  - Captain bonus scales with match context (not just flat +1.0)
  - categorize_news() uses priority order to avoid misclassification
  - Normalised score always clamped to [1.0, 10.0]
  - New: SOURCE_TIERS dict used by rss_collector.py to apply source quality boost
"""

# ── Source Quality Tiers ───────────────────────────────────────────────────────
# Tier 1: Official / Premium outlets. Their articles get a +1.5 score boost.
TIER_1_SOURCES = {
    "ESPNcricinfo Story News",
    "Cricbuzz Latest News",
    "BBC Sport Cricket",
    "ICC Official News",
    "Sky Sports Cricket",
    "The Guardian Cricket",
    "Cricket Australia News",
    "IPL Official News",
    "SA20 Official News",
    "ECB Official Cricket",
    "SuperSport Cricket",
    "BCCI Official News",
}

# Tier 2: National mainstream. +0.5 score boost.
TIER_2_SOURCES = {
    "NDTV Sports Cricket",
    "Indian Express Cricket",
    "Times of India Cricket",
    "The Hindu Sports",
    "Hindustan Times Cricket",
    "ABC News Australia Sport",
    "Sydney Morning Herald Sport",
    "News24 SA Sport",
    "Telegraph UK Sport",
    "Wisden Cricket",
    "Sportskeeda Cricket",
    "Fox Sports Australia",
    "TimesLIVE SA Sport",
}
# All other sources are Tier 3 — no boost.


def get_source_tier_boost(source_name: str) -> float:
    """Returns the score boost for a given source name based on its quality tier."""
    if source_name in TIER_1_SOURCES:
        return 1.5
    if source_name in TIER_2_SOURCES:
        return 0.5
    return 0.0


# ── Keyword Maps ───────────────────────────────────────────────────────────────
# Each tuple: (keyword_list, score_boost)
BATTING_BOOSTS = [
    # Extraordinary (≥ +3.5)
    (["double century", "200 runs", "double ton", "200 not out"], 4.0),
    (["century", "100 runs", "100 not out", "100 off", "ton ", " ton,", "maiden century"], 3.5),
    # Strong (≥ +2.0)
    (["fifty", "50 runs", "half-century", "50 not out", "50 off"], 2.0),
    (["man of the match", "player of the match", "match-winning"], 2.5),
    # Moderate (+1.0)
    (["boundaries", "sixes", "six sixes", "fastest fifty", "fastest century", "record innings"], 1.5),
    (["top scorer", "highest scorer", "batting masterclass", "anchored"], 1.0),
]

BOWLING_BOOSTS = [
    # Extraordinary
    (["10 wickets", "10-wicket haul", "all ten"], 4.5),
    (["7 wickets", "8 wickets", "9 wickets"], 4.0),
    (["5 wickets", "5-wicket haul", "five-for", "5/", "fifer"], 3.5),
    (["hat-trick", "hat trick"], 3.5),
    (["4 wickets", "4-wicket", "four-for"], 2.0),
    (["3 wickets", "3-wicket", "three-for"], 1.5),
    # Moderate
    (["maiden over", "economy rate", "best bowling figures", "spell"], 0.8),
]

INJURY_BOOSTS = [
    (["ruled out", "out for the season", "career-ending", "serious injury", "surgery"], 3.5),
    (["injured", "injury scare", "fracture", "torn", "hamstring", "shoulder injury"], 2.5),
    (["fitness doubt", "fitness test", "fitness concern", "nursing"], 2.0),
    (["unavailable", "missed out", "rested", "withdrawn"], 1.5),
    (["rehab", "recovering", "rehabilitation"], 1.0),
]

SELECTION_BOOSTS = [
    (["sacked as captain", "stripped of captaincy", "new captain", "appointed captain"], 3.0),
    (["international debut", "test debut", "t20i debut", "odi debut", "first cap"], 3.0),
    (["named in squad", "called up", "recalled", "included in squad"], 2.0),
    (["dropped", "axed", "left out", "overlooked", "excluded"], 2.0),
    (["squad announced", "squad named", "series squad"], 1.5),
    (["captain", "vice-captain", "leadership"], 1.0),
]

RECORD_BOOSTS = [
    (["world record", "all-time record", "breaks record", "historic", "unprecedented"], 3.0),
    (["record partnership", "highest ever", "fastest ever", "most runs", "most wickets"], 2.5),
    (["landmark", "milestone", "1000 runs", "100 wickets", "500 wickets"], 2.0),
]

NEGATIVE_BOOSTS = [
    # Training, routine stuff — reduce noise
    (["press conference", "interview", "jersey launch", "photoshoot", "training session", "nets session"], -1.0),
    (["auction preview", "trade rumour", "speculation", "reportedly"], -0.5),
]

# Category keyword map — priority order matters (first match wins)
CATEGORY_MAP = [
    ("Injury / Availability", [
        "injur", "ruled out", "fitness", "surgery", "unavailable",
        "rehab", "fracture", "torn", "hamstring", "recovering", "sidelined",
    ]),
    ("Selection & Squad", [
        "squad", "named in", "selected", "dropped", "recalled", "debut",
        "captain", "vice-captain", "appointed", "axed", "overlooked",
    ]),
    ("Batting Performance", [
        "century", "fifty", "run", "batting", "ton", "innings", "boundary",
        "six", "four", "not out", "score", "top order", "opener",
    ]),
    ("Bowling Performance", [
        "wicket", "bowling", "seamer", "spinner", "spell", "hat-trick",
        "five-for", "fifer", "yorker", "caught", "lbw", "bowled", "stumped",
    ]),
    ("Match Report", [
        "won by", "defeated", "chased", "match result", "victory", "clinched",
        "series win", "series loss", "whitewash",
    ]),
    ("Transfer & Contracts", [
        "signed", "released", "traded", "retained", "auction", "contract",
        "franchise", "ipl auction",
    ]),
]


def calculate_importance_score(
    title: str,
    summary: str,
    player_info: dict,
    source_name: str = "",
) -> float:
    """
    Calculates an importance score from 1.0 to 10.0.

    Scoring layers (additive):
      Base:       5.0
      Captaincy:  +0.5 (context-aware)
      Batting:    up to +4.5
      Bowling:    up to +4.5
      Injury:     up to +3.5
      Selection:  up to +3.0
      Records:    up to +3.0
      Source:     +0.0 / +0.5 / +1.5 (tier)
      Noise:      up to −1.0

    Args:
        title:       Article headline
        summary:     Article body/description
        player_info: Dict with at least {"captain": bool}
        source_name: RSS source name for tier boost

    Returns:
        float in range [1.0, 10.0]
    """
    score = 5.0
    text = f"{title} {summary}".lower()

    # Captain context boost (smaller — captaincy alone isn't big news)
    if player_info.get("captain"):
        score += 0.5

    # Apply all keyword boost groups
    for boost_group in (BATTING_BOOSTS, BOWLING_BOOSTS, INJURY_BOOSTS, SELECTION_BOOSTS, RECORD_BOOSTS):
        for keywords, boost in boost_group:
            if any(k in text for k in keywords):
                score += boost
                break  # Only apply the highest matching boost within each group

    # Negative noise reduction
    for keywords, penalty in NEGATIVE_BOOSTS:
        if any(k in text for k in keywords):
            score += penalty  # penalty is already negative

    # Source quality tier boost
    score += get_source_tier_boost(source_name)

    return round(min(10.0, max(1.0, score)), 2)


def categorize_news(title: str, summary: str) -> str:
    """
    Categorises a news article into one of 7 categories using priority-ordered
    keyword matching. First match wins (most specific categories checked first).

    Categories (in priority order):
      1. Injury / Availability
      2. Selection & Squad
      3. Batting Performance
      4. Bowling Performance
      5. Match Report
      6. Transfer & Contracts
      7. General News  ← fallback
    """
    text = f"{title} {summary}".lower()
    for category, keywords in CATEGORY_MAP:
        if any(k in text for k in keywords):
            return category
    return "General News"


def detect_league_context(title: str, summary: str) -> str:
    """Detects tournament/league context for badge display."""
    text = f"{title} {summary}".lower()
    if any(k in text for k in [
        "the hundred", "hundred", "london spirit", "super giants",
        "welsh fire", "trent rockets", "southern brave", "birmingham phoenix",
        "manchester originals",
    ]):
        return "The Hundred"
    if any(k in text for k in [
        "sa20", "sunrisers eastern cape", "pretoria capitals",
        "paarl royals", "joburg super kings",
    ]):
        return "SA20"
    if any(k in text for k in ["ipl", "indian premier league", "sunrisers hyderabad"]):
        return "IPL"
    if any(k in text for k in [
        "t20i", "odi", "test match", "india tour", "world cup", "wtc",
        "test series", "bilateral series",
    ]):
        return "International Cricket"
    return "Global Cricket"
