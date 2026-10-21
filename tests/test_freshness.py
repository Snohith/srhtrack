"""Regression tests for stale-article delays (Oct 2026 incident).

Incident: a Cricbuzz evergreen page ("Heinrich Klaasen Auction Price & Team -
SA20 2027") was delivered by Telegram as "Fresh" ~19h after its Google News
timestamp (Oct 13 @ 10:52 PM IST -> Oct 14 @ 5:32 PM), and the same title had
already been ingested on Oct 8 / Oct 13. Root causes guarded here:

1. Google News re-stamps evergreen pages in place (same CBM link, mutated
   pubDate), so the 24h age filter keeps passing them.
2. The 24h news purge wipes the display row, so a re-stamped story re-inserts
   AND re-alerts as if new.
3. The Telegram header claims "Fresh" unconditionally, even for ~19h-old
   catch-up deliveries and entries with no timestamp at all.
"""
import time
from contextlib import closing

import pytest

from helpers import phone_alerts as tg

KLAASEN_TITLE = "Heinrich Klaasen Auction Price & Team - SA20 2027 - Cricbuzz"
KLAASEN_LINK = "https://news.google.com/rss/articles/CBMiXklaasen-test?oc=5"

ARTICLE = {
    "title": "Abhishek Sharma smashes fifty",
    "source": "Test Source",
    "summary": "Fifty off 30 balls.",
    "link": "https://example.com/story-1",
    "published_at": "Oct 13, 2026 @ 10:00 AM IST",
    "player_name": "Abhishek Sharma",
    "franchise": "Sunrisers Hyderabad",
}


@pytest.fixture()
def isolated_db(monkeypatch, tmp_path):
    """Fresh private SQLite file per test (never touches the suite-shared DB)."""
    db = str(tmp_path / "freshness.db")
    monkeypatch.setenv("SRH_DB_PATH", db)
    from saved_stories import story_storage as db_manager
    db_manager.set_up_story_box()
    return db


