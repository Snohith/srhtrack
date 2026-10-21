"""Schema, roster, matching, URL safety, and cleanup tests."""
from __future__ import annotations

import hashlib
import os
import sqlite3

import pytest

from helpers.links import article_key, canonicalize_url, normalize_title
from our_teams.players import PLAYERS_BY_TEAM, find_our_players_in_story
from saved_stories.story_storage import open_story_box, set_up_story_box


def _tables(path):
    with sqlite3.connect(path) as conn:
        return {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }


def test_fresh_install_creates_ledger_and_roster():
    tables = _tables(os.environ["SUNRISERS_DB_PATH"])
    assert {"articles", "deliveries", "feed_health", "suppressed_titles"} <= tables
    assert "news" not in tables and "alerted_stories" not in tables

    rows = sum(len(team["players"]) for team in PLAYERS_BY_TEAM.values())
    unique = {
        player["name"]
        for team in PLAYERS_BY_TEAM.values()
        for player in team["players"]
    }
    assert len(PLAYERS_BY_TEAM) == 4
    assert rows == 90
    assert len(unique) == 88

    from contextlib import closing

    with closing(open_story_box()) as conn:
        article_columns = {row["name"] for row in conn.execute("PRAGMA table_info(articles)")}
        delivery_columns = {row["name"] for row in conn.execute("PRAGMA table_info(deliveries)")}
    assert {"people", "franchises", "topics", "title_key", "dedupe_key"} <= article_columns
    assert {"status", "attempts", "next_attempt_ts", "claimed_at"} <= delivery_columns


