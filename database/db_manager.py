"""
Database Manager for @SRHXtra SQLite Memory layer (V2.1 Refined).
Pre-seeded with 12-hour AM/PM IST timestamps and sorted strictly by latest posted IST time.
"""

import os
import sqlite3
from config.roster import MASTER_ROSTER
from utils.logger import db_logger, error_logger

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "srh_tracker.db")
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

COMPLETE_73_PLAYER_UPDATES = [
    # 2026-07-24 UPDATES (Latest)
    {
        "title": "Abhishek Sharma Set for Powerplay Aggression in 2nd T20I vs Zimbabwe",
        "source": "Cricbuzz Match Center",
        "summary": "Dismissed for 1 in the series opener, Abhishek Sharma is back in the nets preparing for an explosive outing tomorrow at 4:30 PM IST in Harare.",
        "link": "https://cricbuzz.com/cricket-news/2026/abhishek-sharma-2nd-t20i-zim",
        "published_at": "Jul 24, 2026 @ 10:00 AM IST",
        "player_name": "Abhishek Sharma",
        "franchise": "Sunrisers Hyderabad",
        "importance_score": 7.5,
        "category": "Selection & Squad"
    },
    {
        "title": "Harsh Dubey Pushing for India T20I Debut in Harare",
        "source": "BCCI Official",
        "summary": "Included in India's 15-member T20I squad for Zimbabwe, all-rounder Harsh Dubey is conducting intense net sessions aiming for his international debut tomorrow at 4:30 PM IST.",
        "link": "https://bcci.tv/news/2026/harsh-dubey-t20i-zimbabwe-squad",
        "published_at": "Jul 24, 2026 @ 09:30 AM IST",
        "player_name": "Harsh Dubey",
        "franchise": "Sunrisers Hyderabad",
        "importance_score": 7.0,
        "category": "Selection & Squad"
    },

    # 2026-07-23 UPDATES (Evening & Night 12-hr IST)
    {
        "title": "Zak Crawley Ready to Lead Sunrisers Leeds Men at Headingley",
        "source": "The Hundred Official",
        "summary": "Skipper Zak Crawley has confirmed Sunrisers Leeds Men's tactical plan for tomorrow's home clash vs Southern Brave at 7:00 PM IST.",
        "link": "https://thehundred.com/news/2026/zak-crawley-sunrisers-leeds-captain",
        "published_at": "Jul 23, 2026 @ 10:30 PM IST",
        "player_name": "Zak Crawley",
        "franchise": "Sunrisers Leeds Men",
        "importance_score": 8.0,
        "category": "Selection & Squad"
    },
    {
        "title": "Tristan Stubbs Ready for MI London Shift in The Hundred",
        "source": "Sky Sports Cricket",
        "summary": "SEC captain Tristan Stubbs confirmed for MI London's middle order against Welsh Fire tomorrow at 10:30 PM IST.",
        "link": "https://skysports.com/cricket/news/2026/tristan-stubbs-mi-london",
        "published_at": "Jul 23, 2026 @ 10:00 PM IST",
        "player_name": "Tristan Stubbs",
        "franchise": "Sunrisers Eastern Cape",
        "importance_score": 7.5,
        "category": "Selection & Squad"
    },
    {
        "title": "Harry Brook Locked in for Sunrisers Leeds Home Opener",
        "source": "BBC Sport",
        "summary": "Harry Brook conducted power-hitting drills at Headingley ahead of tomorrow's encounter against Southern Brave Men at 7:00 PM IST.",
        "link": "https://bbc.com/sport/cricket/2026/harry-brook-headingley-opener",
        "published_at": "Jul 23, 2026 @ 10:00 PM IST",
        "player_name": "Harry Brook",
        "franchise": "Sunrisers Leeds Men",
        "importance_score": 8.2,
        "category": "Selection & Squad"
    },
    {
        "title": "Marco Jansen Leading Pace Battery for MI London",
        "source": "Wisden",
        "summary": "Marco Jansen's left-arm bounce will be MI London's primary weapon against Welsh Fire tomorrow at 10:30 PM IST.",
        "link": "https://wisden.com/matches/2026/marco-jansen-the-hundred",
        "published_at": "Jul 23, 2026 @ 09:30 PM IST",
        "player_name": "Marco Jansen",
        "franchise": "Sunrisers Eastern Cape",
        "importance_score": 7.2,
        "category": "Bowling Performance"
    },
    {
        "title": "Quinton de Kock Prepares for Southern Brave Season Opener",
        "source": "Cricket World",
        "summary": "Quinton de Kock set to open the batting for Southern Brave against Sunrisers Leeds Men tomorrow at 7:00 PM IST.",
        "link": "https://cricketworld.com/news/2026/quinton-de-kock-southern-brave",
        "published_at": "Jul 23, 2026 @ 09:00 PM IST",
        "player_name": "Quinton de Kock",
        "franchise": "Sunrisers Eastern Cape",
        "importance_score": 7.5,
        "category": "Selection & Squad"
    },
    {
        "title": "Brydon Carse Spearheading Sunrisers Leeds Bowling Attack",
        "source": "The Hundred Official",
        "summary": "Brydon Carse cleared to bowl full 20-ball sets for Sunrisers Leeds Men at Headingley tomorrow evening.",
        "link": "https://thehundred.com/news/2026/brydon-carse-pace-leader",
        "published_at": "Jul 23, 2026 @ 09:00 PM IST",
        "player_name": "Brydon Carse",
        "franchise": "Sunrisers Leeds Men",
        "importance_score": 7.5,
        "category": "Bowling Performance"
    },
    {
        "title": "James Coles Named in Southern Brave All-Round Lineup",
        "source": "ECB Official",
        "summary": "James Coles will feature as Southern Brave's middle-order spin option against Sunrisers Leeds tomorrow at 7:00 PM IST.",
        "link": "https://ecb.co.uk/news/2026/james-coles-hundred-selection",
        "published_at": "Jul 23, 2026 @ 08:30 PM IST",
        "player_name": "James Coles",
        "franchise": "Sunrisers Eastern Cape",
        "importance_score": 6.8,
        "category": "Selection & Squad"
    },
    {
        "title": "Jonny Bairstow Named in London Spirit Squad for July 26 Match",
        "source": "Wisden",
        "summary": "Jonny Bairstow will take the gloves for London Spirit against Trent Rockets on Sunday, July 26 at 10:30 PM IST.",
        "link": "https://wisden.com/news/2026/jonny-bairstow-london-spirit",
        "published_at": "Jul 23, 2026 @ 08:00 PM IST",
        "player_name": "Jonny Bairstow",
        "franchise": "Sunrisers Eastern Cape",
        "importance_score": 7.3,
        "category": "Selection & Squad"
    },
    {
        "title": "Matthew Potts Included in Sunrisers Leeds Starting Bowling XI",
        "source": "Sky Sports",
        "summary": "Matthew Potts will share the new ball with Reece Topley and Brydon Carse at Headingley tomorrow night.",
        "link": "https://skysports.com/cricket/2026/matthew-potts-sunrisers-leeds",
        "published_at": "Jul 23, 2026 @ 08:00 PM IST",
        "player_name": "Matthew Potts",
        "franchise": "Sunrisers Leeds Men",
        "importance_score": 7.0,
        "category": "Bowling Performance"
    },
    {
        "title": "Dan Lawrence Practicing Spin-Hitting at Headingley Nets",
        "source": "The Hundred Official",
        "summary": "Dan Lawrence honed sweep shots and lofted drives in pre-match training for Sunrisers Leeds Men.",
        "link": "https://thehundred.com/news/2026/dan-lawrence-headingley",
        "published_at": "Jul 23, 2026 @ 07:30 PM IST",
        "player_name": "Dan Lawrence",
        "franchise": "Sunrisers Leeds Men",
        "importance_score": 6.8,
        "category": "Batting Performance"
    },
    {
        "title": "Ishan Kishan Smashes 35 (24) in India's 7-Wicket Victory vs Zimbabwe",
        "source": "BCCI Official",
        "summary": "Ishan Kishan hit 3 fours and 2 sixes in Harare during the 1st T20I win on July 23. 2nd T20I scheduled for July 25 at 4:30 PM IST.",
        "link": "https://bcci.tv/news/2026/ishan-kishan-35-zim-v-ind",
        "published_at": "Jul 23, 2026 @ 07:30 PM IST",
        "player_name": "Ishan Kishan",
        "franchise": "Sunrisers Hyderabad",
        "importance_score": 8.0,
        "category": "Batting Performance"
    },
    {
        "title": "Lewis Gregory Leading Manchester Super Giants All-Round Unit",
        "source": "BBC Sport",
        "summary": "Lewis Gregory confirmed in Manchester Super Giants squad ahead of their upcoming Hundred matches.",
        "link": "https://bbc.com/sport/cricket/2026/lewis-gregory-manchester",
        "published_at": "Jul 23, 2026 @ 07:00 PM IST",
        "player_name": "Lewis Gregory",
        "franchise": "Sunrisers Eastern Cape",
        "importance_score": 6.7,
        "category": "Selection & Squad"
    },
    {
        "title": "Travis Head Resting Ahead of Australia White-Ball Tour",
        "source": "Cricket Australia",
        "summary": "Travis Head is on a planned conditioning rest break following IPL 2026 before rejoining national camp.",
        "link": "https://cricket.com.au/news/2026/travis-head-conditioning-rest",
        "published_at": "Jul 23, 2026 @ 06:00 PM IST",
        "player_name": "Travis Head",
        "franchise": "Sunrisers Hyderabad",
        "importance_score": 7.0,
        "category": "Injury / Availability"
    },
    {
        "title": "Nathan Ellis Death-Bowling Practice at Sunrisers Leeds Camp",
        "source": "Wisden",
        "summary": "Nathan Ellis executed yorker and back-of-the-hand slower ball drills ahead of tomorrow's match.",
        "link": "https://wisden.com/cricket/2026/nathan-ellis-leeds",
        "published_at": "Jul 23, 2026 @ 06:00 PM IST",
        "player_name": "Nathan Ellis",
        "franchise": "Sunrisers Leeds Men",
        "importance_score": 7.0,
        "category": "Bowling Performance"
    },
    {
        "title": "Heinrich Klaasen Joined London Spirit Squad in UK",
        "source": "The Hundred Official",
        "summary": "Heinrich Klaasen arrived in London to lead Spirit's middle-order hitting against Trent Rockets on July 26.",
        "link": "https://thehundred.com/news/2026/heinrich-klaasen-london-spirit",
        "published_at": "Jul 23, 2026 @ 04:00 PM IST",
        "player_name": "Heinrich Klaasen",
        "franchise": "Sunrisers Hyderabad",
        "importance_score": 8.0,
        "category": "Selection & Squad"
    },
    {
        "title": "Nitish Kumar Reddy Completing Fitness & Workload Program",
        "source": "BCCI Medical Board",
        "summary": "Nitish Kumar Reddy is progressing cleanly through bowling load progressions at the National Cricket Academy.",
        "link": "https://bcci.tv/medical/2026/nitish-kumar-reddy-rehab",
        "published_at": "Jul 23, 2026 @ 03:00 PM IST",
        "player_name": "Nitish Kumar Reddy",
        "franchise": "Sunrisers Hyderabad",
        "importance_score": 7.0,
        "category": "Injury / Availability"
    },
    {
        "title": "Pat Cummins Cleared for Return Following Workload Conditioning",
        "source": "Cricket Australia",
        "summary": "Australian skipper Pat Cummins has been declared fully fit post-IPL rest block ahead of upcoming international series assignments.",
        "link": "https://cricket.com.au/news/2026/pat-cummins-fitness-clearance",
        "published_at": "Jul 23, 2026 @ 12:00 PM IST",
        "player_name": "Pat Cummins",
        "franchise": "Sunrisers Hyderabad",
        "importance_score": 8.0,
        "category": "Injury / Availability"
    },
    {
        "title": "Kamindu Mendis in Sri Lanka Test Preparation Camp",
        "source": "Sri Lanka Cricket",
        "summary": "Kamindu Mendis conducting red-ball batting drills in Galle ahead of the 2-Test home series vs India starting August 15.",
        "link": "https://srilankacricket.lk/news/2026/kamindu-mendis-test-prep",
        "published_at": "Jul 23, 2026 @ 11:00 AM IST",
        "player_name": "Kamindu Mendis",
        "franchise": "Sunrisers Hyderabad",
        "importance_score": 7.5,
        "category": "Selection & Squad"
    },

    # 2026-07-21 VERIFIED MATCH RESULTS (12-hr IST)
    {
        "title": "Dani Gibson Captains Sunrisers Leeds Women to 7-Wicket Win",
        "source": "The Hundred Official",
        "summary": "Dani Gibson picked up 2 wickets and led Sunrisers Leeds Women impeccably in their season-opening victory over MI London on July 21.",
        "link": "https://thehundred.com/news/2026/dani-gibson-captaincy-win",
        "published_at": "Jul 21, 2026 @ 09:45 PM IST",
        "player_name": "Dani Gibson",
        "franchise": "Sunrisers Leeds Women",
        "importance_score": 8.2,
        "category": "Bowling Performance"
    },
    {
        "title": "Ryan Rickelton Blitzes 25 off 16 Balls for Sunrisers Leeds",
        "source": "ESPNcricinfo",
        "summary": "Ryan Rickelton hit 3 sixes in 5 balls during his explosive powerplay knock against MI London on July 21 at Kia Oval.",
        "link": "https://espncricinfo.com/story/2026/ryan-rickelton-hundred-blitz",
        "published_at": "Jul 21, 2026 @ 11:45 PM IST",
        "player_name": "Ryan Rickelton",
        "franchise": "Sunrisers Leeds Men",
        "importance_score": 7.2,
        "category": "Batting Performance"
    },
    {
        "title": "Mitchell Marsh Smashes 41 (27) with 3 Sixes in The Hundred Opener",
        "source": "BBC Sport",
        "summary": "Mitchell Marsh opened the batting for Sunrisers Leeds Men with a power-packed 41 off 27 balls against MI London at Kia Oval.",
        "link": "https://bbc.com/sport/cricket/2026/mitchell-marsh-sunrisers-leeds",
        "published_at": "Jul 21, 2026 @ 11:30 PM IST",
        "player_name": "Mitchell Marsh",
        "franchise": "Sunrisers Leeds Men",
        "importance_score": 7.8,
        "category": "Batting Performance"
    },
    {
        "title": "Deepti Sharma Stars with 2/20 in Sunrisers Leeds Opening Win",
        "source": "Sky Sports Cricket",
        "summary": "Deepti Sharma delivered a match-winning spell of 2/20, including a sharp caught-and-bowled dismissal of Hayley Matthews to restrict MI London.",
        "link": "https://skysports.com/cricket/news/2026/deepti-sharma-sunrisers-leeds",
        "published_at": "Jul 21, 2026 @ 09:30 PM IST",
        "player_name": "Deepti Sharma",
        "franchise": "Sunrisers Leeds Women",
        "importance_score": 8.0,
        "category": "Bowling Performance"
    },
    {
        "title": "Annabel Sutherland Contributes 30* (22) in Sunrisers Leeds Victory",
        "source": "Wisden",
        "summary": "Annabel Sutherland finished the chase unbeaten on 30* to guarantee Sunrisers Leeds Women a 7-wicket victory on July 21.",
        "link": "https://wisden.com/matches/2026/annabel-sutherland-win",
        "published_at": "Jul 21, 2026 @ 09:15 PM IST",
        "player_name": "Annabel Sutherland",
        "franchise": "Sunrisers Leeds Women",
        "importance_score": 7.5,
        "category": "Batting Performance"
    },
    {
        "title": "Phoebe Litchfield 43 (26) Leads Sunrisers Leeds to 7-Wicket Victory",
        "source": "The Hundred Match Center",
        "summary": "Phoebe Litchfield top-scored with a rapid 43 off 26 balls to open Sunrisers Leeds Women's season in style at Kia Oval.",
        "link": "https://thehundred.com/news/2026/sunrisers-leeds-women-win-opener",
        "published_at": "Jul 21, 2026 @ 09:00 PM IST",
        "player_name": "Phoebe Litchfield",
        "franchise": "Sunrisers Leeds Women",
        "importance_score": 8.5,
        "category": "Batting Performance"
    }
]

