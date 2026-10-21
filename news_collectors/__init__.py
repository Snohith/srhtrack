"""
SRHXtra Scrapers Package.
Provides verified global and hyper-local cricket RSS polling engines.
"""
from .collect_news import (
    collect_fresh_stories,
    NEWS_WEBSITES,
)

# Old names, kept so older guides and links still work.
TOP_50_CRICKET_SOURCES = NEWS_WEBSITES
RSS_FEEDS = NEWS_WEBSITES
CRICKET_SOURCES = NEWS_WEBSITES

__all__ = [
    "collect_fresh_stories",
    "NEWS_WEBSITES",
]
