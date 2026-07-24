"""
Database Manager for @SRHXtra SQLite Memory layer (V12.0 — Context-Manager Edition).
Stores raw exact headlines, summaries, and source links for all 74 players and 4 franchises.
Improvements in V12.0:
  - contextlib.closing() on every connection to prevent leaks on exceptions
  - purge_stale_notifications() cleans unbounded notifications table weekly
  - Zero-timestamp migration in init_db() fixes legacy rows with pub_timestamp = 0.0
  - cleanup_invalid_matches() row-limit guard keeps it O(N) not O(all-time)
  - get_analytics_summary() added for test & dashboard use
"""

import os
import sqlite3
import time
from contextlib import closing
from config.roster import MASTER_ROSTER, match_player_or_franchise_in_text
from utils.logger import db_logger, error_logger

# Allow DB path override via env variable for isolated test environments
DB_PATH = os.environ.get(
    "SRH_DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "srh_tracker.db")
)
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# 24 Hours in Seconds
SECONDS_24_HOURS = 86400.0


def get_connection():
    """Returns sqlite3 connection with dict-row cursor. Use with contextlib.closing()."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def cleanup_invalid_matches(max_rows=500):
    """
    Re-evaluates the most recent N articles and purges any misattributed rows.
    Row limit keeps the scan O(max_rows) instead of O(entire DB) on every call.
    """
    try:
        with closing(get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, summary, player_name FROM news ORDER BY id DESC LIMIT ?",
                (max_rows,)
            )
            rows = cursor.fetchall()

            to_delete = []
            for r in rows:
                text = f"{r['title']} {r['summary']}"
                matches = match_player_or_franchise_in_text(text)
                matched_names = {m["player_name"] for m in matches}
                if r["player_name"] not in matched_names:
                    to_delete.append(r["id"])

            if to_delete:
                conn.executemany("DELETE FROM news WHERE id = ?", [(i,) for i in to_delete])
                conn.commit()
                db_logger.info(f"Purged {len(to_delete)} legacy misattributed rows.")
    except Exception as e:
        error_logger.error(f"Error cleaning invalid matches: {e}")


def purge_expired_24h_news():
    """Purges any news article older than 24 hours (86,400 seconds) from SQLite database."""
    try:
        with closing(get_connection()) as conn:
            cursor = conn.cursor()
            cutoff_ts = time.time() - SECONDS_24_HOURS
            cursor.execute(
                "DELETE FROM news WHERE pub_timestamp > 0 AND pub_timestamp < ?",
                (cutoff_ts,)
            )
            deleted = cursor.rowcount
            conn.commit()
        if deleted > 0:
            db_logger.info(f"Purged {deleted} expired articles (>24 hours old).")
    except Exception as e:
        error_logger.error(f"Error purging 24h expired news: {e}")


def purge_stale_notifications(days=7):
    """Purges notifications older than N days to keep the notifications table bounded."""
    try:
        with closing(get_connection()) as conn:
            conn.execute(
                "DELETE FROM notifications WHERE created_at < datetime('now', ?)",
                (f"-{days} days",)
            )
            conn.commit()
    except Exception as e:
        error_logger.error(f"Error purging stale notifications: {e}")


def init_db():
    """
    Initialises DB schema, runs migrations, seeds roster, and runs startup cleanups.
    V12.0 additions:
      - Migrates legacy pub_timestamp = 0.0 rows to current time so they sort correctly
      - Calls purge_stale_notifications() to bound the notifications table
    """
    try:
        with closing(get_connection()) as conn:
            cursor = conn.cursor()

            # Apply schema (CREATE TABLE IF NOT EXISTS is idempotent)
            with open(SCHEMA_PATH, "r") as f:
                cursor.executescript(f.read())
            conn.commit()

            # Schema migration: ensure pub_timestamp column exists (legacy DBs)
            cursor.execute("PRAGMA table_info(news)")
            columns = [c["name"] for c in cursor.fetchall()]
            if "pub_timestamp" not in columns:
                cursor.execute("ALTER TABLE news ADD COLUMN pub_timestamp REAL DEFAULT 0.0")
                conn.commit()

            # Migration: fix legacy rows where pub_timestamp = 0.0 so they sort correctly
            cursor.execute(
                "UPDATE news SET pub_timestamp = ? WHERE pub_timestamp = 0.0 OR pub_timestamp IS NULL",
                (time.time(),)
            )
            conn.commit()

            # Hard purge legacy Sakib Hussain misattribution row (guarded)
            try:
                cursor.execute(
                    "DELETE FROM news WHERE title LIKE '%Pranav, Irfan, Shashank%' OR player_name = 'Sakib Hussain'"
                )
                conn.commit()
            except Exception:
                pass

            # Seed Master Roster of 74 Players
            for team_key, team_info in MASTER_ROSTER.items():
                franchise = team_info["franchise_name"]
                for p in team_info["players"]:
                    cursor.execute(
                        """INSERT OR IGNORE INTO players (name, country, franchise, role, captain)
                           VALUES (?, ?, ?, ?, ?)""",
                        (p["name"], p["country"], franchise, p["role"], 1 if p.get("captain") else 0)
                    )
            conn.commit()

        # Post-init cleanups (use their own connections)
        cleanup_invalid_matches()
        purge_expired_24h_news()
        purge_stale_notifications()
        db_logger.info("Database schema & 74-player master roster initialised cleanly.")
    except Exception as e:
        error_logger.error(f"Failed to initialise database: {e}")


def get_all_players(franchise_filter=None):
    """Retrieves list of players, optionally filtered by franchise."""
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        if franchise_filter and franchise_filter != "All":
            cursor.execute(
                "SELECT * FROM players WHERE franchise = ? ORDER BY name ASC",
                (franchise_filter,)
            )
        else:
            cursor.execute("SELECT * FROM players ORDER BY name ASC")
        return [dict(r) for r in cursor.fetchall()]


def insert_news(title, source, summary, link, published_at, player_name, franchise, pub_timestamp=0.0, importance_score=5.0, category="General News"):
    """
    Inserts exact raw RSS headline & summary for all 74 players and 4 franchises.
    Deduplicates on URL or exact title. Coerces empty/# links to NULL to avoid
    false UNIQUE constraint conflicts on empty strings.

    Phase 1 upgrade: importance_score and category are now real parameters
    (no longer hardcoded to 5.0 / 'General'). Defaults maintain backwards compat.
    """
    # Coerce empty / placeholder links to None (NULL in SQLite handles UNIQUE safely)
    clean_link = link.strip() if link and link.strip() and link.strip() != "#" else None

    try:
        with closing(get_connection()) as conn:
            cursor = conn.cursor()

            # Dedup check
            if clean_link:
                cursor.execute("SELECT id FROM news WHERE link = ? OR title = ?", (clean_link, title))
            else:
                cursor.execute("SELECT id FROM news WHERE title = ?", (title,))

            if cursor.fetchone():
                return None  # Duplicate — skip silently

            cursor.execute(
                """INSERT INTO news
                   (title, source, summary, link, published_at, pub_timestamp,
                    player_name, franchise, importance_score, category)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (title, source, summary, clean_link, published_at, pub_timestamp,
                 player_name, franchise, importance_score, category)
            )
            conn.commit()
            news_id = cursor.lastrowid

        db_logger.info(
            f"Inserted article #{news_id} [{category} | score={importance_score}] "
            f"for {player_name} from {source}."
        )
        return news_id
    except Exception as e:
        error_logger.error(f"Database insert error: {e}")
        return None


