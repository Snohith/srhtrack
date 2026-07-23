"""
Importance Ranking & Categorization Engine for @SRHXtra.
Ranks player news items on a 1.0 to 10.0 scale based on keywords and context.
"""

def calculate_importance_score(title, summary, player_info):
    """Calculates importance score between 1.0 and 10.0."""
    score = 5.0
    combined_text = (f"{title} {summary}").lower()
    
    # Captain / Key Player weight
    if player_info.get("captain"):
        score += 1.5
    
    # Keyword weights
    high_impact_keywords = [
        "century", "100", "50", "fifty", "hat-trick", "5-wicket", "5 wickets", "4 wickets",
        "captain", "trophy", "champion", "man of the match", "player of the match", "won", "injury", "ruled out"
    ]
    medium_impact_keywords = [
        "wicket", "six", "chase", "squad", "selected", "interview", "stat", "record", "haul"
    ]
    
    for kw in high_impact_keywords:
        if kw in combined_text:
            score += 1.0
            
    for kw in medium_impact_keywords:
        if kw in combined_text:
            score += 0.5
            
    return min(round(score, 1), 10.0)

def categorize_news(title, summary):
    """Categorizes news item into Batting, Bowling, Injury, Selection, or General."""
    text = (f"{title} {summary}").lower()
    
    if any(k in text for k in ["injury", "ruled out", "fit", "medical", "strain", "rehab"]):
        return "Injury / Availability"
    elif any(k in text for k in ["runs", "50", "100", "century", "half-century", "batting", "sixes", "fours"]):
        return "Batting Performance"
    elif any(k in text for k in ["wickets", "bowling", "economy", "hat-trick", "haul", "pace"]):
        return "Bowling Performance"
    elif any(k in text for k in ["squad", "selected", "captain", "contract", "auction"]):
        return "Selection & Squad"
    else:
        return "General Update"