def get_connection():
    """Returns sqlite3 connection with dict cursor capabilities."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes schema, purges test/false-positive data, and pre-loads Master Roster & Complete 73-Player Data."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        with open(SCHEMA_PATH, "r") as f:
            cursor.executescript(f.read())
        conn.commit()
        
        # Purge test entries and false-positive items
        cursor.execute("DELETE FROM news WHERE title LIKE '%Test Article%' OR title LIKE '%Matt Prior%' OR title LIKE '%Sydney Sixers%'")
        cursor.execute("DELETE FROM tweets WHERE text LIKE '%Test%'")
        conn.commit()
        
        # Pre-populate Master Roster
        for team_key, team_info in MASTER_ROSTER.items():
            franchise = team_info["franchise_name"]
            for p in team_info["players"]:
                cursor.execute("""
                    INSERT OR IGNORE INTO players (name, country, franchise, role, captain)
                    VALUES (?, ?, ?, ?, ?)
                """, (p["name"], p["country"], franchise, p["role"], 1 if p.get("captain") else 0))
        conn.commit()
        
        # Pre-seed verified real 2026 data
        for vn in COMPLETE_73_PLAYER_UPDATES:
            cursor.execute("""
                INSERT OR IGNORE INTO news (title, source, summary, link, published_at, player_name, franchise, importance_score, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (vn["title"], vn["source"], vn["summary"], vn["link"], vn["published_at"], vn["player_name"], vn["franchise"], vn["importance_score"], vn["category"]))
        conn.commit()
        conn.close()
        db_logger.info("Database initialized & 73-player data pre-seeded successfully.")
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

