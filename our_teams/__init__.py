"""
SRHXtra Configuration Package.
Provides master rosters, alias regex matching, fixture calendars, and athletic styling tokens.
"""
from .players import (
    PLAYERS_BY_TEAM,
    find_our_players_in_story,
    PLAYER_NICKNAMES,
    TEAM_NAME_PATTERNS,
)
from .upcoming_matches import UPCOMING_MATCHES, CALENDAR_DAY_BOXES
from .website_look import (
    get_website_style,
    show_top_part,
    show_next_match_big_box,
    show_numbers_at_top,
    show_big_story,
    show_story_card,
    show_small_timeline_story,
    show_match_card,
    show_player_card,
)

__all__ = [
    "PLAYERS_BY_TEAM",
    "find_our_players_in_story",
    "PLAYER_NICKNAMES",
    "TEAM_NAME_PATTERNS",
    "UPCOMING_MATCHES",
    "CALENDAR_DAY_BOXES",
    "get_website_style",
    "show_top_part",
    "show_next_match_big_box",
    "show_numbers_at_top",
    "show_big_story",
    "show_story_card",
    "show_small_timeline_story",
    "show_match_card",
    "show_player_card",
]
