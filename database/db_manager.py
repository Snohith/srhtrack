"""
Database Manager for @SRHXtra SQLite Memory layer (V8.0 Strict 24-Hour Expiry Engine).
Purges any article older than 24 hours automatically on query & startup.
Stores 73 players and 4 franchise updates ordered strictly BY pub_timestamp DESC.
"""

import os
import sqlite3
import re
import time
from config.roster import MASTER_ROSTER
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
    """Initializes database schema, handles schema migrations, and purges articles > 24 hours old."""
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
        
        # Purge any news older than 24 hours
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

def extract_topic_keywords(title):
    """Extracts significant keywords for single-topic deduplication."""
    words = re.findall(r'\b[a-zA-Z]{4,}\b', title.lower())
    ignore = {"cricket", "india", "england", "australia", "south", "africa", "first", "second", "third", "match", "series"}
    return [w for w in words if w not in ignore]

def insert_and_summarize_news(title, source, summary, link, published_at, player_name, franchise, importance_score, category, pub_timestamp=0.0):
    """
    Inserts or summarizes multiple coverage articles for the same player/team into ONE single consolidated card.
    Merges summaries, updates latest timestamp, and attaches all verified source buttons.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Check exact link or exact title match first
        if link and link.strip() and link != "#":
            cursor.execute("SELECT id, source, link FROM news WHERE link = ? OR title = ?", (link, title))
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return None

        # Check for related topic cards for the same target
        cursor.execute("SELECT id, title, source, summary, link, importance_score, pub_timestamp, published_at FROM news WHERE player_name = ?", (player_name,))
        player_news = cursor.fetchall()
        
        new_keywords = set(extract_topic_keywords(title))
        for row in player_news:
            existing_keywords = set(extract_topic_keywords(row["title"]))
            overlap = new_keywords.intersection(existing_keywords)
            
            # If 2 or more major topic words match for the same player/team, SUMMARIZE & MERGE into single card!
            if len(overlap) >= 2 or (len(new_keywords) == 1 and overlap):
                existing_sources = [s.strip() for s in row["source"].split(",")]
                existing_links = [l.strip() for l in row["link"].split(",")]
                
                # Merge source and link if not already present
                if source not in existing_sources:
                    existing_sources.append(source)
                if link not in existing_links:
                    existing_links.append(link)
                
                updated_sources = ", ".join(existing_sources)
                updated_links = ", ".join(existing_links)
                
                # Combine summaries intelligently
                existing_summary = row["summary"].strip()
                if summary and summary not in existing_summary:
                    merged_summary = f"{existing_summary} | [{source} Update]: {summary}"
                else:
                    merged_summary = existing_summary
                
                # Use latest timestamp so consolidated card moves to top
                latest_ts = max(row["pub_timestamp"], pub_timestamp)
                latest_pub_date = published_at if pub_timestamp > row["pub_timestamp"] else row["published_at"]
                max_score = max(row["importance_score"], importance_score)

                cursor.execute("""
                    UPDATE news 
                    SET source = ?, summary = ?, link = ?, importance_score = ?, pub_timestamp = ?, published_at = ?
                    WHERE id = ?
                """, (updated_sources, merged_summary, updated_links, max_score, latest_ts, latest_pub_date, row["id"]))
                conn.commit()
                db_logger.info(f"Summarized & merged new report from '{source}' into single card for {player_name}.")
                conn.close()
                return row["id"]

        # Insert as new standalone topic card
        cursor.execute("""
            INSERT INTO news (title, source, summary, link, published_at, pub_timestamp, player_name, franchise, importance_score, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, source, summary, link, published_at, pub_timestamp, player_name, franchise, importance_score, category))
        conn.commit()
        news_id = cursor.lastrowid
        conn.close()
        db_logger.info(f"Inserted new topic card #{news_id} for {player_name} from {source}.")
        return news_id
    except Exception as e:
        error_logger.error(f"Database insert error: {e}")
        conn.close()
        return None

def get_recent_news(limit=100):
    """Purges >24h expired news and gets recent scraped live news items ordered strictly BY pub_timestamp DESC."""
    purge_expired_24h_news()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY pub_timestamp DESC, id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_news(query):
    """Searches news items by keyword across title, summary, or player name."""
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

def get_analytics_summary():
    """Returns analytics metrics for dashboard."""
    purge_expired_24h_news()
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as cnt FROM news")
    total_news = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT AVG(importance_score) as avg_score FROM news")
    avg_score = cursor.fetchone()["avg_score"] or 0.0
    
    cursor.execute("""
        SELECT player_name, COUNT(*) as cnt 
        FROM news 
        WHERE player_name IS NOT NULL 
        GROUP BY player_name 
        ORDER BY cnt DESC LIMIT 5
    """)
    top_players = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return {
        "total_news": total_news,
        "avg_importance": round(avg_score, 1),
        "top_players": top_players
    }
