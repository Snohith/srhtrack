"""
SRHXtra Database Package.
Provides persistent SQLite storage, migrations, and target-aware deduplication.
"""
from .db_manager import (
    init_db,
    get_connection,
    get_all_players,
    insert_news,
    get_recent_news,
    search_news,
    get_analytics_summary,
    get_metadata,
    set_metadata,
    purge_expired_24h_news,
    purge_stale_notifications,
    cleanup_invalid_matches,
)

__all__ = [
    "init_db",
    "get_connection",
    "get_all_players",
    "insert_news",
    "get_recent_news",
    "search_news",
    "get_analytics_summary",
    "get_metadata",
    "set_metadata",
    "purge_expired_24h_news",
    "purge_stale_notifications",
    "cleanup_invalid_matches",
]
