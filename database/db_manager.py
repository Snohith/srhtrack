"""
Database Manager for @SRHXtra SQLite Memory layer (V5.0 Topic Consolidation Engine).
Ensures 100% real live data, 73-player coverage across 4 squads, and single-topic multi-source deduplication.
"""

import os
import sqlite3
import re
from config.roster import MASTER_ROSTER
from utils.logger import db_logger, error_logger

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "srh_tracker.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

def get_connection():
    """Returns sqlite3 connection with dict cursor capabilities."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes database schema and ensures tables exist."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        with open(SCHEMA_PATH, "r") as f:
            cursor.executescript(f.read())
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

def insert_or_consolidate_news(title, source, summary, link, published_at, player_name, franchise, importance_score, category):
    """
    Inserts a real live RSS news article.
    If an article about the SAME TOPIC for the same player already exists, consolidates sources and links into ONE single card!
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

        # Check single-topic duplicate (Same Player + matching key topic words)
        cursor.execute("SELECT id, title, source, link, importance_score FROM news WHERE player_name = ?", (player_name,))
        player_news = cursor.fetchall()
        
        new_keywords = set(extract_topic_keywords(title))
        for row in player_news:
            existing_keywords = set(extract_topic_keywords(row["title"]))
            overlap = new_keywords.intersection(existing_keywords)
            # If 2 or more major topic words match for the same player, treat as SAME TOPIC!
            if len(overlap) >= 2:
                existing_sources = [s.strip() for s in row["source"].split(",")]
                existing_links = [l.strip() for l in row["link"].split(",")]
                
                if source not in existing_sources and link not in existing_links:
                    updated_sources = ", ".join(existing_sources + [source])
                    updated_links = ", ".join(existing_links + [link])
                    max_score = max(row["importance_score"], importance_score)
                    
                    cursor.execute("""
                        UPDATE news 
                        SET source = ?, link = ?, importance_score = ?
                        WHERE id = ?
                    """, (updated_sources, updated_links, max_score, row["id"]))
                    conn.commit()
                    db_logger.info(f"Consolidated new source '{source}' into existing topic for {player_name}.")
                
                conn.close()
                return None

        # Insert as new unique topic card
        cursor.execute("""
            INSERT INTO news (title, source, summary, link, published_at, player_name, franchise, importance_score, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, source, summary, link, published_at, player_name, franchise, importance_score, category))
        conn.commit()
        news_id = cursor.lastrowid
        conn.close()
        db_logger.info(f"Inserted live RSS article #{news_id} for {player_name} from {source}.")
        return news_id
    except Exception as e:
        error_logger.error(f"Database insert error: {e}")
        conn.close()
        return None

def get_recent_news(limit=100):
    """Gets recent scraped live news items ordered strictly by ID DESC (newest scraped articles first)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_news(query):
    """Searches news items by keyword across title, summary, or player name."""
    conn = get_connection()
    cursor = conn.cursor()
    q = f"%{query.lower()}%"
    cursor.execute("""
        SELECT * FROM news 
        WHERE LOWER(title) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(player_name) LIKE ?
        ORDER BY id DESC
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