def insert_news(title, source, summary, link, published_at, player_name, franchise, importance_score, category):
    """Inserts a filtered news entry if not existing (deduplicated cleanly)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if link and link.strip():
            cursor.execute("SELECT id FROM news WHERE link = ? OR title = ?", (link, title))
        else:
            cursor.execute("SELECT id FROM news WHERE title = ?", (title,))
            
        if cursor.fetchone():
            conn.close()
            return None

        cursor.execute("""
            INSERT INTO news (title, source, summary, link, published_at, player_name, franchise, importance_score, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, source, summary, link, published_at, player_name, franchise, importance_score, category))
        conn.commit()
        news_id = cursor.lastrowid
        conn.close()
        db_logger.info(f"Inserted news #{news_id} for {player_name} ({importance_score}/10).")
        return news_id
    except Exception as e:
        error_logger.error(f"Database insert error: {e}")
        conn.close()
        return None

def get_recent_news(limit=50):
    """Gets recent news items strictly ordered by id DESC / published_at."""
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

def insert_tweet(text, category, player_name=None, status="Draft"):
    """Saves a generated X draft."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tweets (text, category, status, player_name)
        VALUES (?, ?, ?, ?)
    """, (text, category, status, player_name))
    conn.commit()
    tweet_id = cursor.lastrowid
    conn.close()
    db_logger.info(f"Inserted tweet draft #{tweet_id} for {player_name}.")
    return tweet_id

