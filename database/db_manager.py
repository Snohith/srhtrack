"""
Database Manager for @SRHXtra SQLite Memory layer (V11.0 Auto-Sanitizing Engine).
Stores raw exact headlines, summaries, and source links for all 73 players and 4 franchises.
Includes cleanup_invalid_matches() to automatically purge legacy misattributed rows on Streamlit Cloud disk.
"""

import os
import sqlite3
import time
from config.roster import MASTER_ROSTER, match_player_or_franchise_in_text
from utils.logger import db_logger, error_logger

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "srh_tracker.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# 24 Hours in Seconds (86,400s)
SECONDS_24_HOURS = 86400.0

def get_connection():
    """Returns sqlite3 connection with dict cursor capabilities."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def cleanup_invalid_matches():
    """Re-evaluates all stored articles and purges any legacy misattributed rows from disk."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, summary, player_name FROM news")
        rows = cursor.fetchall()
        
        to_delete = []
        for r in rows:
            text = f"{r['title']} {r['summary']}"
            matches = match_player_or_franchise_in_text(text)
            matched_names = {m["player_name"] for m in matches}
            
            # If current player_name in DB is NOT in matched_names, mark for deletion!
            if r["player_name"] not in matched_names:
                to_delete.append(r["id"])
                
        if to_delete:
            for idx in to_delete:
                cursor.execute("DELETE FROM news WHERE id = ?", (idx,))
            conn.commit()
            db_logger.info(f"Purged {len(to_delete)} legacy misattributed rows.")
        conn.close()
    except Exception as e:
        error_logger.error(f"Error cleaning invalid matches: {e}")

def purge_expired_24h_news():
    """Purges any news article older than 24 hours (86,400 seconds) from SQLite database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now_ts = time.time()
        cutoff_ts = now_ts - SECONDS_24_HOURS
        cursor.execute("DELETE FROM news WHERE pub_timestamp > 0 AND pub_timestamp < ?", (cutoff_ts,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            db_logger.info(f"Purged {deleted} expired articles (>24 hours old).")
    except Exception as e:
        error_logger.error(f"Error purging 24h expired news: {e}")

def init_db():
    """Initializes database schema, handles schema migrations, purges misattributed rows & 24h expired articles."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        with open(SCHEMA_PATH, "r") as f:
            cursor.executescript(f.read())
        conn.commit()

        # Schema migration check: ensure pub_timestamp column exists
        cursor.execute("PRAGMA table_info(news)")
        columns = [c["name"] for c in cursor.fetchall()]
        if "pub_timestamp" not in columns:
            cursor.execute("ALTER TABLE news ADD COLUMN pub_timestamp REAL DEFAULT 0.0")
            conn.commit()

        # Hard purge legacy Sakib Hussain misattribution row
        cursor.execute("DELETE FROM news WHERE title LIKE '%Pranav, Irfan, Shashank%' OR player_name = 'Sakib Hussain'")
        conn.commit()

        # Populate Master Roster of 73 Players
        for team_key, team_info in MASTER_ROSTER.items():
            franchise = team_info["franchise_name"]
            for p in team_info["players"]:
                cursor.execute("""
                    INSERT OR IGNORE INTO players (name, country, franchise, role, captain)
                    VALUES (?, ?, ?, ?, ?)
                """, (p["name"], p["country"], franchise, p["role"], 1 if p.get("captain") else 0))
        conn.commit()
        conn.close()
        
        # Purge misattributed legacy rows and articles > 24 hours old
        cleanup_invalid_matches()
        purge_expired_24h_news()
        db_logger.info("Database schema & 73-player master roster initialized cleanly.")
    except Exception as e:
        error_logger.error(f"Failed to initialize database: {e}")

def get_all_players(franchise_filter=None):
    """Retrieves list of players, optionally filtered by franchise."""
    conn = get_connection()
    cursor = conn.cursor()
    if franchise_filter and franchise_filter != "All":
        cursor.execute("SELECT * FROM players WHERE franchise = ? ORDER BY name ASC", (franchise_filter,))
    else:
        cursor.execute("SELECT * FROM players ORDER BY name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def insert_news(title, source, summary, link, published_at, player_name, franchise, pub_timestamp=0.0):
    """
    Inserts exact raw RSS headline & summary for all 73 players and 4 franchises.
    Only checks exact URL / exact Title uniqueness so identical URL feeds aren't repeated.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if link and link.strip() and link != "#":
            cursor.execute("SELECT id FROM news WHERE link = ? OR title = ?", (link, title))
        else:
            cursor.execute("SELECT id FROM news WHERE title = ?", (title,))
            
        if cursor.fetchone():
            conn.close()
            return None

        cursor.execute("""
            INSERT INTO news (title, source, summary, link, published_at, pub_timestamp, player_name, franchise, importance_score, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 5.0, 'General')
        """, (title, source, summary, link, published_at, pub_timestamp, player_name, franchise))
        conn.commit()
        news_id = cursor.lastrowid
        conn.close()
        db_logger.info(f"Inserted raw article #{news_id} for {player_name} from {source}.")
        return news_id
    except Exception as e:
        error_logger.error(f"Database insert error: {e}")
        conn.close()
        return None

def get_recent_news(limit=150):
    """Purges misattributed legacy rows & >24h expired news, then gets active live news items ordered strictly BY pub_timestamp DESC."""
    cleanup_invalid_matches()
    purge_expired_24h_news()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY pub_timestamp DESC, id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_news(query):
    """Searches news items by keyword across title, summary, or player name."""
    cleanup_invalid_matches()
    purge_expired_24h_news()
    conn = get_connection()
    cursor = conn.cursor()
    q = f"%{query.lower()}%"
    cursor.execute("""
        SELECT * FROM news 
        WHERE LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(player_name) LIKE ?
        ORDER BY pub_timestamp DESC, id DESC
    """, (q, q, q))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def insert_notification(message, type_str="INFO"):
    """Inserts a new dashboard notification."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notifications (message, type) VALUES (?, ?)", (message, type_str))
    conn.commit()
    conn.close()
