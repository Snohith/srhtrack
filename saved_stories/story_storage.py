"""SQLite storage for collected articles and their Telegram delivery ledger.

Two tables matter:
  articles   one row per unique relevant story (dedupe + display data)
  deliveries one row per article (pending -> sending -> sent / retry / failed)

The article insert and its delivery row happen in one transaction.  A story is
never considered delivered until Telegram returns ok; a failed send stays in
the ledger for a bounded retry.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from contextlib import closing

from helpers.links import article_key, canonicalize_url, normalize_title
from helpers.log_books import problems_diary, storage_diary

HERE = os.path.dirname(os.path.abspath(__file__))
TABLES_FILE = os.path.join(HERE, "tables.sql")

MAX_DELIVERY_ATTEMPTS = 5
STALE_CLAIM_SECS = 15 * 60
RETRY_BASE_SECS = 60
RETRY_MAX_SECS = 3600
LEGACY_ALERT_MEMORY_SECS = 14 * 24 * 3600
ARTICLE_RETENTION_SECS = 30 * 24 * 3600
LEGACY_TABLES = (
    "news", "players", "matches", "tweets", "images",
    "notifications", "metadata", "alerted_stories",
)


def _pick_story_file():
    for env_name in ("SUNRISERS_DB_PATH", "SRH_DB_PATH"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    return os.path.join(HERE, "sunrisers_news.db")


def database_path():
    return _pick_story_file()


def open_story_box():
    path = _pick_story_file()
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    return conn


def _table_exists(conn, name):
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _migrate_legacy_tables(conn):
    """Drop the old dashboard tables, preserving recent alert history.

    The old alerted_stories keyed memories by title+target.  We fold those
    titles into suppressed_titles for the remainder of their 14-day life,
    then drop the table.  Old news rows are display-only and may be dropped.
    """
    if _table_exists(conn, "alerted_stories"):
        now = time.time()
        try:
            rows = conn.execute(
                "SELECT title_norm, MAX(first_seen_ts) AS seen "
                "FROM alerted_stories GROUP BY title_norm"
            ).fetchall()
            for row in rows:
                try:
                    seen = float(row["seen"] or 0)
                except (TypeError, ValueError):
                    seen = 0.0
                expires = seen + LEGACY_ALERT_MEMORY_SECS
                if expires > now:
                    conn.execute(
                        "INSERT OR REPLACE INTO suppressed_titles (title_key, expires_ts) "
                        "VALUES (?, ?)",
                        (str(row["title_norm"]), expires),
                    )
        except sqlite3.Error as exc:
            problems_diary.warning(f"Legacy alert migration skipped: {exc}")
    for table in LEGACY_TABLES:
        if _table_exists(conn, table):
            conn.execute(f"DROP TABLE {table}")
            storage_diary.info(f"Dropped legacy table {table}.")


def _recover_stale_claims(conn, now=None):
    now = time.time() if now is None else now
    stale_before = now - STALE_CLAIM_SECS
    conn.execute(
        "UPDATE deliveries SET status = 'failed', claimed_at = NULL, "
        "last_error = 'stale send claim after max attempts', updated_at = ? "
        "WHERE status = 'sending' AND claimed_at IS NOT NULL "
        "AND claimed_at < ? AND attempts >= ?",
        (now, stale_before, MAX_DELIVERY_ATTEMPTS),
    )
    conn.execute(
        "UPDATE deliveries SET status = 'pending', claimed_at = NULL, "
        "next_attempt_ts = ?, updated_at = ? "
        "WHERE status = 'sending' AND claimed_at IS NOT NULL "
        "AND claimed_at < ? AND attempts < ?",
        (now, now, stale_before, MAX_DELIVERY_ATTEMPTS),
    )


def set_up_story_box():
    """Create the schema once and migrate old dashboard tables if present."""
    with closing(open_story_box()) as conn:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        with open(TABLES_FILE, "r", encoding="utf-8") as schema_file:
            conn.executescript(schema_file.read())
        conn.execute("BEGIN IMMEDIATE")
        try:
            _migrate_legacy_tables(conn)
            _recover_stale_claims(conn)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    storage_diary.info("SQLite delivery ledger ready.")


def make_title_simple_to_compare(title):
    return normalize_title(title)


def is_title_suppressed(title_key, now=None):
    now = time.time() if now is None else now
    with closing(open_story_box()) as conn:
        row = conn.execute(
            "SELECT 1 FROM suppressed_titles WHERE title_key = ? AND expires_ts > ?",
            (title_key, now),
        ).fetchone()
    return row is not None


def _json_list(values):
    clean = sorted({str(value).strip() for value in (values or []) if str(value).strip()})
    return json.dumps(clean, ensure_ascii=False)


def save_article(title, source, summary, link, published_at, published_ts,
                 people=None, franchises=None, topics=None):
    """Insert one unique article and its pending delivery row atomically."""
    safe_link = canonicalize_url(link)
    title = str(title or "").strip()
    title_key = normalize_title(title)
    if not safe_link or not title_key:
        return None
    if is_title_suppressed(title_key):
        return None
    dedupe_key = article_key(safe_link, title)
    now = time.time()
    with closing(open_story_box()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            cursor = conn.execute(
                """INSERT INTO articles
                   (dedupe_key, title_key, title, source, summary, link,
                    published_at, published_ts, people, franchises, topics,
                    first_seen_ts)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dedupe_key, title_key, title, str(source or "")[:200],
                    str(summary or "")[:4000], safe_link,
                    str(published_at or ""), float(published_ts or 0.0),
                    _json_list(people), _json_list(franchises),
                    _json_list(topics), now,
                ),
            )
            article_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO deliveries (article_id, status, next_attempt_ts, updated_at) "
                "VALUES (?, 'pending', 0, ?)",
                (article_id, now),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            return None
        except Exception:
            conn.rollback()
            raise
    storage_diary.info(f"Stored article #{article_id}: {title[:80]}")
    return article_id


