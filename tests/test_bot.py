"""
Command-bot + matchday-card tests (no network, no production DB).
"""
import threading
import time
from datetime import datetime

import bot
from bot import CommandBot, is_owner, parse_command
from utils.matchday_cards import (
    build_roster_franchise_map,
    fixture_day_label,
    format_match_card,
    format_matches_message,
    parse_fixture_dt,
)


def _bot(**kw):
    b = CommandBot.__new__(CommandBot)
    b.token, b.owner, b.mode, b.interval = "t", "123", "per_article", 900
    b._run_cycle = kw.get("run_cycle", lambda: None)
    b._matches_fn = kw.get("matches_fn")
    b._lock = threading.Lock()
    b.sent = []
    b.send = lambda text: (b.sent.append(text), True)[1]
    return b


def _update(chat_id="123", text="/refresh", uid=1):
    return {"update_id": uid, "message": {"chat": {"id": chat_id}, "text": text}}


def _fx(status="LIVE", team1="WACA", team2="QLD", players=None,
        day="October 13, 2026", time="12:00 PM IST", **kw):
    d = {
        "team1": team1, "team2": team2, "series": "WBBL", "match_no": "12th Match",
        "league": "WBBL · 12th Match", "venue": "WACA Ground",
        "broadcast": "Check Crex for stream",
        "date_str": day, "time": time, "day_name": "Mon", "status": status,
        "srh_players": players if players is not None else ["Annabel Sutherland"],
        "franchises": ["Sunrisers Leeds Women"],
        "link": "https://crex.com/m/1", "players": "", "vs": team2,
        "squad": team1, "source": "CREX Live Schedule",
    }
    d.update(kw)
    return d


NOW = datetime(2026, 10, 13, 16, 0)


def test_parse_command_variants():
    assert parse_command("/refresh") == "refresh"
    assert parse_command("/matches") == "matches"
    assert parse_command("/matches@srhxtrafeedbot") == "matches"
    assert parse_command("/STATUS") == "status"
    assert parse_command("/start") == "start"
    assert parse_command("hello") is None
    assert parse_command("/unknown") is None
    assert parse_command("") is None
    assert parse_command(None) is None


def test_stranger_is_silently_ignored():
    b = _bot()
    assert b.handle_update(_update(chat_id="999", text="/refresh")) == "ignored"
    assert b.handle_update(_update(chat_id="999", text="/matches")) == "ignored"
    assert b.sent == []


def test_owner_mismatch_types_still_match():
    assert is_owner(123, "123") is True
    assert is_owner("", "123") is False


def test_start_and_status_reply():
    b = _bot()
    assert b.handle_update(_update(text="/start")) == "start"
    assert "/matches" in b.sent[-1] and "/refresh" in b.sent[-1]
    import database.db_manager as dm
    orig = dm.get_analytics_summary
    dm.get_analytics_summary = lambda: {"total_news": 5, "total_players": 88}
    try:
        assert b.handle_update(_update(text="/status")) == "status"
    finally:
        dm.get_analytics_summary = orig
    assert "88" in b.sent[-1]


def test_refresh_runs_cycle_and_replies():
    calls = []

    def _cycle():
        calls.append(1)

        class _R:
            inserted = 3
            failed_feeds = ["x"]

        return _R()

    b = _bot(run_cycle=_cycle)
    assert b.handle_update(_update(text="/refresh")) == "refreshing"
    deadline = time.time() + 5
    while not calls and time.time() < deadline:
        time.sleep(0.05)
    deadline = time.time() + 5
    while len(b.sent) < 2 and time.time() < deadline:
        time.sleep(0.05)
    assert calls == [1]
    assert "Sweeping 193 feeds" in b.sent[0]
    assert "+3 new stories" in b.sent[1]


def test_second_refresh_while_busy():
    started = threading.Event()

    def _slow():
        started.set()
        time.sleep(2)

        class _R:
            inserted = 0
            failed_feeds = []

        return _R()

    b = _bot(run_cycle=_slow)
    assert b.cmd_refresh() == "refreshing"
    assert started.wait(timeout=5)
    assert b.cmd_refresh() == "busy"
    assert "already running" in b.sent[-1]


def test_matches_live_first_with_ist_and_players():
    live = _fx(status="LIVE", players=["Abhishek Sharma", "Heinrich Klaasen"])
    upcoming = _fx(status="UPCOMING", team1="SRH", team2="MI",
                   day="October 14, 2026", time="7:30 PM IST",
                   players=["Abhishek Sharma"], link="https://crex.com/m/2")
    b = _bot(matches_fn=lambda: [upcoming, live])  # deliberately unsorted
    assert b.handle_update(_update(text="/matches")) == "matches"
    text = b.sent[-1]
    assert text.index("LIVE NOW") < text.index("Coming up")
    assert "WACA vs QLD" in text and "SRH vs MI" in text
    assert "Abhishek Sharma" in text and "(Sunrisers Hyderabad ×2)" in text
    assert "https://crex.com/m/1" in text
    # Exact IST day labels, clock injected (Bot path uses real now).
    live_text = format_matches_message([live], NOW)
    assert "Today, October 13, 2026 · 12:00 PM IST" in live_text
    up_text = format_matches_message([upcoming], NOW)
    assert "Tomorrow, October 14, 2026 · 7:30 PM IST" in up_text


def test_matches_empty_state_and_fetch_failure():
    b = _bot(matches_fn=lambda: [])
    assert b.handle_update(_update(text="/matches")) == "matches"
    assert "No Sunrisers fixtures live" in b.sent[-1]
    assert "crex.com/schedule" in b.sent[-1]

    def _boom():
        raise RuntimeError("crex down")

    b2 = _bot(matches_fn=_boom)
    assert b2.handle_update(_update(text="/matches")) == "matches"  # never raises
    assert "No Sunrisers fixtures live" in b2.sent[-1]


def test_match_card_escaping_caps_and_labels():
    evil = _fx(team1='<script>alert("x")</script>', venue="A&B Arena",
               players=[f"P{i}" for i in range(8)])
    text = format_match_card(evil, NOW, {})
    assert "<script>" not in text and "&lt;script&gt;" in text
    assert "A&amp;B Arena" in text
    assert "+2 more" in text  # 8 players, 6 shown
    assert parse_fixture_dt({"date_str": "October 13, 2026", "time": "12:00 PM IST"})
    assert parse_fixture_dt({"date_str": "bogus", "time": "xx"}) is None
    assert fixture_day_label(datetime(2026, 10, 13, 9), NOW) == "Today"
    assert fixture_day_label(datetime(2026, 10, 14, 9), NOW) == "Tomorrow"
    assert fixture_day_label(datetime(2026, 10, 20, 9), NOW) == "Tue, Oct 20"
    assert fixture_day_label(None, NOW) == ""


def test_upcoming_cap_and_roster_map():
    fixtures = [
        _fx(status="UPCOMING", team1=f"T{i}", day="October 14, 2026",
            time="7:30 PM IST", link=f"https://crex.com/m/{i}")
        for i in range(6)
    ]
    text = format_matches_message(fixtures, NOW)
    assert "+2 more in the 4-day window." in text
    assert "https://crex.com/m/5" not in text  # only first 4 shown
    assert build_roster_franchise_map().get("Abhishek Sharma") == "Sunrisers Hyderabad"
