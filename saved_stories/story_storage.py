"""
How we save Sunrisers stories on your computer.

Think of this file as a small filing box:
- stories live in a file called sunrisers_news.db (plain SQLite)
- we keep each story for 24 hours, then recycle it
- the same story can be filed once per player it mentions
  (so one story about two players appears under both names)
- phone alerts are remembered for 14 days so you never get the same text twice
"""
import os
import re
import sqlite3
import time
import unicodedata
from contextlib import closing
from our_teams.players import PLAYERS_BY_TEAM, find_our_players_in_story
from helpers.log_books import storage_diary, problems_diary
def _pick_story_file():
    """Where is our filing box? New home first, old homes as backup."""
    for env_name in ("SUNRISERS_DB_PATH", "SRH_DB_PATH"):
        env_path = os.environ.get(env_name, "").strip()
        if env_path:
            return env_path
    here = os.path.dirname(os.path.abspath(__file__))
    new_home = os.path.join(here, "sunrisers_news.db")
    if os.path.exists(new_home):
        return new_home
    # Old homes from before the friendly rename (Oct 2026).
    for old_home in (
        os.path.join(here, "srh_tracker.db"),
        os.path.join(os.path.dirname(here), "database", "srh_tracker.db"),
    ):
        if os.path.exists(old_home):
            return old_home
    return new_home
