"""
SRHXtra Database Package.
Provides persistent SQLite storage, migrations, and target-aware deduplication.
"""
from .story_storage import (
    set_up_story_box,
    open_story_box,
    get_all_players,
    save_story,
    get_latest_stories,
    search_stories,
    count_stories_and_players,
    read_saved_fact,
    save_a_fact,
    throw_away_old_stories,
    throw_away_old_notes,
    remove_stories_that_mention_no_one,
)

__all__ = [
    "set_up_story_box",
    "open_story_box",
    "get_all_players",
    "save_story",
    "get_latest_stories",
    "search_stories",
    "count_stories_and_players",
    "read_saved_fact",
    "save_a_fact",
    "throw_away_old_stories",
    "throw_away_old_notes",
    "remove_stories_that_mention_no_one",
]
