"""
AI Tweet Generator for @SRHXtra.
Generates 3 ready-to-post X updates: Stat Card, Breaking/Schedule, and Fan Emotion.
"""

from utils.time_utils import format_ist_string

def generate_tweet_drafts(player_name, franchise, details, stats=None):
    """
    Generates 3 ready-to-post X updates based on data inputs.
    Returns a dict with draft_1, draft_2, draft_3.
    """
    hashtag = "#OrangeArmy"
    if "Hyderabad" in franchise or "SRH" in franchise:
        franchise_tag = "#SRH"
    elif "Leeds" in franchise:
        franchise_tag = "#SunrisersLeeds"
    elif "Eastern Cape" in franchise or "SEC" in franchise:
        franchise_tag = "#SEC"
    else:
        franchise_tag = "#Sunrisers"

    # Draft 1: Stat Card / Performance Focus
    if stats:
        runs = stats.get("runs", "")
        balls = stats.get("balls", "")
        fours = stats.get("fours", "")
        sixes = stats.get("sixes", "")
        wickets = stats.get("wickets", "")
        overs = stats.get("overs", "")
        
        stat_line = f"💥 {runs} off {balls} balls ({fours}x4, {sixes}x6)" if runs else f"🎯 {wickets} wickets in {overs} overs"
        draft_1 = (
            f"PURE CLASS FROM {player_name.upper()}! 🦅🔥\n\n"
            f"{stat_line}\n"
            f"Dominating for {franchise}! 🧡\n\n"
            f"Keep this momentum surging into the next match!\n"
            f"{hashtag} {franchise_tag}"
        )
    else:
        draft_1 = (
            f"SPOTLIGHT ON {player_name.upper()}! 🦅\n\n"
            f"{details}\n\n"
            f"Pure Orange Army energy on display! 🧡🔥\n"
            f"{hashtag} {franchise_tag}"
        )

    # Draft 2: Breaking News / Schedule Focus (IST)
    draft_2 = (
        f"🚨 SUNRISERS UPDATE ({format_ist_string()})\n\n"
        f"{player_name} ({franchise}): {details}\n\n"
        f"Next fixture timings & squad availability locked in IST. 🗓️\n"
        f"{hashtag} {franchise_tag}"
    )

    # Draft 3: Fan Emotion / Quote / Viral Moment
    draft_3 = (
        f"{player_name} in Sunrisers colors is hit different! 🧡🦅\n\n"
        f"No fear, high intent, pure entertainment.\n\n"
        f"Who else is hyped for what's coming next? Drop a 🧡 in the replies!\n"
        f"{hashtag} {franchise_tag}"
    )

    return {
        "draft_1": draft_1,
        "draft_2": draft_2,
        "draft_3": draft_3
    }