STORY_BOX_FILE = os.environ.get(
    "SUNRISERS_DB_PATH",
    os.environ.get("SRH_DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "sunrisers_news.db")),
)
# Old name, kept so older guides still work.
DB_PATH = STORY_BOX_FILE
def _pick_tables_file():
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("tables.sql", "schema.sql"):
        candidate = os.path.join(here, name)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(here, "tables.sql")
TABLES_FILE = _pick_tables_file()
# Old name, kept so older guides still work.
SCHEMA_PATH = TABLES_FILE
ONE_DAY_IN_SECONDS = 86400.0
HOW_LONG_TO_REMEMBER_ALERTS = 14 * 24 * 3600.0
_DASH_CHARS_RE = re.compile("[\u2010\u2011\u2012\u2013\u2014\u2015]")
def open_story_box():
    """Open our filing box (a small SQLite file) so we can read or save stories.

    The file to open is looked up fresh every time, so tests can point
    us at a throwaway file with SUNRISERS_DB_PATH or SRH_DB_PATH.
    """
    conn = sqlite3.connect(_pick_story_file())
    conn.row_factory = sqlite3.Row
    return conn

# Old name, kept so older guides and tests still work.
get_connection = open_story_box
def make_title_simple_to_compare(title):
    """Folds a headline into a stable dedupe key.

    Google News re-serves the same evergreen story with cosmetic variance
    (case, spacing, hyphen vs en-dash, curly quotes). Raw titles stay stored
    verbatim; only the alert-memory key is normalized.

    A trailing outlet tag ("... fail the test - IOL") is also folded away:
    direct publisher feeds and Google News mirrors of the same story differ
    only by that tag. The tag is stripped only when it is short, digit-free
    (fixture markers like "2nd T20I" distinguish real stories), and leaves a
    meaningful remainder.
    """
    text = unicodedata.normalize("NFKC", str(title or ""))
    text = (
        text.replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2018", "'").replace("\u2019", "'")
    )
    text = _DASH_CHARS_RE.sub("-", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    for sep in (" - ", " | "):
        if sep not in text:
            continue
        head, _, tail = text.rpartition(sep)
        tail_words = tail.split()
        if (
            len(head) >= 15
            and 1 <= len(tail_words) <= 4
            and not any(ch.isdigit() for ch in tail)
        ):
            text = head.strip()
            break
    return text


def claim_phone_alert_once(title_norm, player_name, franchise, seen_ts=None,
                    max_age_secs=HOW_LONG_TO_REMEMBER_ALERTS):
    """Atomically claims one Telegram alert slot for a story+target.

    Returns True only when this call wins the slot: first sighting, or a
    sighting after the memory window expired. Re-stamped evergreen pages and
    post-purge resurrections lose the race and must stay silent. Concurrent
    claimants are serialized by the UNIQUE index; the loser reads
    "already present" instead of double-alerting.
    """
    now = time.time()
    try:
        seen = float(seen_ts) if seen_ts else now
    except (TypeError, ValueError):
        seen = now
    try:
        with closing(open_story_box()) as conn:
            # BEGIN IMMEDIATE serializes concurrent claimants so the
            # check-and-set below is atomic across processes.
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT first_seen_ts FROM alerted_stories "
                "WHERE title_norm = ? AND player_name = ? AND franchise = ?",
                (title_norm, player_name, franchise),
            )
            row = cursor.fetchone()
            if row is None:
                try:
                    cursor.execute(
                        "INSERT INTO alerted_stories "
                        "(title_norm, player_name, franchise, first_seen_ts) "
                        "VALUES (?, ?, ?, ?)",
                        (title_norm, player_name, franchise, seen),
                    )
                except sqlite3.IntegrityError:
                    # Lost a concurrent claim race: the slot is taken.
                    conn.rollback()
                    return False
                conn.commit()
                return True
            try:
                first_seen = float(row["first_seen_ts"])
            except (TypeError, ValueError):
                first_seen = 0.0
            if now - first_seen > max_age_secs:
                cursor.execute(
                    "UPDATE alerted_stories SET first_seen_ts = ? "
                    "WHERE title_norm = ? AND player_name = ? AND franchise = ?",
                    (now, title_norm, player_name, franchise),
                )
                conn.commit()
                return True
            conn.rollback()
            return False
    except Exception as e:
        problems_diary.error(f"Alert-claim error: {e}")
        return True


def forget_old_phone_alerts(max_age_secs=HOW_LONG_TO_REMEMBER_ALERTS):
    """Drops alert-memory rows older than the window so the table stays bounded."""
    try:
        with closing(open_story_box()) as conn:
            conn.execute(
                "DELETE FROM alerted_stories WHERE first_seen_ts < ?",
                (time.time() - max_age_secs,),
            )
            conn.commit()
    except Exception as e:
        problems_diary.error(f"Error purging expired alert memory: {e}")


def remove_stories_that_mention_no_one(max_rows=500):
    """
    Re-evaluates the most recent N articles and purges any misattributed rows.
    Row limit keeps the scan O(max_rows) instead of O(entire DB) on every call.
    """
    try:
        with closing(open_story_box()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, title, summary, player_name FROM news ORDER BY id DESC LIMIT ?",
                (max_rows,)
            )
            rows = cursor.fetchall()
            to_delete = []
            for r in rows:
                text = f"{r['title']} {r['summary']}"
                matches = find_our_players_in_story(text)
                matched_names = {m["player_name"] for m in matches}
                if r["player_name"] not in matched_names:
                    to_delete.append(r["id"])
            if to_delete:
                conn.executemany("DELETE FROM news WHERE id = ?", [(i,) for i in to_delete])
                conn.commit()
                storage_diary.info(f"Purged {len(to_delete)} legacy misattributed rows.")
    except Exception as e:
        problems_diary.error(f"Error cleaning invalid matches: {e}")
def throw_away_old_stories():
    """Purges any news article older than 24 hours (86,400 seconds) from SQLite database."""
    try:
        with closing(open_story_box()) as conn:
            cursor = conn.cursor()
            cutoff_ts = time.time() - ONE_DAY_IN_SECONDS
            cursor.execute(
                "DELETE FROM news WHERE pub_timestamp > 0 AND pub_timestamp < ?",
                (cutoff_ts,)
            )
            deleted = cursor.rowcount
            conn.commit()
        if deleted > 0:
            storage_diary.info(f"Purged {deleted} expired articles (>24 hours old).")
    except Exception as e:
        problems_diary.error(f"Error purging 24h expired news: {e}")
def throw_away_old_notes(days=7):
    """Purges notifications older than N days to keep the notifications table bounded."""
    try:
        with closing(open_story_box()) as conn:
            conn.execute(
                "DELETE FROM notifications WHERE created_at < datetime('now', ?)",
                (f"-{days} days",)
            )
            conn.commit()
    except Exception as e:
        problems_diary.error(f"Error purging stale notifications: {e}")
def set_up_story_box():
    """Get our filing box ready: make tables, copy the player list in,
    tidy up old stories. Safe to run every time the app starts.
    """
    try:
        with closing(open_story_box()) as conn:
            cursor = conn.cursor()
            with open(TABLES_FILE, "r") as f:
                cursor.executescript(f.read())
            conn.commit()
            cursor.execute("PRAGMA table_info(news)")
            columns = [c["name"] for c in cursor.fetchall()]
            if "pub_timestamp" not in columns:
                cursor.execute("ALTER TABLE news ADD COLUMN pub_timestamp REAL DEFAULT 0.0")
                conn.commit()
            cursor.execute("PRAGMA index_list(news)")
            legacy_link_unique = any(
                row["unique"] and str(row["name"]).startswith("sqlite_autoindex_news")
                for row in cursor.fetchall()
            )
            if legacy_link_unique:
                cursor.executescript(
                    """
                    ALTER TABLE news RENAME TO news_legacy_unique_link;
                    CREATE TABLE news (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        source TEXT NOT NULL,
                        summary TEXT,
                        link TEXT,
                        published_at TEXT,
                        pub_timestamp REAL DEFAULT 0.0,
                        player_name TEXT,
                        franchise TEXT,
                        importance_score REAL DEFAULT 5.0,
                        category TEXT DEFAULT 'General News'
                    );
                    INSERT OR IGNORE INTO news
                        (id, title, source, summary, link, published_at, pub_timestamp,
                         player_name, franchise, importance_score, category)
                    SELECT id, title, source, summary, link, published_at, pub_timestamp,
                           player_name, franchise, importance_score, category
                    FROM news_legacy_unique_link;
                    DROP TABLE news_legacy_unique_link;
                    """
                )
                conn.commit()
                with open(TABLES_FILE, "r") as f:
                    cursor.executescript(f.read())
                conn.commit()
            cursor.execute(
                "UPDATE news SET pub_timestamp = ? WHERE pub_timestamp = 0.0 OR pub_timestamp IS NULL",
                (time.time(),)
            )
            conn.commit()
            try:
                cursor.execute(
                    "DELETE FROM news WHERE title LIKE '%Pranav, Irfan, Shashank%'"
                )
                conn.commit()
            except Exception:
                pass
            cursor.execute("DELETE FROM players")
            for team_key, team_info in PLAYERS_BY_TEAM.items():
                franchise = team_info["franchise_name"]
                for p in team_info["players"]:
                    cursor.execute(
                        """INSERT OR IGNORE INTO players (name, country, franchise, role, captain)
                           VALUES (?, ?, ?, ?, ?)""",
                        (p["name"], p["country"], franchise, p["role"], 1 if p.get("captain") else 0)
                    )
            conn.commit()
        remove_stories_that_mention_no_one()
        throw_away_old_stories()
        throw_away_old_notes()
        forget_old_phone_alerts()
        storage_diary.info("Database schema & Excel master roster initialised cleanly.")
    except Exception as e:
        problems_diary.error(f"Failed to initialise database: {e}")
def get_all_players(franchise_filter=None):
    """Retrieves list of players, optionally filtered by franchise."""
    with closing(open_story_box()) as conn:
        cursor = conn.cursor()
        if franchise_filter and franchise_filter != "All":
            cursor.execute(
                "SELECT * FROM players WHERE franchise = ? ORDER BY name ASC",
                (franchise_filter,)
            )
        else:
            cursor.execute("SELECT * FROM players ORDER BY name ASC")
        return [dict(r) for r in cursor.fetchall()]
def save_story(title, source, summary, link, published_at, player_name, franchise, pub_timestamp=0.0, importance_score=5.0, category="General News"):
    """
    Inserts exact raw RSS headline & summary for rostered players and 4 franchises.
    Deduplicates on URL or exact title per tracked target. Coerces empty/# links
    to NULL so placeholder URLs do not collapse unrelated articles.
    importance_score and category always take database defaults (5.0 / 'General News');
    per-article scoring was removed.
    """
    clean_link = link.strip() if link and link.strip() and link.strip() != "#" else None
    try:
        with closing(open_story_box()) as conn:
            cursor = conn.cursor()
            if clean_link:
                cursor.execute(
                    """SELECT id FROM news
                       WHERE (link = ? OR title = ?)
                         AND player_name = ?
                         AND franchise = ?""",
                    (clean_link, title, player_name, franchise)
                )
            else:
                cursor.execute(
                    """SELECT id FROM news
                       WHERE title = ?
                         AND player_name = ?
                         AND franchise = ?""",
                    (title, player_name, franchise)
                )
            if cursor.fetchone():
                return None  
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
        storage_diary.info(
            f"Inserted article #{news_id} [{category} | score={importance_score}] "
            f"for {player_name} from {source}."
        )
        return news_id
    except sqlite3.IntegrityError as e:
        # Expected concurrent-dedupe hit: two overlapping ingest cycles (or a
        # retry) raced past the SELECT check above. The row is already stored
        # for this target, so report "already present" quietly instead of
        # spamming errors.log with UNIQUE constraint noise.
        storage_diary.debug(f"Concurrent dedupe hit for '{title}' ({player_name}): {e}")
        return None
    except Exception as e:
        problems_diary.error(f"Database insert error: {e}")
        return None
def get_latest_stories(limit=150):
    """Returns live news items ordered by pub_timestamp DESC."""
    with closing(open_story_box()) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM news ORDER BY pub_timestamp DESC, id DESC LIMIT ?",
            (limit,)
        )
        return [dict(r) for r in cursor.fetchall()]
