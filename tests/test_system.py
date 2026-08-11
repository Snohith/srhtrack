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
    try:
        os.unlink(_tmp_db.name)
    except OSError:
        pass
def test_master_roster_count():
    """Distinct players must be seeded into the DB from the Excel roster."""
    players = get_all_players()
    expected_distinct = len({p["name"] for data in MASTER_ROSTER.values() for p in data["players"]})
    assert len(players) == expected_distinct, f"Expected {expected_distinct} distinct players, got {len(players)}"
    print(f"✅ Master Roster: {len(players)} distinct players verified across 4 squads.")
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
def test_same_article_can_track_multiple_targets():
    """One URL/title mentioning multiple players must be stored for each matched target."""
    test_link = "https://example.com/multi-target-article-001"
    test_title = "Abhishek Sharma and Heinrich Klaasen star for Sunrisers"
    id1 = insert_news(
        title=test_title,
        source="Test Source",
        summary="Both Sunrisers players were in the news.",
        link=test_link,
        published_at="Jul 24, 2026 @ 11:00 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
    )
    id2 = insert_news(
        title=test_title,
        source="Test Source",
        summary="Both Sunrisers players were in the news.",
        link=test_link,
        published_at="Jul 24, 2026 @ 11:00 AM IST",
        player_name="Heinrich Klaasen",
        franchise="Sunrisers Hyderabad",
    )
    id3 = insert_news(
        title=test_title,
        source="Test Source",
        summary="Duplicate same target should still be rejected.",
        link=test_link,
        published_at="Jul 24, 2026 @ 11:00 AM IST",
        player_name="Abhishek Sharma",
        franchise="Sunrisers Hyderabad",
    )
    assert id1 is not None, "First target insert should succeed"
    assert id2 is not None, "Second target from same article should succeed"
    assert id3 is None, "Duplicate same URL/title and target must be rejected"
    print("✅ Multi-target article dedupe: passed.")
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
def test_franchise_name_matching_is_case_insensitive():
    """Title-case franchise names must not fall through to the generic SRH fallback."""
    sec_matches = match_player_or_franchise_in_text("Sunrisers Eastern Cape announce their SA20 squad")
    assert sec_matches[0]["franchise"] == "Sunrisers Eastern Cape", sec_matches
    srh_matches = match_player_or_franchise_in_text("sunrisers hyderabad prepare for IPL auction")
    assert srh_matches[0]["franchise"] == "Sunrisers Hyderabad", srh_matches
    leeds_women_matches = match_player_or_franchise_in_text("Sunrisers Leeds Women announce squad changes")
    assert leeds_women_matches[0]["franchise"] == "Sunrisers Leeds Women", leeds_women_matches
    assert match_player_or_franchise_in_text("The timer runs for 30 sec before reset") == []
    print("✅ Franchise name case-insensitive matching: passed.")
def test_head_coach_phrase_matching():
    """Valid player news must NOT be dropped when 'head coach' phrase is present."""
    text = "Abhishek Sharma spoke with head coach VVS Laxman ahead of the match"
    matches = match_player_or_franchise_in_text(text)
    names = [m["player_name"] for m in matches]
    assert "Abhishek Sharma" in names, f"Expected Abhishek Sharma to match despite 'head coach', got {names}"
    non_cricket_text = "Abhishek Sharma in padres trade baseball update"
    assert match_player_or_franchise_in_text(non_cricket_text) == [], "Non-cricket false positive should return empty list"
    print("✅ Head coach & false-positive phrase filtering: passed.")
def test_hyperlocal_source_tier_boost():
    """Telangana Today & Yorkshire CCC Tier 1 sources must receive a +1.5 tier boost."""
    score_local = calculate_importance_score(
        title="Abhishek Sharma hit a fifty",
        summary="Match update at Uppal stadium",
        player_info={"captain": False},
        source_name="Telangana Today Sport"
    )
    score_regular = calculate_importance_score(
        title="Abhishek Sharma hit a fifty",
        summary="Match update at Uppal stadium",
        player_info={"captain": False},
        source_name="Unknown Source"
    )
    assert score_local - score_regular == 1.5, f"Expected Tier 1 +1.5 boost, got diff {score_local - score_regular}"
    print("✅ Hyper-local source tier boost: passed.")
def test_current_feed_names_receive_source_tier_boosts():
    """Premium feed names used by CRICKET_SOURCES must align with ranker source tiers."""
    from agents.ranker import get_source_tier_boost
    assert get_source_tier_boost("ESPNcricinfo India") == 1.5
    assert get_source_tier_boost("Cricbuzz (FeedBurner)") == 1.5
    assert get_source_tier_boost("Sportstar (The Hindu)") == 1.5
    assert get_source_tier_boost("SMH Sport") == 0.5
    print("✅ Current feed source tier boosts: passed.")