@pytest.fixture()
def tg_env(monkeypatch):
    """Hermetic Telegram env: configured per-article by default."""
    monkeypatch.setenv("TELEGRAM_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setenv("TELEGRAM_MODE", "per_article")
    monkeypatch.setenv("TELEGRAM_MAX_ALERTS_PER_CYCLE", "10")
    monkeypatch.setattr(tg, "_fetch_og_image", lambda url, timeout=5: None)
    return monkeypatch


# ── Slice 1: title normalization ──────────────────────────────────────────

def test_title_normalization_folds_case_whitespace_and_dashes():
    from saved_stories.story_storage import make_title_simple_to_compare
    a = make_title_simple_to_compare(KLAASEN_TITLE)
    b = make_title_simple_to_compare("heinrich  klaasen auction price & team \u2013 SA20 2027 \u2013 cricbuzz")
    assert a == b
    assert make_title_simple_to_compare("Totally Different Story - Cricbuzz") != a


# ── Slice 2: 14-day alert memory ──────────────────────────────────────────

def test_alert_slot_claimed_once_per_target(isolated_db):
    from saved_stories.story_storage import make_title_simple_to_compare, claim_phone_alert_once
    norm = make_title_simple_to_compare(KLAASEN_TITLE)
    assert claim_phone_alert_once(norm, "Heinrich Klaasen", "Sunrisers Hyderabad") is True
    assert claim_phone_alert_once(norm, "Heinrich Klaasen", "Sunrisers Hyderabad") is False


def test_alert_memory_is_per_target(isolated_db):
    from saved_stories.story_storage import make_title_simple_to_compare, claim_phone_alert_once
    norm = make_title_simple_to_compare("Abhishek Sharma and Heinrich Klaasen star")
    assert claim_phone_alert_once(norm, "Abhishek Sharma", "Sunrisers Hyderabad") is True
    assert claim_phone_alert_once(norm, "Heinrich Klaasen", "Sunrisers Hyderabad") is True


def test_alert_memory_survives_news_purge(isolated_db):
    """The exact incident: news row purged after 24h, re-stamp re-inserts the
    display row but must NOT win a second Telegram alert."""
    from saved_stories import story_storage as dm
    norm = dm.make_title_simple_to_compare(KLAASEN_TITLE)
    assert dm.claim_phone_alert_once(norm, "Heinrich Klaasen", "Sunrisers Hyderabad") is True
    with closing(dm.open_story_box()) as conn:
        conn.execute("DELETE FROM news")
        conn.commit()
    assert dm.claim_phone_alert_once(norm, "Heinrich Klaasen", "Sunrisers Hyderabad") is False


def test_alert_slot_expires_after_memory_window(isolated_db):
    from saved_stories.story_storage import make_title_simple_to_compare, claim_phone_alert_once
    norm = make_title_simple_to_compare(KLAASEN_TITLE)
    old = time.time() - 15 * 24 * 3600
    assert claim_phone_alert_once(norm, "Heinrich Klaasen", "Sunrisers Hyderabad", seen_ts=old) is True
    assert claim_phone_alert_once(norm, "Heinrich Klaasen", "Sunrisers Hyderabad") is True


# ── Slice 3: ingest wiring ────────────────────────────────────────────────

def _wire_collector(monkeypatch, entry, age_hours=1.0, pub_ts=1000.0):
    from news_collectors import collect_news as rc
    monkeypatch.setattr(
        rc, "NEWS_WEBSITES",
        [{"name": "Google News: Heinrich Klaasen", "url": "https://example.com/fake"}],
    )
    monkeypatch.setattr(rc, "_poll_one_source", lambda fi: (fi, [dict(entry)], None))
    monkeypatch.setattr(
        rc, "find_our_players_in_story",
        lambda t: [{"player_name": "Heinrich Klaasen", "franchise": "Sunrisers Hyderabad"}],
    )
    monkeypatch.setattr(
        rc, "read_story_date_as_indian_time",
        lambda e: ("Oct 13, 2026 @ 10:52 PM IST", age_hours, pub_ts),
    )
    sent = []
    monkeypatch.setattr(
        "helpers.phone_alerts.tell_phones_about_new_stories",
        lambda arts, stats=None: (
            sent.append(list(arts)),
            {"sent": len(arts), "mode": "per_article", "reason": "ok"},
        )[1],
    )
    return rc, sent


def test_restamped_story_does_not_realert_after_purge(isolated_db, monkeypatch):
    """End-to-end incident replay: ingest -> purge display row -> re-ingest the
    same Google re-stamp. Display row returns, Telegram stays silent."""
    from saved_stories import story_storage as dm
    entry = {
        "title": KLAASEN_TITLE,
        "summary": "Evergreen auction tracker.",
        "link": KLAASEN_LINK,
        "published_parsed": time.gmtime(time.time() - 3600),
    }
    rc, sent = _wire_collector(monkeypatch, entry)
    res1 = rc.collect_fresh_stories()
    assert len(sent) == 1 and len(sent[0]) == 1
    with closing(dm.open_story_box()) as conn:
        conn.execute("DELETE FROM news")  # simulate the 24h retention purge
        conn.commit()
    res2 = rc.collect_fresh_stories()
    assert int(res2) == 1  # display row re-stored for the dashboard
    assert res2.new_articles == []  # ...but no second Telegram alert
    assert sent[-1] == []


def test_new_story_for_same_player_still_alerts(isolated_db, monkeypatch):
    entry = {
        "title": KLAASEN_TITLE,
        "summary": "S",
        "link": KLAASEN_LINK,
        "published_parsed": time.gmtime(time.time() - 3600),
    }
    rc, sent = _wire_collector(monkeypatch, entry)
    rc.collect_fresh_stories()
    entry2 = dict(entry, title="Heinrich Klaasen smashes unbeaten ton",
                  link="https://news.google.com/rss/articles/CBMiXton-test?oc=5")
    monkeypatch.setattr(rc, "_poll_one_source", lambda fi: (fi, [entry2], None))
    res = rc.collect_fresh_stories()
    assert len(res.new_articles) == 1


def test_alert_candidates_carry_age_and_sort_newest_first(isolated_db, monkeypatch):
    from news_collectors import collect_news as rc
    old = {"title": "Old story for Klaasen", "summary": "S",
           "link": "https://news.google.com/rss/articles/CBMiXold?oc=5",
           "published_parsed": time.gmtime(time.time() - 20 * 3600)}
    new = {"title": "New story for Klaasen", "summary": "S",
           "link": "https://news.google.com/rss/articles/CBMiXnew?oc=5",
           "published_parsed": time.gmtime(time.time() - 3600)}
    monkeypatch.setattr(
        rc, "NEWS_WEBSITES",
        [{"name": "Google News: Heinrich Klaasen", "url": "https://example.com/fake"}],
    )
    monkeypatch.setattr(rc, "_poll_one_source", lambda fi: (fi, [old, new], None))
    monkeypatch.setattr(
        rc, "find_our_players_in_story",
        lambda t: [{"player_name": "Heinrich Klaasen", "franchise": "Sunrisers Hyderabad"}],
    )
    def _ages(entry):
        if "Old story" in entry["title"]:
            return ("Oct 13, 2026 @ 10:00 PM IST", 20.0, 1000.0)
        return ("Oct 14, 2026 @ 05:00 PM IST", 1.0, 2000.0)
    monkeypatch.setattr(rc, "read_story_date_as_indian_time", _ages)
    sent = []
    monkeypatch.setattr(
        "helpers.phone_alerts.tell_phones_about_new_stories",
        lambda arts, stats=None: (
            sent.append(list(arts)),
            {"sent": len(arts), "mode": "per_article", "reason": "ok"},
        )[1],
    )
    rc.collect_fresh_stories()
    assert [a["title"] for a in sent[0]] == ["New story for Klaasen", "Old story for Klaasen"]
    assert sent[0][0]["age_hours"] == 1.0
    assert sent[0][1]["age_hours"] == 20.0


def test_multi_target_story_claims_every_slot(isolated_db, monkeypatch):
    """One story matching 2 players alerts once but claims both slots, so a
    post-purge re-ingest stays silent for every target."""
    from saved_stories import story_storage as dm
    from news_collectors import collect_news as rc
    entry = {
        "title": "Abhishek Sharma and Heinrich Klaasen star for Sunrisers",
        "summary": "S",
        "link": "https://news.google.com/rss/articles/CBMiXduo?oc=5",
        "published_parsed": time.gmtime(time.time() - 3600),
    }
    monkeypatch.setattr(
        rc, "NEWS_WEBSITES",
        [{"name": "Google News: SRH", "url": "https://example.com/fake"}],
    )
    monkeypatch.setattr(rc, "_poll_one_source", lambda fi: (fi, [dict(entry)], None))
    monkeypatch.setattr(
        rc, "find_our_players_in_story",
        lambda t: [
            {"player_name": "Abhishek Sharma", "franchise": "Sunrisers Hyderabad"},
            {"player_name": "Heinrich Klaasen", "franchise": "Sunrisers Hyderabad"},
        ],
    )
    monkeypatch.setattr(
        rc, "read_story_date_as_indian_time", lambda e: ("Oct 14, 2026 @ 05:00 PM IST", 1.0, 2000.0))
    sent = []
    monkeypatch.setattr(
        "helpers.phone_alerts.tell_phones_about_new_stories",
        lambda arts, stats=None: (
            sent.append(list(arts)),
            {"sent": len(arts), "mode": "per_article", "reason": "ok"},
        )[1],
    )
    res1 = rc.collect_fresh_stories()
    assert len(sent[0]) == 1  # single alert for the shared story
    with closing(dm.open_story_box()) as conn:
        conn.execute("DELETE FROM news")  # simulate the 24h retention purge
        conn.commit()
    res2 = rc.collect_fresh_stories()
    assert int(res2) == 2  # both per-target display rows re-stored
    assert res2.new_articles == []  # ...but neither target re-alerts


# ── Slice 5: outlet-suffix near-duplicates (direct feed vs Google mirror) ──


def test_title_normalization_strips_outlet_suffix():
    from saved_stories.story_storage import make_title_simple_to_compare
    direct = "Proteas Player Ratings: Markram outstanding, but Rickelton and Stubbs fail the test"
    mirror = "Proteas Player Ratings: Markram outstanding, but Rickelton and Stubbs fail the test - IOL"
    assert make_title_simple_to_compare(direct) == make_title_simple_to_compare(mirror)
    assert (
        make_title_simple_to_compare("Heinrich Klaasen Auction Price & Team - SA20 2027 - Cricbuzz")
        == make_title_simple_to_compare("Heinrich Klaasen Auction Price & Team - SA20 2027")
    )


def test_title_normalization_keeps_distinct_endings():
    from saved_stories.story_storage import make_title_simple_to_compare
    first = make_title_simple_to_compare("Match tied - 1st T20I")
    second = make_title_simple_to_compare("Match tied - 2nd T20I")
    assert first != second  # digit endings distinguish real fixtures
    long_title = "IND vs WI Prediction - Who will win India vs West Indies 4th T20I match?"
    assert make_title_simple_to_compare(long_title).endswith("4th t20i match?")


def test_direct_plus_mirror_alerts_once(isolated_db, monkeypatch):
    """Incident replay: SA IOL News direct item, then the Google mirror of the
    same story 21 min later with ' - IOL' appended. One Telegram alert total."""
    from saved_stories import story_storage as dm
    from news_collectors import collect_news as rc
    direct = {
        "title": "Proteas Player Ratings: Markram outstanding, but Rickelton and Stubbs fail the test",
        "summary": "S",
        "link": "https://www.iol.co.za/proteas-ratings-123",
        "published_parsed": time.gmtime(time.time() - 2 * 3600),
    }
    mirror = {
        "title": "Proteas Player Ratings: Markram outstanding, but Rickelton and Stubbs fail the test - IOL",
        "summary": "S",
        "link": "https://news.google.com/rss/articles/CBMiXiOL?oc=5",
        "published_parsed": time.gmtime(time.time() - 3600),
    }
    monkeypatch.setattr(
        rc, "NEWS_WEBSITES",
        [{"name": "SA IOL News", "url": "https://example.com/fake"}],
    )
    monkeypatch.setattr(rc, "_poll_one_source", lambda fi: (fi, [dict(direct)], None))
    monkeypatch.setattr(
        rc, "find_our_players_in_story",
        lambda t: [{"player_name": "Tristan Stubbs", "franchise": "Sunrisers Eastern Cape"}],
    )
    monkeypatch.setattr(
        rc, "read_story_date_as_indian_time", lambda e: ("Oct 13, 2026 @ 07:00 PM IST", 2.0, 1000.0))
    sent = []
    monkeypatch.setattr(
        "helpers.phone_alerts.tell_phones_about_new_stories",
        lambda arts, stats=None: (
            sent.append(list(arts)),
            {"sent": len(arts), "mode": "per_article", "reason": "ok"},
        )[1],
    )
    rc.collect_fresh_stories()
    assert len(sent[0]) == 1
    monkeypatch.setattr(rc, "_poll_one_source", lambda fi: (fi, [dict(mirror)], None))
    monkeypatch.setattr(
        rc, "read_story_date_as_indian_time", lambda e: ("Oct 13, 2026 @ 07:21 PM IST", 1.0, 2000.0))
    res = rc.collect_fresh_stories()
    assert res.new_articles == []
    assert sent[-1] == []


# ── Slice 6: stale backlog collapses into one catch-up digest ─────────────


def _notify_setup(monkeypatch, tg_env):
    calls = []

    def _post(url, **kwargs):
        body = kwargs.get("json")
        calls.append({"url": url, "body": body})

        class _Resp:
            status_code = 200

            @staticmethod
            def json():
                return {"ok": True}

        return _Resp()

    monkeypatch.setattr(tg.requests, "post", _post)
    return calls


def test_mixed_fresh_and_stale_sends_cards_plus_catchup_digest(tg_env, monkeypatch):
    calls = _notify_setup(monkeypatch, tg_env)
    fresh = {**ARTICLE, "age_hours": 1.0}
    stale = {**ARTICLE, "title": "Day-old story", "age_hours": 20.0}
    res = tg.tell_phones_about_new_stories([stale, fresh])
    assert res["sent"] == 2
    texts = [c["body"]["text"] for c in calls]
    assert len(calls) == 2
    assert "Day-old story" not in texts[0]  # stale must not get its own card
    assert "📦" in texts[1] and "Day-old story" in texts[1]  # one catch-up digest
    assert calls[0]["url"].endswith("/sendMessage")  # fresh card first


def test_all_stale_cycle_sends_only_digest(tg_env, monkeypatch):
    calls = _notify_setup(monkeypatch, tg_env)
    stale = [
        {**ARTICLE, "title": f"Old story {i}", "age_hours": 10.0 + i}
        for i in range(3)
    ]
    res = tg.tell_phones_about_new_stories(stale)
    assert res["sent"] == 1 and res["reason"] == "ok"
    assert "Catch-up" in calls[0]["body"]["text"]


def test_ageless_articles_still_go_per_article(tg_env, monkeypatch):
    calls = _notify_setup(monkeypatch, tg_env)
    res = tg.tell_phones_about_new_stories([ARTICLE])
    assert res["sent"] == 1
    assert "SRHXtra · Fresh" in calls[0]["body"]["text"]

# ── Slice 4: honest Telegram headers ──────────────────────────────────────

def test_nineteen_hour_old_article_is_labeled_catchup():
    card = tg.write_story_card_for_phone({**ARTICLE, "age_hours": 18.6})
    assert "Catch-up" in card and "19h old" in card
    assert "SRHXtra · Fresh" not in card


def test_fresh_article_keeps_fresh_label():
    card = tg.write_story_card_for_phone({**ARTICLE, "age_hours": 1.0})
    assert "SRHXtra · Fresh" in card


def test_missing_timestamp_is_not_called_fresh():
    card = tg.write_story_card_for_phone({**ARTICLE, "age_hours": None})
    assert "SRHXtra · Fresh" not in card


def test_legacy_articles_without_age_stay_fresh():
    assert "SRHXtra · Fresh" in tg.write_story_card_for_phone(ARTICLE)


def test_photo_caption_mirrors_header_honesty():
    assert "Catch-up" in tg.format_photo_caption({**ARTICLE, "age_hours": 18.6})
    assert "SRHXtra · Fresh" in tg.format_photo_caption({**ARTICLE, "age_hours": 1.0})