def _row_to_article(row):
    article = dict(row)
    for field in ("people", "franchises", "topics"):
        try:
            article[field] = json.loads(article.get(field) or "[]")
        except (TypeError, ValueError):
            article[field] = []
    return article


def claim_due_deliveries(limit=1):
    """Atomically claim up to `limit` due deliveries for sending.

    The conditional UPDATE means two processes cannot claim the same article.
    A crash while sending leaves a 'sending' row; it is retried after the stale
    window.  That is the documented rare-duplicate window.
    """
    now = time.time()
    stale_before = now - STALE_CLAIM_SECS
    claimed = []
    with closing(open_story_box()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            rows = conn.execute(
                """SELECT a.*, d.attempts AS delivery_attempts
                   FROM articles a
                   JOIN deliveries d ON d.article_id = a.id
                   WHERE d.attempts < ?
                     AND ((d.status = 'pending' AND d.next_attempt_ts <= ?)
                          OR (d.status = 'sending' AND d.claimed_at IS NOT NULL
                              AND d.claimed_at < ?))
                   ORDER BY a.published_ts DESC, a.id DESC
                   LIMIT ?""",
                (MAX_DELIVERY_ATTEMPTS, now, stale_before, max(1, int(limit))),
            ).fetchall()
            for row in rows:
                cursor = conn.execute(
                    """UPDATE deliveries
                       SET status = 'sending', claimed_at = ?, attempts = attempts + 1,
                           updated_at = ?
                       WHERE article_id = ? AND attempts < ?
                         AND ((status = 'pending' AND next_attempt_ts <= ?)
                              OR (status = 'sending' AND claimed_at IS NOT NULL
                                  AND claimed_at < ?))""",
                    (
                        now, now, row["id"], MAX_DELIVERY_ATTEMPTS,
                        now, stale_before,
                    ),
                )
                if cursor.rowcount == 1:
                    claimed.append(_row_to_article(row))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return claimed


def mark_delivery_sent(article_id):
    now = time.time()
    with closing(open_story_box()) as conn:
        conn.execute(
            "UPDATE deliveries SET status = 'sent', sent_at = ?, claimed_at = NULL, "
            "last_error = NULL, updated_at = ? WHERE article_id = ? AND status = 'sending'",
            (now, now, article_id),
        )


def _retry_delay(attempts, retry_after=None):
    base = RETRY_BASE_SECS * (2 ** max(0, attempts - 1))
    delay = min(RETRY_MAX_SECS, base)
    if retry_after is not None:
        try:
            delay = max(delay, int(float(retry_after)))
        except (TypeError, ValueError):
            pass
    return delay


def mark_delivery_failed(article_id, error, retry_after=None):
    """Keep a failed send pending with backoff, or mark it failed at the cap."""
    now = time.time()
    with closing(open_story_box()) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT status, attempts FROM deliveries WHERE article_id = ?",
                (article_id,),
            ).fetchone()
            if row is None or row["status"] != "sending":
                conn.rollback()
                return "ignored"
            attempts = int(row["attempts"])
            message = str(error or "send failed")[:500]
            if attempts >= MAX_DELIVERY_ATTEMPTS:
                conn.execute(
                    "UPDATE deliveries SET status = 'failed', claimed_at = NULL, "
                    "last_error = ?, updated_at = ? WHERE article_id = ?",
                    (message, now, article_id),
                )
                result = "failed"
            else:
                next_attempt = now + _retry_delay(attempts, retry_after)
                conn.execute(
                    "UPDATE deliveries SET status = 'pending', claimed_at = NULL, "
                    "next_attempt_ts = ?, last_error = ?, updated_at = ? "
                    "WHERE article_id = ?",
                    (next_attempt, message, now, article_id),
                )
                result = "retry"
            conn.commit()
            return result
        except Exception:
            conn.rollback()
            raise