def test_tilly_kesteven_tracking():
    """Verify Tilly Kesteven is loaded into roster and tracked cleanly."""
    players = get_all_players(franchise_filter="Sunrisers Leeds Women")
    p_names = [p["name"] for p in players]
    assert "Tilly Kesteven" in p_names, f"Expected Tilly Kesteven in Sunrisers Leeds Women, got {p_names}"
    matches = match_player_or_franchise_in_text("Tilly Kesteven joined the Sunrisers Leeds Women camp recently")
    m_names = [m["player_name"] for m in matches]
    assert "Tilly Kesteven" in m_names, f"Expected Tilly Kesteven match, got {m_names}"
    print("✅ Tilly Kesteven tracking: verified successfully.")
def test_logging_files_exist():
    """Logger must have created rss.log and database.log files."""
    rss_logger.info("Test RSS logger verification entry")
    db_logger.info("Test DB logger verification entry")
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    assert os.path.exists(os.path.join(logs_dir, "rss.log")),      "rss.log not found"
    assert os.path.exists(os.path.join(logs_dir, "database.log")), "database.log not found"
    print("✅ Logging files: rss.log and database.log confirmed.")
def test_source_count_dynamic():
    """CRICKET_SOURCES must have >= 48 verified entries (audited 2026-07-31 — dead feeds removed)."""
    from scrapers.rss_collector import CRICKET_SOURCES, TOP_50_CRICKET_SOURCES
    assert len(CRICKET_SOURCES) >= 48, f"Expected ≥ 48 sources, got {len(CRICKET_SOURCES)}"
    assert CRICKET_SOURCES is TOP_50_CRICKET_SOURCES, "TOP_50_CRICKET_SOURCES alias must point to CRICKET_SOURCES"
    names = [s['name'] for s in CRICKET_SOURCES]
    assert len(names) == len(set(names)), f"Duplicate source names found: {[n for n in names if names.count(n) > 1]}"
    urls = [s['url'] for s in CRICKET_SOURCES]
    assert len(urls) == len(set(urls)), f"Duplicate source URLs found"
    print(f"✅ Source count dynamic: {len(CRICKET_SOURCES)} sources, no duplicates.")
def test_schema_uses_target_aware_news_dedupe():
    """Schema must not globally unique-constrain article links."""
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "schema.sql")
    with open(schema_path) as f:
        schema_text = f.read()
    assert "link TEXT UNIQUE" not in schema_text, "news.link must not be globally unique"
    assert "idx_news_link_target" in schema_text, "schema must dedupe links per tracked target"
    assert "idx_news_title_target" in schema_text, "schema must dedupe titles per tracked target"
    print("✅ Target-aware news dedupe schema: passed.")
def test_category_default_alignment():
    """The schema.sql category DEFAULT and insert_news() default must both be 'General News'."""
    import inspect
    from database.db_manager import insert_news
    sig = inspect.signature(insert_news)
    code_default = sig.parameters['category'].default
    assert code_default == 'General News', f"insert_news category default is '{code_default}', expected 'General News'"
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database", "schema.sql")
    with open(schema_path) as f:
        schema_text = f.read()
    assert "DEFAULT 'General News'" in schema_text, "schema.sql category default must be 'General News'"
    assert "DEFAULT 'General'" not in schema_text, "schema.sql still has old DEFAULT 'General'"
    print("✅ Category default alignment: schema.sql and insert_news() both use 'General News'.")
def test_scheduler_no_init_db():
    """scheduler/worker.py must NOT call init_db() (to avoid redundant migrations on every cycle).
    Checks for actual function call — ignores any mention in comments/docstrings.
    """
    import re
    scheduler_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scheduler", "worker.py")
    with open(scheduler_path) as f:
        source = f.read()
    source_no_comments = re.sub(r'(#[^\n]*|\'\'\'[\s\S]*?\'\'\'|"""[\s\S]*?""")', '', source)
    assert 'init_db()' not in source_no_comments, "scheduler/worker.py must not call init_db() — it runs migrations on every cycle"
    print("✅ Scheduler isolation: init_db() not called in worker.py.")
def test_single_name_alias_matching():
    """Verify that headlines using single names like 'Salil' or 'Klaasen' match the player's profile."""
    text = "Ayush Mhatre to SRH trade deal called off SRH offered Salil in return"
    matches = match_player_or_franchise_in_text(text)
    p_names = [m["player_name"] for m in matches]
    assert "Salil Arora" in p_names, f"Expected Salil Arora in matches, got {p_names}"
    print("✅ Single-name alias matching ('Salil' -> 'Salil Arora'): verified successfully.")
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
    test_head_coach_phrase_matching()
    test_hyperlocal_source_tier_boost()
    test_tilly_kesteven_tracking()
    test_logging_files_exist()
    test_source_count_dynamic()
    test_category_default_alignment()
    test_scheduler_no_init_db()
    test_single_name_alias_matching()
    print("\n🎉 ALL SYSTEM VERIFICATION TESTS PASSED CLEANLY!")
