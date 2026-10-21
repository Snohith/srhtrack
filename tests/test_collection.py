"""Collector and delivery-ledger tests (all network access is mocked)."""
from __future__ import annotations

import time
from contextlib import closing

from news_collectors import collect_news
from saved_stories.story_storage import (
    article_count,
    claim_due_deliveries,
    delivery_counts,
    get_article,
    get_delivery,
    open_story_box,
    save_article,
    set_up_story_box,
)


def _entry(title, link, summary="", age_hours=0.0):
    return {
        "title": title,
        "summary": summary,
        "link": link,
        "published_parsed": time.gmtime(time.time() - (age_hours * 3600)),
    }


def _poll_with(entries, monkeypatch):
    """Replace the network worker, not the filtering/storage code."""

    def fake_poll(feed_info):
        return feed_info, entries, None

    monkeypatch.setattr(collect_news, "_poll_one_source", fake_poll)


def _feed(name="Test Feed", url="https://example.com/feed.xml"):
    return {"name": name, "url": url}


def test_feed_download_parses_rss_and_rejects_unsafe_urls(monkeypatch):
    rss = b"""<?xml version="1.0"?>
    <rss version="2.0"><channel><title>Test</title>
      <item><title>Pat Cummins takes five</title>
      <link>https://example.com/rss-story</link>
      <pubDate>Tue, 20 Oct 2026 10:00:00 GMT</pubDate></item>
    </channel></rss>"""
    requested = []

    class Response:
        status_code = 200
        content = rss

    def fake_get(url, **kwargs):
        requested.append(url)
        return Response()

    monkeypatch.setattr(collect_news.requests, "get", fake_get)

    feed, reason = collect_news._download_feed("https://example.com/feed.xml")
    assert reason == ""
    assert feed.entries[0]["title"] == "Pat Cummins takes five"
    assert requested == ["https://example.com/feed.xml"]

    unsafe, reason = collect_news._download_feed("file:///etc/passwd")
    assert unsafe is None
    assert reason == "unsafe feed URL"
    assert requested == ["https://example.com/feed.xml"]


def test_feed_download_does_not_retry_a_client_error(monkeypatch):
    requested = []

    class Response:
        status_code = 404
        content = b""

    def fake_get(url, **kwargs):
        requested.append(url)
        return Response()

    monkeypatch.setattr(collect_news.requests, "get", fake_get)

    feed, reason = collect_news._download_feed(
        "https://example.com/missing.xml", retries=2
    )
    assert feed is None
    assert reason == "HTTP 404"
    assert len(requested) == 1


def test_collector_stores_one_article_and_never_marks_it_sent(monkeypatch):
    feed = _feed()
    _poll_with(
        [
            _entry(
                "Pat Cummins and Heinrich Klaasen star for Sunrisers Hyderabad",
                "https://example.com/story/one",
                "Cummins took wickets and Klaasen made runs.",
            )
        ],
        monkeypatch,
    )

    result = collect_news.collect_fresh_stories(feeds=[feed], max_workers=1)

    assert result.inserted == 1
    assert result.matched == 1
    counts = delivery_counts()
    assert counts["pending"] == 1
    assert counts["sent"] == 0
    article = get_article(1)
    assert set(article["people"]) == {"Pat Cummins", "Heinrich Klaasen"}
    assert article["franchises"] == ["Sunrisers Hyderabad"]
    assert get_delivery(1)["status"] == "pending"

    # A second sweep of the same feed must not create a second article or alert.
    second = collect_news.collect_fresh_stories(feeds=[feed], max_workers=1)
    assert second.inserted == 0
    assert second.duplicates == 1
    assert article_count() == 1
    assert delivery_counts()["pending"] == 1


def test_collector_combines_labels_for_a_multi_franchise_player(monkeypatch):
    _poll_with(
        [_entry("Mitch Marsh signs for Sunrisers Leeds Men", "https://example.com/marsh")],
        monkeypatch,
    )

    result = collect_news.collect_fresh_stories(feeds=[_feed()], max_workers=1)

    assert result.inserted == 1
    article = get_article(1)
    assert article["people"] == ["Mitch Marsh"]
    assert set(article["franchises"]) == {
        "Sunrisers Eastern Cape",
        "Sunrisers Leeds Men",
    }
    assert delivery_counts()["pending"] == 1


