"""
Automated Verification Test Suite for @SRHXtra Zero-API Command Center.
Tests Master Roster Ingestion, Strict Deduplication Engine, Deep Search,
Analytics Summary, and Logging.

V2.0 improvements:
  - Uses an isolated temp DB (via SRH_DB_PATH env var) — never touches production DB
  - Fixed import: match_player_or_franchise_in_text (correct function name)
  - Removed invalid kwargs from insert_news() calls (importance_score, category)
  - Log file assertions use absolute paths (works from any working directory)
  - Compatible with pytest (pytest.ini sets pythonpath = .)
"""

import os
import tempfile
import pytest

# ── Isolated test DB — must be set BEFORE importing db_manager ───────────────
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["SRH_DB_PATH"] = _tmp_db.name

from config.roster import MASTER_ROSTER, match_player_or_franchise_in_text
from database.db_manager import (
    init_db, get_all_players, insert_news, search_news,
    get_recent_news, get_analytics_summary
)
from agents.ranker import calculate_importance_score, categorize_news
from utils.logger import rss_logger, db_logger


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Initialise the isolated test DB once for the whole module."""
    init_db()
    yield
    # Cleanup temp DB file after tests complete
    try:
        os.unlink(_tmp_db.name)
    except OSError:
        pass


def test_master_roster_count():
    """73 players must be seeded into the DB from the Excel roster."""
    players = get_all_players()
    assert len(players) == 73, f"Expected 73 players, got {len(players)}"
    print(f"✅ Master Roster: {len(players)} players verified across 4 squads.")


def test_deduplication_by_url():
    """Second insert with same URL must be rejected (returns None)."""
    test_link = "https://example.com/dedup-url-test-001"
    id1 = insert_news(
        title="Dedup URL Test Article",
        source="Test Source",
        summary="Test Summary",
        link=test_link,
        published_at="Jul 24, 2026 @ 10:00 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
    )
    assert id1 is not None, "First insert should succeed"

    id2 = insert_news(
        title="Different Title Same URL",
        source="Test Source 2",
        summary="Different summary",
        link=test_link,
        published_at="Jul 24, 2026 @ 10:05 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
    )
    assert id2 is None, "Duplicate URL must be rejected"
    print("✅ Deduplication by URL: passed.")


def test_deduplication_by_title():
    """Second insert with same title (different URL) must be rejected."""
    test_title = "Dedup Title Test Article — Unique String XYZ987"
    id1 = insert_news(
        title=test_title,
        source="Test Source A",
        summary="Summary A",
        link="https://example.com/title-dedup-link-001",
        published_at="Jul 24, 2026 @ 10:10 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
    )
    assert id1 is not None, "First insert should succeed"

    id2 = insert_news(
        title=test_title,
        source="Test Source B",
        summary="Summary B",
        link="https://example.com/title-dedup-link-002",
        published_at="Jul 24, 2026 @ 10:15 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
    )
    assert id2 is None, "Duplicate title must be rejected"
    print("✅ Deduplication by Title: passed.")


def test_search_news():
    """search_news() must return at least one result for a known player."""
    results = search_news("Abhishek")
    assert len(results) > 0, "search_news('Abhishek') returned no results"
    print(f"✅ Search: found {len(results)} results for 'Abhishek'.")


def test_analytics_summary():
    """get_analytics_summary() must report > 0 news and players."""
    metrics = get_analytics_summary()
    assert metrics["total_news"] > 0,    "Analytics: total_news should be > 0"
    assert metrics["total_players"] > 0, "Analytics: total_players should be > 0"
    print(f"✅ Analytics: {metrics['total_news']} news, {metrics['total_players']} players.")


def test_ranker_importance_score():
    """Importance score for century article should be above baseline (5.0)."""
    score = calculate_importance_score(
        title="Abhishek Sharma scores stunning century",
        summary="He hit 100 runs off 55 balls in the T20I.",
        player_info={"captain": False}
    )
    assert score > 5.0, f"Expected score > 5.0, got {score}"
    print(f"✅ Ranker importance score: {score}")


def test_ranker_categorize():
    """categorize_news() must correctly categorise a batting headline."""
    category = categorize_news(
        title="Abhishek Sharma hits fifty in T20I",
        summary="He scored 50 runs in the first innings."
    )
    assert category == "Batting Performance", f"Unexpected category: {category}"
    print(f"✅ Ranker category: {category}")


def test_match_player_function():
    """match_player_or_franchise_in_text must match a known player name."""
    results = match_player_or_franchise_in_text("Heinrich Klaasen played brilliantly today")
    names = [r["player_name"] for r in results]
    assert "Heinrich Klaasen" in names, f"Expected 'Heinrich Klaasen' in {names}"
    print("✅ Player name matching: passed.")


def test_logging_files_exist():
    """Logger must have created rss.log and database.log files."""
    rss_logger.info("Test RSS logger verification entry")
    db_logger.info("Test DB logger verification entry")

    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    assert os.path.exists(os.path.join(logs_dir, "rss.log")),      "rss.log not found"
    assert os.path.exists(os.path.join(logs_dir, "database.log")), "database.log not found"
    print("✅ Logging files: rss.log and database.log confirmed.")


# ── Standalone runner ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🧪 Starting @SRHXtra System Verification Suite...\n")
    init_db()
    test_master_roster_count()
    test_deduplication_by_url()
    test_deduplication_by_title()
    test_search_news()
    test_analytics_summary()
    test_ranker_importance_score()
    test_ranker_categorize()
    test_match_player_function()
    test_logging_files_exist()
    print("\n🎉 ALL SYSTEM VERIFICATION TESTS PASSED CLEANLY!")