def test_schema_setup_is_idempotent():
    from saved_stories.story_storage import save_article
    article_id = save_article(
        "Heinrich Klaasen fifty", "Test", "Summary", "https://example.com/a",
        "", 0, ["Heinrich Klaasen"], ["Sunrisers Hyderabad"], [],
    )
    assert article_id is not None
    set_up_story_box()
    from contextlib import closing

    with closing(open_story_box()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1


def test_multi_franchise_player_matches_every_team():
    marsh = find_our_players_in_story("Mitch Marsh signs a new deal")
    assert {match["franchise"] for match in marsh} == {
        "Sunrisers Eastern Cape", "Sunrisers Leeds Men",
    }
    carse = find_our_players_in_story("Brydon Carse is fit again")
    assert {match["franchise"] for match in carse} == {
        "Sunrisers Hyderabad", "Sunrisers Leeds Men",
    }
    vettori = find_our_players_in_story("Vettori plans the bowling attack")
    assert {match["franchise"] for match in vettori} == {
        "Sunrisers Hyderabad", "Sunrisers Leeds Men",
    }


def test_team_name_matching_and_leeds_gender():
    assert find_our_players_in_story("Sunrisers Eastern Cape name a squad")[0]["franchise"] == (
        "Sunrisers Eastern Cape"
    )
    generic = find_our_players_in_story("Sunrisers Leeds announce a signing")
    assert {match["franchise"] for match in generic} == {
        "Sunrisers Leeds Men", "Sunrisers Leeds Women",
    }
    women = find_our_players_in_story("Sunrisers Leeds Women announce a signing")
    assert {match["franchise"] for match in women} == {"Sunrisers Leeds Women"}


def test_alias_precision_guards_common_false_positives():
    assert "Abhishek Sharma" not in {
        match["player_name"] for match in find_our_players_in_story("Bengal pick Abhishek Porel")
    }
    assert "Ishan Kishan" not in {
        match["player_name"] for match in find_our_players_in_story("Ishan Porel takes five")
    }
    assert find_our_players_in_story("SEC filing shows revenue growth") == []
    assert find_our_players_in_story("Cummins quarterly results beat estimates") == []
    assert find_our_players_in_story("Brookfield buys a site") == []
    assert find_our_players_in_story("head coach speaks to the media") == []
    assert "Travis Head" in {
        match["player_name"] for match in find_our_players_in_story("Travis Head hits a fifty")
    }


def test_management_topics_are_tracked():
    topics = find_our_players_in_story("Sun Group discloses a stake filing")
    assert any(match["player_name"] == "Sun Group" for match in topics)
    people = find_our_players_in_story("Kavya Maran speaks about the auction")
    assert any(match["player_name"] == "Kavya Maran" for match in people)


def test_srh_abbreviation_and_injury_alias_context():
    srh = find_our_players_in_story("SRH announce new captain")
    assert {match["franchise"] for match in srh} == {"Sunrisers Hyderabad"}
    injury = find_our_players_in_story("Cummins ruled out with a injury")
    assert "Pat Cummins" in {match["player_name"] for match in injury}
    assert find_our_players_in_story("SEC filing shows revenue growth") == []


def test_roster_surname_aliases_stay_usable():
    fixtures = find_our_players_in_story("Crawley hits a fifty")
    assert "Zak Crawley" in {match["player_name"] for match in fixtures}
    potts = find_our_players_in_story("Potts takes three wickets")
    assert "Matthew Potts" in {match["player_name"] for match in potts}
    assert find_our_players_in_story("Brookfield buys a site") == []


def test_url_safety_and_identity():
    assert canonicalize_url("https://example.com/a?utm_source=x&id=7#frag") == (
        "https://example.com/a?id=7"
    )
    for unsafe in (
        "javascript:alert(1)",
        "data:text/html,x",
        "file:///etc/passwd",
        "ftp://example.com/x",
        "http://127.0.0.1/x",
        "http://localhost/x",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/x",
        "http://user:pass@example.com/x",
        "http://foo.internal/x",
        "http://[::1]/x",
        "http://10.0.0.1/x",
        "https://exa mple.com/x",
        "https://example..com/x",
        "https://-bad.example/x",
        "http://2130706433/x",
        "http://0x7f000001/x",
        "http://0177.0.0.1/x",
        "http://999.999.999.999/x",
    ):
        assert canonicalize_url(unsafe) == "", unsafe
    assert canonicalize_url("https://[2606:4700:4700::1111]/x") == (
        "https://[2606:4700:4700::1111]/x"
    )
    assert canonicalize_url("https://news.google.com/rss/articles/abc?oc=5")
    assert article_key("", "Same title") == article_key("", "same  title")
    assert article_key("https://example.com/a", "x") != article_key("", "x")


def test_title_normalization_folds_outlet_suffix():
    direct = "Proteas Player Ratings: Markram outstanding, but Rickelton and Stubbs fail"
    mirror = direct + " - IOL"
    assert normalize_title(direct) == normalize_title(mirror)
    assert normalize_title("Match tied - 1st T20I") != normalize_title("Match tied - 2nd T20I")


def test_legacy_tables_are_migrated_and_dropped(tmp_path, monkeypatch):
    import time

    legacy = tmp_path / "legacy.db"
    with sqlite3.connect(legacy) as conn:
        conn.executescript(
            """
            CREATE TABLE news (id INTEGER PRIMARY KEY, title TEXT);
            CREATE TABLE alerted_stories (
                id INTEGER PRIMARY KEY, title_norm TEXT, player_name TEXT,
                franchise TEXT, first_seen_ts REAL
            );
            INSERT INTO news (title) VALUES ('old dashboard row');
            """
        )
        conn.execute(
            "INSERT INTO alerted_stories (title_norm, player_name, franchise, first_seen_ts) "
            "VALUES ('recently sent title', 'Abhishek Sharma', 'Sunrisers Hyderabad', ?)",
            (time.time(),),
        )
    monkeypatch.setenv("SUNRISERS_DB_PATH", str(legacy))
    set_up_story_box()
    tables = _tables(str(legacy))
    assert "news" not in tables and "alerted_stories" not in tables
    with sqlite3.connect(legacy) as conn:
        row = conn.execute(
            "SELECT title_key FROM suppressed_titles WHERE title_key = 'recently sent title'"
        ).fetchone()
    assert row is not None


def test_roster_load_failure_is_actionable(monkeypatch):
    from our_teams import players

    monkeypatch.setattr(
        players, "ROSTER_LOAD_ERROR", players.RosterError("missing workbook")
    )
    with pytest.raises(players.RosterError, match="missing workbook"):
        players.player_entries()


def test_roster_validator_is_read_only(capsys):
    from handy_tools.validate_roster import validate

    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "squadofsunrisers.xlsx",
    )
    with open(path, "rb") as workbook:
        before = hashlib.sha256(workbook.read()).hexdigest()
    assert validate(path) is True
    with open(path, "rb") as workbook:
        after = hashlib.sha256(workbook.read()).hexdigest()
    assert before == after
    assert "Roster OK" in capsys.readouterr().out


def test_source_list_is_complete_and_unique():
    from news_collectors.collect_news import NEWS_WEBSITES

    assert len(NEWS_WEBSITES) == 268
    assert len({feed["url"] for feed in NEWS_WEBSITES}) == 268
    assert len({feed["name"] for feed in NEWS_WEBSITES}) == 268


def test_removed_dashboard_and_bot_modules_are_gone():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for removed in (
        "app.py", "phone_bot.py", "bot.py",
        "our_teams/website_look.py",
        "news_collectors/find_matches.py",
        "news_collectors/backup_news_finder.py",
        "helpers/match_cards.py",
    ):
        assert not os.path.exists(os.path.join(root, removed)), removed
    import sys
    import regular_checks.check_news  # noqa: F401
    assert "streamlit" not in sys.modules