def get_recent_news(limit=150):
    """Returns live news items ordered by pub_timestamp DESC."""
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM news ORDER BY pub_timestamp DESC, id DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in cursor.fetchall()]


def search_news(query):
    """Searches news items by keyword across title, summary, or player name."""
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        q = f"%{query.lower()}%"
        cursor.execute(
            """SELECT * FROM news
               WHERE LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(player_name) LIKE ?
               ORDER BY pub_timestamp DESC, id DESC""",
            (q, q, q)
        )
        return [dict(r) for r in cursor.fetchall()]


def insert_notification(message, type_str="INFO"):
    """Inserts a new dashboard notification."""
    try:
        with closing(get_connection()) as conn:
            conn.execute(
                "INSERT INTO notifications (message, type) VALUES (?, ?)",
                (message, type_str)
            )
            conn.commit()
    except Exception as e:
        error_logger.error(f"Error inserting notification: {e}")


def get_analytics_summary():
    """Returns a summary dict with total_news, total_players, and franchise breakdown."""
    with closing(get_connection()) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS cnt FROM news")
        total_news = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) AS cnt FROM players")
        total_players = cursor.fetchone()["cnt"]
        cursor.execute(
            "SELECT franchise, COUNT(*) AS cnt FROM news GROUP BY franchise ORDER BY cnt DESC"
        )
        franchise_breakdown = {r["franchise"]: r["cnt"] for r in cursor.fetchall()}
    return {
        "total_news": total_news,
        "total_players": total_players,
        "franchise_breakdown": franchise_breakdown,
    }