def test_collector_skips_stale_stories_and_malformed_links(monkeypatch):
    _poll_with(
        [
            _entry("Pat Cummins old story", "https://example.com/old", age_hours=48),
            _entry("Pat Cummins bad link", "javascript:alert(1)"),
            _entry("Pat Cummins fresh story", "https://example.com/fresh"),
        ],
        monkeypatch,
    )

    result = collect_news.collect_fresh_stories(feeds=[_feed()], max_workers=1)

    assert result.stale == 1
    assert result.invalid_links == 1
    assert result.inserted == 1
    assert article_count() == 1
    assert get_article(1)["link"] == "https://example.com/fresh"


def test_one_broken_feed_does_not_stop_the_sweep_and_is_backed_off(monkeypatch):
    good = _feed("Good Feed", "https://example.com/good.xml")
    bad = _feed("Bad Feed", "https://example.com/bad.xml")
    calls = []

    def fake_poll(feed_info):
        calls.append(feed_info["url"])
        if feed_info["url"] == bad["url"]:
            return feed_info, [], "HTTP 500"
        return feed_info, [_entry("Pat Cummins fresh", "https://example.com/ok")], None

    monkeypatch.setattr(collect_news, "_poll_one_source", fake_poll)

    first = collect_news.collect_fresh_stories(feeds=[good, bad], max_workers=1)
    assert first.inserted == 1
    assert first.failed_feeds == ["Bad Feed"]
    assert first.polled_feeds == 2
    from saved_stories.story_storage import feed_is_due

    assert feed_is_due(good["url"]) is True
    assert feed_is_due(bad["url"]) is False

    calls.clear()
    second = collect_news.collect_fresh_stories(feeds=[good, bad], max_workers=1)
    assert second.skipped_feeds == 1
    assert second.polled_feeds == 1
    assert bad["url"] not in calls


def test_atomic_claims_never_hand_the_same_article_to_two_workers():
    first = save_article(
        "Pat Cummins first", "Test", "", "https://example.com/claim/one",
        "", 1.0, ["Pat Cummins"], ["Sunrisers Hyderabad"], [],
    )
    second = save_article(
        "Pat Cummins second", "Test", "", "https://example.com/claim/two",
        "", 2.0, ["Pat Cummins"], ["Sunrisers Hyderabad"], [],
    )
    assert first and second

    one = claim_due_deliveries(1)
    two = claim_due_deliveries(1)
    three = claim_due_deliveries(1)

    assert [row["id"] for row in one] == [second]
    assert [row["id"] for row in two] == [first]
    assert three == []
    assert get_delivery(first)["status"] == "sending"
    assert get_delivery(second)["status"] == "sending"
    assert get_delivery(first)["attempts"] == 1


def test_stale_send_claim_is_recovered_or_terminally_failed():
    first = save_article(
        "Pat Cummins stale", "Test", "", "https://example.com/stale-one",
        "", 1.0, ["Pat Cummins"], ["Sunrisers Hyderabad"], [],
    )
    second = save_article(
        "Heinrich Klaasen stale", "Test", "", "https://example.com/stale-two",
        "", 2.0, ["Heinrich Klaasen"], ["Sunrisers Hyderabad"], [],
    )
    claim_due_deliveries(2)
    old = time.time() - 16 * 60
    with closing(open_story_box()) as conn:
        conn.execute(
            "UPDATE deliveries SET claimed_at = ?, attempts = 1 WHERE article_id = ?",
            (old, first),
        )
        conn.execute(
            "UPDATE deliveries SET claimed_at = ?, attempts = 5 WHERE article_id = ?",
            (old, second),
        )

    set_up_story_box()

    assert get_delivery(first)["status"] == "pending"
    assert get_delivery(first)["claimed_at"] is None
    assert get_delivery(second)["status"] == "failed"
    assert claim_due_deliveries(1)[0]["id"] == first