def search_stories(query):
    """Searches news items by keyword across title, summary, or player name."""
    with closing(open_story_box()) as conn:
        cursor = conn.cursor()
        q = f"%{query.lower()}%"
        cursor.execute(
            """SELECT * FROM news
               WHERE LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(player_name) LIKE ?
               ORDER BY pub_timestamp DESC, id DESC""",
            (q, q, q)
        )
        return [dict(r) for r in cursor.fetchall()]
def leave_a_note(message, type_str="INFO"):
    """Inserts a new dashboard notification."""
    try:
        with closing(open_story_box()) as conn:
            conn.execute(
                "INSERT INTO notifications (message, type) VALUES (?, ?)",
                (message, type_str)
            )
            conn.commit()
    except Exception as e:
        problems_diary.error(f"Error inserting notification: {e}")
def count_stories_and_players():
    """Returns a summary dict with total_news, total_players, and franchise breakdown."""
    with closing(open_story_box()) as conn:
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
def read_saved_fact(key: str, default=None):
    """Reads a persistent key-value pair from the metadata table.
    Returns default if the key does not exist.
    """
    try:
        with closing(open_story_box()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
    except Exception as e:
        problems_diary.error(f"read_saved_fact({key}) error: {e}")
        return default
def save_a_fact(key: str, value: str):
    """Upserts a persistent key-value pair into the metadata table."""
    try:
        with closing(open_story_box()) as conn:
            conn.execute(
                """INSERT INTO metadata (key, value, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP""",
                (key, str(value))
            )
            conn.commit()
    except Exception as e:
        problems_diary.error(f"save_a_fact({key}) error: {e}")


# Old names, kept so older guides, tests and phone alerts still work.
init_db = set_up_story_box
get_connection = open_story_box
insert_news = save_story
get_recent_news = get_latest_stories
search_news = search_stories
insert_notification = leave_a_note
purge_expired_24h_news = throw_away_old_stories
purge_stale_notifications = throw_away_old_notes
get_analytics_summary = count_stories_and_players
get_metadata = read_saved_fact
set_metadata = save_a_fact
normalize_title_for_dedupe = make_title_simple_to_compare
try_claim_alert = claim_phone_alert_once
purge_expired_alerts = forget_old_phone_alerts
cleanup_invalid_matches = remove_stories_that_mention_no_one
