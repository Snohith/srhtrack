"""
News Importance Ranker for @SRHXtra.
Calculates impact score (1.0 to 10.0) based on performance milestones, captaincy, and injuries.
"""

def calculate_importance_score(title, summary, player_info):
    """Calculates an importance score from 1.0 to 10.0."""
    score = 5.0
    text = (title + " " + summary).lower()

    # Captaincy boost
    if player_info.get("captain"):
        score += 1.0

    # High-impact performance keywords
    if any(k in text for k in ["century", "100 runs", "100 off", "ton"]):
        score += 3.0
    elif any(k in text for k in ["fifty", "50 runs", "half-century", "50 off"]):
        score += 2.0

    if any(k in text for k in ["5 wickets", "5-wicket", "5/"]):
        score += 3.0
    elif any(k in text for k in ["3 wickets", "3-wicket", "hat-trick", "4 wickets"]):
        score += 2.0

    # Injury / Squad selection keywords
    if any(k in text for k in ["injured", "ruled out", "injury", "fitness"]):
        score += 2.5
    if any(k in text for k in ["named in squad", "called up", "debut", "captain"]):
        score += 1.5

    return min(10.0, round(score, 1))

def categorize_news(title, summary):
    """Categorizes news item into Batting, Bowling, Selection, Injury, or General."""
    text = (title + " " + summary).lower()
    
    if any(k in text for k in ["run", "batting", "century", "fifty", "sixes", "fours"]):
        return "Batting Performance"
    elif any(k in text for k in ["wicket", "bowling", "seamer", "spinner", "spell"]):
        return "Bowling Performance"
    elif any(k in text for k in ["injured", "ruled out", "fitness", "rehab"]):
        return "Injury / Availability"
    elif any(k in text for k in ["squad", "named", "selected", "captain"]):
        return "Selection & Squad"
    else:
        return "General News"
