"""
SRHXtra Configuration Package.
Provides master rosters, alias regex matching, fixture calendars, and athletic styling tokens.
"""
from .roster import (
    MASTER_ROSTER,
    match_player_or_franchise_in_text,
    PLAYER_ALIASES,
    FRANCHISE_PATTERNS,
)
from .schedule import FIXTURE_SCHEDULE, GRID_DATE_SLOTS
from .theme import (
    get_custom_css,
    render_header_banner,
    render_next_match_hero,
    render_telemetry_metrics,
    render_featured_hero_news,
    render_telemetry_news_card,
    render_telemetry_pulse_item,
    render_broadcast_match_card,
    render_otd_telemetry_card,
    render_squad_member_card,
)

__all__ = [
    "MASTER_ROSTER",
    "match_player_or_franchise_in_text",
    "PLAYER_ALIASES",
    "FRANCHISE_PATTERNS",
    "FIXTURE_SCHEDULE",
    "GRID_DATE_SLOTS",
    "get_custom_css",
    "render_header_banner",
    "render_next_match_hero",
    "render_telemetry_metrics",
    "render_featured_hero_news",
    "render_telemetry_news_card",
    "render_telemetry_pulse_item",
    "render_broadcast_match_card",
    "render_otd_telemetry_card",
    "render_squad_member_card",
]
