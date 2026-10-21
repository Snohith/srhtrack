"""
Command-bot + matchday-card tests (no network, no production DB).
"""
import threading
import time
from datetime import datetime

import phone_bot as bot
from phone_bot import CommandBot, is_owner, parse_command
from helpers.match_cards import (
    make_player_to_team_list,
    fixture_day_label,
    format_match_card,
    write_match_list_for_phones,
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
    import saved_stories.story_storage as dm
    orig = dm.count_stories_and_players
    dm.count_stories_and_players = lambda: {"total_news": 5, "total_players": 88}
    try:
        assert b.handle_update(_update(text="/status")) == "status"
    finally:
        dm.count_stories_and_players = orig
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
    assert f"Sweeping {bot.FEED_COUNT} feeds" in b.sent[0]
    assert bot.FEED_COUNT == 268  # audited 17 Oct 2026: 193 baseline + 75 deep-scan lanes
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
    live_text = write_match_list_for_phones([live], NOW)
    assert "Today, October 13, 2026 · 12:00 PM IST" in live_text
    up_text = write_match_list_for_phones([upcoming], NOW)
    assert "Tomorrow, October 14, 2026 · 7:30 PM IST" in up_text


def test_matches_empty_state_and_fetch_failure(monkeypatch):
    b = _bot(matches_fn=lambda: [])
    assert b.handle_update(_update(text="/matches")) == "matches"
    assert "No Sunrisers fixtures live" in b.sent[-1]
    assert "crex.com/schedule" in b.sent[-1]

    monkeypatch.setattr(bot.time, "sleep", lambda s: None)
    attempts = []

    def _boom():
        attempts.append(1)
        raise RuntimeError("crex down")

    b2 = _bot(matches_fn=_boom)
    assert b2.handle_update(_update(text="/matches")) == "matches"  # never raises
    assert len(attempts) == 2  # one retry before serving empty state
    assert "No Sunrisers fixtures live" in b2.sent[-1]


def test_matches_retry_recovers_transient_failure(monkeypatch):
    monkeypatch.setattr(bot.time, "sleep", lambda s: None)
    calls = []
    fx = _fx(status="LIVE")

    def _flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("blip")
        return [fx]

    b = _bot(matches_fn=_flaky)
    assert b.handle_update(_update(text="/matches")) == "matches"
    assert "LIVE NOW" in b.sent[-1] and "WACA vs QLD" in b.sent[-1]


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
    text = write_match_list_for_phones(fixtures, NOW)
    assert "+2 more in the 4-day window." in text
    assert "https://crex.com/m/5" not in text  # only first 4 shown
    assert make_player_to_team_list().get("Abhishek Sharma") == "Sunrisers Hyderabad"


def test_weekday_label_does_not_repeat_date():
    weekday = _fx(status="UPCOMING", day="October 16, 2026", time="11:00 AM IST")
    text = format_match_card(weekday, NOW)
    assert "Fri, Oct 16 · 11:00 AM IST" in text
    assert "October 16, 2026" not in text
    today = _fx(status="UPCOMING", day="October 13, 2026", time="12:00 PM IST")
    assert "Today, October 13, 2026 · 12:00 PM IST" in format_match_card(today, NOW)