def mark_delivery_dead(article_id, error):
    now = time.time()
    with closing(open_story_box()) as conn:
        conn.execute(
            "UPDATE deliveries SET status = 'failed', claimed_at = NULL, "
            "last_error = ?, updated_at = ? WHERE article_id = ?",
            (str(error or "permanent failure")[:500], now, article_id),
        )


def retry_failed_deliveries():
    with closing(open_story_box()) as conn:
        cursor = conn.execute(
            "UPDATE deliveries SET status = 'pending', attempts = 0, "
            "next_attempt_ts = 0, claimed_at = NULL, last_error = NULL, updated_at = ? "
            "WHERE status = 'failed'",
            (time.time(),),
        )
        rowcount = cursor.rowcount
    return rowcount


def get_delivery(article_id):
    with closing(open_story_box()) as conn:
        row = conn.execute(
            "SELECT * FROM deliveries WHERE article_id = ?", (article_id,)
        ).fetchone()
    return dict(row) if row else None


def get_article(article_id):
    with closing(open_story_box()) as conn:
        row = conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
    return _row_to_article(row) if row else None


def delivery_counts():
    with closing(open_story_box()) as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS count FROM deliveries GROUP BY status"
        ).fetchall()
    counts = {row["status"]: row["count"] for row in rows}
    return {
        "pending": counts.get("pending", 0),
        "sending": counts.get("sending", 0),
        "sent": counts.get("sent", 0),
        "failed": counts.get("failed", 0),
        "total": sum(counts.values()),
    }


def article_count():
    with closing(open_story_box()) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0])


def feed_is_due(feed_url, now=None):
    now = time.time() if now is None else now
    with closing(open_story_box()) as conn:
        row = conn.execute(
            "SELECT next_attempt_ts FROM feed_health WHERE feed_url = ?", (feed_url,)
        ).fetchone()
    return row is None or float(row["next_attempt_ts"] or 0) <= now


def record_feed_success(feed_url):
    with closing(open_story_box()) as conn:
        conn.execute("DELETE FROM feed_health WHERE feed_url = ?", (feed_url,))


def record_feed_failure(feed_url, feed_name, error):
    now = time.time()
    with closing(open_story_box()) as conn:
        row = conn.execute(
            "SELECT failures FROM feed_health WHERE feed_url = ?", (feed_url,)
        ).fetchone()
        failures = int(row["failures"] or 0) + 1 if row else 1
        delay = min(6 * 3600, 300 * (2 ** min(failures, 6)))
        conn.execute(
            """INSERT INTO feed_health
               (feed_url, feed_name, failures, next_attempt_ts, last_error, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(feed_url) DO UPDATE SET
                 feed_name = excluded.feed_name,
                 failures = excluded.failures,
                 next_attempt_ts = excluded.next_attempt_ts,
                 last_error = excluded.last_error,
                 updated_at = excluded.updated_at""",
            (feed_url, str(feed_name or "")[:200], failures, now + delay,
             str(error or "")[:500], now),
        )


def prune_expired(now=None):
    """Delete only terminal rows old enough that their identity is no longer needed."""
    now = time.time() if now is None else now
    cutoff = now - ARTICLE_RETENTION_SECS
    with closing(open_story_box()) as conn:
        cursor = conn.execute(
            """DELETE FROM articles
               WHERE first_seen_ts < ?
                 AND id IN (SELECT article_id FROM deliveries WHERE status IN ('sent', 'failed'))""",
            (cutoff,),
        )
        deleted_articles = cursor.rowcount
        cursor = conn.execute(
            "DELETE FROM suppressed_titles WHERE expires_ts < ?", (now,)
        )
        deleted_suppressed = cursor.rowcount
    if deleted_articles or deleted_suppressed:
        storage_diary.info(
            f"Pruned {deleted_articles} old article(s), "
            f"{deleted_suppressed} expired suppression(s)."
        )
    return {"articles": deleted_articles, "suppressed": deleted_suppressed}


# Old names used by earlier guides.
init_db = set_up_story_box
get_connection = open_story_box
normalize_title_for_dedupe = make_title_simple_to_compare
