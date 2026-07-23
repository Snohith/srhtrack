"""
Database Manager for @SRHXtra SQLite Memory layer (V6.0 All-Player Complete News Feed).
Stores EVERY SINGLE scraped article for all 73 players without topic deduplication.
"""

import os
import sqlite3
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
    """Initializes database schema, handles schema migrations, and purges legacy hardcoded timestamp rows."""
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

def insert_news(title, source, summary, link, published_at, player_name, franchise, importance_score, category, pub_timestamp=0.0):
    """
    Inserts EVERY SINGLE scraped news article for all 73 players (No topic deduplication).
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, source, summary, link, published_at, pub_timestamp, player_name, franchise, importance_score, category))
        conn.commit()
        news_id = cursor.lastrowid
        conn.close()
        db_logger.info(f"Inserted article #{news_id} for {player_name} from {source}.")
        return news_id
    except Exception as e:
        error_logger.error(f"Database insert error: {e}")
        conn.close()
        return None

def get_recent_news(limit=200):
    """Gets recent scraped live news items ordered strictly BY pub_timestamp DESC (latest published timestamp first)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM news ORDER BY pub_timestamp DESC, id DESC LIMIT ?", (limit,))
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
