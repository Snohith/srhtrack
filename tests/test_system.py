"""
Automated Verification Test Suite for @SRHXtra Zero-API Command Center (V1.5).
"""

import os
from config.roster import MASTER_ROSTER, match_player_in_text
from database.db_manager import (
    init_db, get_all_players, insert_news, search_news,
    insert_tweet, get_tweets, get_analytics_summary
)
from agents.ranker import calculate_importance_score, categorize_news
from agents.tweet_generator import generate_tweet_drafts
from graphics.generator import create_stat_card, detect_best_template
from utils.logger import rss_logger, db_logger

def test_system_v1_5():
    print("🧪 Starting @SRHXtra V1.5 System Verification Suite...")
    
    # 1. Test DB & Roster
    init_db()
    players = get_all_players()
    assert len(players) > 0, "Failed: Players table empty"
    print(f"✅ DB Roster test passed ({len(players)} players loaded).")
    
    # 2. Test Deduplication Layer
    id1 = insert_news("Test Article Headline", "Test Source", "Summary text", "http://example.com/1", "2026-07-24", "Abhishek Sharma", "Sunrisers Hyderabad", 8.0, "Batting")
    id2 = insert_news("Test Article Headline", "Test Source", "Summary text", "http://example.com/1", "2026-07-24", "Abhishek Sharma", "Sunrisers Hyderabad", 8.0, "Batting")
    assert id1 is not None, "Failed: First insert failed"
    assert id2 is None, "Failed: Duplicate detection failed to block repeated URL"
    print("✅ Duplicate detection layer passed.")
    
    # 3. Test Search & Analytics
    search_results = search_news("Abhishek")
    assert len(search_results) > 0, "Failed: Search query failed"
    metrics = get_analytics_summary()
    assert metrics["total_news"] > 0, "Failed: Analytics summary failed"
    print(f"✅ Deep Search & Analytics passed (Found {len(search_results)} search results).")
    
    # 4. Test Auto-Graphic Template Selection
    t_century, b1 = detect_best_template("Scored 105 runs off 48 balls")
    t_fifty, b2 = detect_best_template("50 off 20 balls")
    t_5wkts, b3 = detect_best_template("5 wickets for 18 runs")
    
    assert t_century == "century", "Failed: Century template detection failed"
    assert t_fifty == "fifty", "Failed: Fifty template detection failed"
    assert t_5wkts == "five_wickets", "Failed: 5-Wicket template detection failed"
    print("✅ Smart Auto-Graphic Template Detection passed.")
    
    # 5. Test Logging Layer
    rss_logger.info("Test RSS logger verification entry")
    db_logger.info("Test DB logger verification entry")
    assert os.path.exists("logs/rss.log"), "Failed: rss.log file not created"
    assert os.path.exists("logs/database.log"), "Failed: database.log file not created"
    print("✅ Structured Logging Layer passed.")
    
    print("\n🎉 ALL V1.5 SYSTEM TESTS PASSED CLEANLY!")

if __name__ == "__main__":
    test_system_v1_5()
