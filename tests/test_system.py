"""
Automated Verification Test Suite for @SRHXtra Zero-API Command Center.
Tests Master Roster Ingestion, Strict Deduplication Engine, Deep Search, and Logging.
"""

import os
from config.roster import MASTER_ROSTER, match_player_in_text
from database.db_manager import (
    init_db, get_all_players, insert_news, search_news,
    get_recent_news, get_analytics_summary
)
from agents.ranker import calculate_importance_score, categorize_news
from utils.logger import rss_logger, db_logger

def test_system_verification():
    print("🧪 Starting @SRHXtra System Verification Suite...")
    
    # 1. Test DB & Master Roster (73 Players)
    init_db()
    players = get_all_players()
    assert len(players) == 73, f"Failed: Expected 73 players, got {len(players)}"
    print(f"✅ Master Roster test passed ({len(players)} players verified across 4 squads).")
    
    # 2. Comprehensive Deduplication Layer Verification
    test_title = "Deduplication Test Article Title Unique"
    test_link = "https://example.com/unique-test-link-12345"
    
    # First insert (Should succeed)
    id1 = insert_news(
        title=test_title,
        source="Test Source",
        summary="Test Summary Content",
        link=test_link,
        published_at="Jul 24, 2026 @ 10:00 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
        importance_score=8.0,
        category="Selection & Squad"
    )
    assert id1 is not None, "Failed: First insert failed"
    
    # Second insert with EXACT SAME URL (Should be rejected as duplicate)
    id2 = insert_news(
        title="Different Title",
        source="Test Source 2",
        summary="Summary text",
        link=test_link,
        published_at="Jul 24, 2026 @ 10:05 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
        importance_score=8.0,
        category="Selection & Squad"
    )
    assert id2 is None, "Failed: Deduplication layer failed to block duplicate URL"
    
    # Third insert with EXACT SAME TITLE (Should be rejected as duplicate)
    id3 = insert_news(
        title=test_title,
        source="Test Source 3",
        summary="Summary text",
        link="https://example.com/different-link-9999",
        published_at="Jul 24, 2026 @ 10:10 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
        importance_score=8.0,
        category="Selection & Squad"
    )
    assert id3 is None, "Failed: Deduplication layer failed to block duplicate Title"
    
    print("✅ Deduplication Layer passed (100% verified duplicate rejection on URL & Title).")
    
    # 3. Test Search & Analytics
    search_results = search_news("Abhishek")
    assert len(search_results) > 0, "Failed: Search query failed"
    metrics = get_analytics_summary()
    assert metrics["total_news"] > 0, "Failed: Analytics summary failed"
    print(f"✅ Deep Search & Analytics passed (Found {len(search_results)} search results).")
    
    # 4. Test Logging Layer
    rss_logger.info("Test RSS logger verification entry")
    db_logger.info("Test DB logger verification entry")
    assert os.path.exists("logs/rss.log"), "Failed: rss.log file not created"
    assert os.path.exists("logs/database.log"), "Failed: database.log file not created"
    print("✅ Structured Logging Layer passed.")
    
    print("\n🎉 ALL SYSTEM VERIFICATION TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    test_system_verification()
