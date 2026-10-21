"""Production entry point: ordering, locking, and failure messages."""
from __future__ import annotations

from contextlib import contextmanager

import pytest

from helpers.phone_alerts import SendResult
from regular_checks import check_news


class FakeCollection:
    inserted = 1
    duplicates = 0
    stale = 0
    invalid_links = 0
    polled_feeds = 1
    skipped_feeds = 0
    failed_feeds = []


@contextmanager
def _owned_lock():
    yield True


@contextmanager
def _busy_lock():
    yield False


def _patch_cycle(monkeypatch, calls):
    monkeypatch.setattr(check_news, "load_env", lambda: calls.append("env"))
    monkeypatch.setattr(
        check_news, "player_entries", lambda: calls.append("roster") or []
    )
    monkeypatch.setattr(
        check_news, "set_up_story_box", lambda: calls.append("schema")
    )
    monkeypatch.setattr(
        check_news,
        "collect_fresh_stories",
        lambda: calls.append("collect") or FakeCollection(),
    )
    monkeypatch.setattr(
        check_news,
        "send_pending_alerts",
        lambda: calls.append("send") or {"sent": 1, "retried": 0, "failed": 0},
    )
    monkeypatch.setattr(
        check_news, "prune_expired", lambda: calls.append("prune") or {}
    )
    monkeypatch.setattr(
        check_news,
        "delivery_counts",
        lambda: {"pending": 0, "sending": 0, "sent": 1, "failed": 0, "total": 1},
    )
    monkeypatch.setattr(check_news, "are_phone_alerts_ready", lambda: True)
    monkeypatch.setattr(check_news, "collector_lock", _owned_lock)


def test_cycle_runs_in_order_and_returns_success(monkeypatch, capsys):
    calls = []
    _patch_cycle(monkeypatch, calls)

    assert check_news.main([]) == 0
    assert calls == ["env", "roster", "schema", "collect", "send", "prune"]
    out = capsys.readouterr().out
    assert "SRHXtra cycle: 1 new" in out
    assert "alerts 1 sent" in out


def test_busy_lock_skips_the_cycle(monkeypatch):
    calls = []
    _patch_cycle(monkeypatch, calls)
    monkeypatch.setattr(check_news, "collector_lock", _busy_lock)

    assert check_news.main([]) == 0
    assert "collect" not in calls


def test_roster_error_is_reported_without_collecting(monkeypatch, capsys):
    calls = []
    _patch_cycle(monkeypatch, calls)

    def broken_roster():
        raise check_news.RosterError("missing workbook")

    monkeypatch.setattr(check_news, "player_entries", broken_roster)

    assert check_news.main([]) == 2
    assert "collect" not in calls
    assert "Roster error: missing workbook" in capsys.readouterr().err


def test_retry_failed_happens_before_collection(monkeypatch):
    calls = []
    _patch_cycle(monkeypatch, calls)
    monkeypatch.setattr(
        check_news,
        "retry_failed_deliveries",
        lambda: calls.append("retry") or 2,
    )

    assert check_news.main(["--retry-failed"]) == 0
    assert calls.index("retry") < calls.index("collect")


def test_status_does_not_run_the_collector(monkeypatch, capsys):
    monkeypatch.setattr(check_news, "load_env", lambda: None)
    monkeypatch.setattr(check_news, "set_up_story_box", lambda: None)
    monkeypatch.setattr(check_news, "article_count", lambda: 7)
    monkeypatch.setattr(
        check_news,
        "delivery_counts",
        lambda: {"pending": 2, "sending": 0, "sent": 4, "failed": 1, "total": 7},
    )
    monkeypatch.setattr(check_news, "are_phone_alerts_ready", lambda: False)
    monkeypatch.setattr(
        check_news, "collect_fresh_stories", lambda: pytest.fail("must not collect")
    )

    assert check_news.main(["--status"]) == 0
    out = capsys.readouterr().out
    assert "articles: 7" in out
    assert "2 pending, 0 sending, 4 sent, 1 failed" in out
    assert "telegram: not configured" in out


def test_test_telegram_stops_before_collection(telegram_env, monkeypatch):
    monkeypatch.setattr(check_news, "load_env", lambda: None)
    monkeypatch.setattr(check_news, "are_phone_alerts_ready", lambda: True)
    monkeypatch.setattr(
        check_news, "send_test_message", lambda: SendResult(ok=True)
    )
    monkeypatch.setattr(
        check_news, "collect_fresh_stories", lambda: pytest.fail("must not collect")
    )

    assert check_news.main(["--test-telegram"]) == 0


def test_test_telegram_without_configuration_returns_2(monkeypatch):
    monkeypatch.setattr(check_news, "load_env", lambda: None)
    monkeypatch.setattr(check_news, "are_phone_alerts_ready", lambda: False)

    assert check_news.main(["--test-telegram"]) == 2


def test_configuration_error_is_reported(monkeypatch, capsys):
    def broken_env():
        raise RuntimeError("cannot read .env")

    monkeypatch.setattr(check_news, "load_env", broken_env)

    assert check_news.main([]) == 2
    assert "Configuration error: cannot read .env" in capsys.readouterr().err


def test_unexpected_cycle_error_returns_1(monkeypatch, capsys):
    calls = []
    _patch_cycle(monkeypatch, calls)

    def broken_collection():
        raise RuntimeError("database locked")

    monkeypatch.setattr(check_news, "collect_fresh_stories", broken_collection)

    assert check_news.main([]) == 1
    assert "Cycle failed: RuntimeError: database locked" in capsys.readouterr().err