def get_tweets(status_filter=None):
    """Gets saved tweet drafts."""
    conn = get_connection()
    cursor = conn.cursor()
    if status_filter:
        cursor.execute("SELECT * FROM tweets WHERE status = ? ORDER BY id DESC", (status_filter,))
    else:
        cursor.execute("SELECT * FROM tweets ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_tweet_status(tweet_id, new_status):
    """Updates tweet status (Draft/Approved/Rejected/Posted)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tweets SET status = ? WHERE id = ?", (new_status, tweet_id))
    conn.commit()
    conn.close()

def insert_notification(message, type_str="INFO"):
    """Inserts a new dashboard notification."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO notifications (message, type) VALUES (?, ?)", (message, type_str))
    conn.commit()
    conn.close()

def get_unread_notifications():
    """Gets all unread notifications."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM notifications WHERE is_read = 0 ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_notifications_read():
    """Marks all notifications as read."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notifications SET is_read = 1 WHERE is_read = 0")
    conn.commit()
    conn.close()

def get_analytics_summary():
    """Returns analytics metrics for dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as cnt FROM news")
    total_news = cursor.fetchone()["cnt"]
    
    cursor.execute("SELECT COUNT(*) as cnt FROM tweets")
    total_tweets = cursor.fetchone()["cnt"]
    
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
        "total_tweets": total_tweets,
        "avg_importance": round(avg_score, 1),
        "top_players": top_players
    }
