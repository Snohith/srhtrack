"""One scheduled collection + delivery cycle (the production entry point).

Run with:
    python -m regular_checks.check_news

Cron calls that same command every five minutes.  A non-blocking file lock
prevents overlapping runs; SQLite unique constraints and atomic delivery
claims are the second line of defence.
"""
from __future__ import annotations

import argparse
import os
import sys
import traceback
from contextlib import contextmanager

from helpers.config import load_env
from helpers.log_books import configure_logs, news_diary, problems_diary
from helpers.phone_alerts import (
    are_phone_alerts_ready,
    send_pending_alerts,
    send_test_message,
)
from news_collectors.collect_news import collect_fresh_stories
from our_teams.players import RosterError, player_entries, reload_roster
from saved_stories.story_storage import (
    article_count,
    database_path,
    delivery_counts,
    prune_expired,
    retry_failed_deliveries,
    set_up_story_box,
)

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None


@contextmanager
def collector_lock():
    """Yield True when this process owns the lock, False if another run does."""
    lock_path = database_path() + ".lock"
    os.makedirs(os.path.dirname(os.path.abspath(lock_path)), exist_ok=True)
    handle = open(lock_path, "a+")
    acquired = True
    try:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                acquired = False
        if acquired:
            handle.seek(0)
            handle.truncate()
            handle.write(str(os.getpid()))
            handle.flush()
        yield acquired
    finally:
        if acquired and fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def _print_status():
    set_up_story_box()
    counts = delivery_counts()
    print(f"database: {database_path()}")
    print(f"articles: {article_count()}")
    print(
        "alerts: "
        f"{counts['pending']} pending, {counts['sending']} sending, "
        f"{counts['sent']} sent, {counts['failed']} failed"
    )
    print(f"telegram: {'ready' if are_phone_alerts_ready() else 'not configured'}")


def main(argv=None):
    try:
        load_env()
        configure_logs()
    except (OSError, RuntimeError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(description="Run one SRHXtra news cycle.")
    parser.add_argument("--test-telegram", action="store_true",
                        help="send one explicit test message and exit")
    parser.add_argument("--status", action="store_true",
                        help="print database and delivery counts and exit")
    parser.add_argument("--retry-failed", action="store_true",
                        help="reset terminally failed alerts to pending before sending")
    args = parser.parse_args(argv)

    if args.test_telegram:
        if not are_phone_alerts_ready():
            print(
                "Telegram is not configured. Set TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_CHAT_ID in .env or the environment."
            )
            return 2
        result = send_test_message()
        print("Test message sent." if result.ok else f"Test message failed: {result.error}")
        return 0 if result.ok else 1

    if args.status:
        try:
            _print_status()
            return 0
        except Exception as exc:
            print(f"Status failed: {exc}")
            return 1

    with collector_lock() as acquired:
        if not acquired:
            print("Another SRHXtra collector run is already in progress; exiting.")
            return 0
        try:
            reload_roster()  # pick up SUNRISERS_ROSTER_PATH from .env if needed
            player_entries()  # fail early with a clear roster message
            set_up_story_box()
            if args.retry_failed:
                reset = retry_failed_deliveries()
                print(f"Reset {reset} failed alert(s) to pending.")
            result = collect_fresh_stories()
            alerts = send_pending_alerts()
            prune_expired()
            counts = delivery_counts()
            summary = (
                f"SRHXtra cycle: {result.inserted} new, {result.duplicates} duplicate, "
                f"{result.stale} stale, {result.invalid_links} bad link(s); "
                f"feeds {result.polled_feeds - len(result.failed_feeds)} ok / "
                f"{len(result.failed_feeds)} failed / {result.skipped_feeds} backoff; "
                f"alerts {alerts['sent']} sent, {alerts['retried']} retry, "
                f"{alerts['failed']} failed, {counts['pending']} pending."
            )
            news_diary.info(summary)
            print(summary)
            if not are_phone_alerts_ready():
                print(
                    "Telegram is not configured; articles are stored and alerts stay pending. "
                    "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID."
                )
            return 0
        except RosterError as exc:
            problems_diary.error(f"Roster error: {exc}")
            print(f"Roster error: {exc}", file=sys.stderr)
            return 2
        except KeyboardInterrupt:
            return 130
        except Exception as exc:
            problems_diary.error(f"Cycle failed: {type(exc).__name__}: {exc}")
            problems_diary.error(traceback.format_exc())
            print(f"Cycle failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(main())
