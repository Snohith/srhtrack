"""Telegram formatting and delivery-ledger tests (the HTTP call is always mocked)."""
from __future__ import annotations

import os
import sqlite3
import time

import pytest

from helpers import phone_alerts
from saved_stories.story_storage import (
    MAX_DELIVERY_ATTEMPTS,
    delivery_counts,
    get_delivery,
    save_article,
)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


def _make_article(title="Pat Cummins takes five", link="https://example.com/story"):
    article_id = save_article(
        title,
        "Test Feed",
        "A report about Pat Cummins.",
        link,
        "Oct 21, 2026 @ 10:00 AM IST",
        time.time(),
        ["Pat Cummins"],
        ["Sunrisers Hyderabad"],
        [],
    )
    assert article_id
    return article_id


def _post_calls(monkeypatch, responses):
    calls = []
    queue = list(responses)

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(phone_alerts.requests, "post", fake_post)
    return calls


def _make_due(article_id):
    with sqlite3.connect(os.environ["SUNRISERS_DB_PATH"]) as conn:
        conn.execute(
            "UPDATE deliveries SET next_attempt_ts = 0 WHERE article_id = ?",
            (article_id,),
        )


def test_successful_send_is_marked_sent_and_is_not_resent(telegram_env, monkeypatch):
    article_id = _make_article()
    calls = _post_calls(monkeypatch, [FakeResponse(200, {"ok": True})])
    monkeypatch.setattr(phone_alerts.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        phone_alerts.requests,
        "get",
        lambda *args, **kwargs: pytest.fail("Telegram delivery must not fetch article images"),
    )

    first = phone_alerts.send_pending_alerts()
    assert first == {"claimed": 1, "sent": 1, "retried": 0, "failed": 0, "reason": "ok"}
    assert get_delivery(article_id)["status"] == "sent"
    assert get_delivery(article_id)["sent_at"] is not None
    assert len(calls) == 1
    url, kwargs = calls[0]
    assert "sendMessage" in url
    assert kwargs["json"]["chat_id"] == "12345"
    assert kwargs["json"]["parse_mode"] == "HTML"
    assert kwargs["json"]["link_preview_options"]["url"] == "https://example.com/story"
    assert "Pat Cummins" in kwargs["json"]["text"]

    second = phone_alerts.send_pending_alerts()
    assert second["claimed"] == 0
    assert second["sent"] == 0
    assert len(calls) == 1


def test_network_failure_stays_pending_and_retries_with_backoff(telegram_env, monkeypatch):
    article_id = _make_article()
    calls = _post_calls(
        monkeypatch,
        [ConnectionError("offline"), FakeResponse(200, {"ok": True})],
    )
    monkeypatch.setattr(phone_alerts.time, "sleep", lambda _seconds: None)

    first = phone_alerts.send_pending_alerts()
    assert first["retried"] == 1
    delivery = get_delivery(article_id)
    assert delivery["status"] == "pending"
    assert delivery["attempts"] == 1
    assert delivery["next_attempt_ts"] > time.time()
    assert "ConnectionError" in delivery["last_error"]

    # A retry is only attempted once the backoff expires.
    assert phone_alerts.send_pending_alerts()["claimed"] == 0
    assert len(calls) == 1

    _make_due(article_id)
    second = phone_alerts.send_pending_alerts()
    assert second["sent"] == 1
    assert get_delivery(article_id)["status"] == "sent"
    assert get_delivery(article_id)["attempts"] == 2


def test_delivery_retries_are_bounded(telegram_env, monkeypatch):
    article_id = _make_article()
    calls = _post_calls(
        monkeypatch,
        [ConnectionError("offline")] * MAX_DELIVERY_ATTEMPTS,
    )
    monkeypatch.setattr(phone_alerts.time, "sleep", lambda _seconds: None)

    for attempt in range(1, MAX_DELIVERY_ATTEMPTS + 1):
        _make_due(article_id)
        stats = phone_alerts.send_pending_alerts()
        delivery = get_delivery(article_id)
        assert delivery["attempts"] == attempt
        if attempt < MAX_DELIVERY_ATTEMPTS:
            assert delivery["status"] == "pending"
            assert stats["retried"] == 1
        else:
            assert delivery["status"] == "failed"
            assert stats["failed"] == 1

    assert phone_alerts.send_pending_alerts()["claimed"] == 0
    assert len(calls) == MAX_DELIVERY_ATTEMPTS


def test_rate_limit_uses_retry_after(telegram_env, monkeypatch):
    article_id = _make_article()
    before = time.time()
    _post_calls(
        monkeypatch,
        [FakeResponse(429, {"ok": False, "parameters": {"retry_after": 90}})],
    )

    stats = phone_alerts.send_pending_alerts()

    assert stats["retried"] == 1
    delivery = get_delivery(article_id)
    assert delivery["status"] == "pending"
    assert delivery["next_attempt_ts"] >= before + 90
    assert "rate limited" in delivery["last_error"]


def test_permanent_telegram_error_fails_without_retrying(telegram_env, monkeypatch):
    article_id = _make_article()
    calls = _post_calls(
        monkeypatch,
        [FakeResponse(400, {"ok": False, "description": "Bad Request"})],
    )

    stats = phone_alerts.send_pending_alerts()

    assert stats["failed"] == 1
    assert get_delivery(article_id)["status"] == "failed"
    assert get_delivery(article_id)["attempts"] == 1
    assert phone_alerts.send_pending_alerts()["claimed"] == 0
    assert len(calls) == 1


def test_unconfigured_telegram_leaves_alerts_pending(telegram_env, monkeypatch):
    article_id = _make_article()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    calls = _post_calls(monkeypatch, [])

    stats = phone_alerts.send_pending_alerts()

    assert stats["reason"] == "unconfigured"
    assert stats["claimed"] == 0
    assert get_delivery(article_id)["status"] == "pending"
    assert calls == []


def test_format_escapes_html_and_drops_unsafe_links():
    text = phone_alerts.format_article_alert(
        {
            "title": '<script>alert("x")</script>',
            "summary": "<b>summary</b> & more",
            "source": "A & B",
            "published_at": "",
            "people": ["Pat Cummins"],
            "franchises": ["Sunrisers Hyderabad"],
            "topics": [],
            "link": "javascript:alert(1)",
        }
    )

    assert "<script>" not in text
    assert "&lt;script&gt;" in text
    assert "<b>summary</b>" not in text
    assert "A &amp; B" in text
    assert "href=" not in text
    assert "Read full story" not in text


def test_test_message_does_not_touch_the_delivery_ledger(telegram_env, monkeypatch):
    article_id = _make_article()
    calls = _post_calls(monkeypatch, [FakeResponse(200, {"ok": True})])

    result = phone_alerts.send_test_message()

    assert result.ok is True
    assert len(calls) == 1
    assert delivery_counts()["pending"] == 1
    assert get_delivery(article_id)["status"] == "pending"
