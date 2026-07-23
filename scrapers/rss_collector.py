"""
Expanded RSS Feed Collector for @SRHXtra V1.5.
Features 16 Top-Tier Verified Global Cricket Data & News Sources.
"""

import time
import requests
import feedparser
from config.roster import match_player_in_text
from agents.ranker import calculate_importance_score, categorize_news
from agents.tweet_generator import generate_tweet_drafts
from database.db_manager import insert_news, insert_tweet, insert_notification
from utils.logger import rss_logger, error_logger
from utils.time_utils import format_ist_string

# 16 Verified Active Global Cricket Data & News Outlets
TOP_16_CRICKET_SOURCES = [
    {"name": "ESPNcricinfo Main News", "url": "https://www.espncricinfo.com/rss/content/story/news.xml"},
    {"name": "Cricbuzz Latest", "url": "https://www.cricbuzz.com/rss/cricket-news"},
    {"name": "BBC Sport Cricket", "url": "https://feeds.bbci.co.uk/sport/cricket/rss.xml"},
    {"name": "Sky Sports Cricket", "url": "https://www.skysports.com/rss/12123"},
    {"name": "Cricket Times", "url": "https://crickettimes.com/feed/"},
    {"name": "Female Cricket", "url": "https://femalecricket.com/feed"},
    {"name": "CricTracker Global", "url": "https://www.crictracker.com/feed/"},
    {"name": "News18 CricketNext", "url": "https://www.news18.com/rss/cricketnext.xml"},
    {"name": "IPL Official News", "url": "https://www.iplt20.com/rss/news"},
    {"name": "SA20 Official News", "url": "https://www.sa20.co.za/feed"},
    {"name": "NDTV Sports Cricket", "url": "https://sports.ndtv.com/cricket/rss"},
    {"name": "The Hindu Sports", "url": "https://www.thehindu.com/sport/cricket/feeder/default.rss"},
    {"name": "Indian Express Sports", "url": "https://indianexpress.com/section/sports/cricket/feed/"},
    {"name": "Hindustan Times Cricket", "url": "https://www.hindustantimes.com/feeds/rss/cricket/rssfeed.xml"},
    {"name": "Times of India Sports", "url": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms"},
    {"name": "DNA India Sports", "url": "https://www.dnaindia.com/feeds/cricket.xml"}
]

def fetch_feed_with_retry(url, retries=2, delay=1):
    """Fetches RSS feed content with exponential backoff retries."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                rss_logger.info(f"Successfully fetched feed '{url}' on attempt {attempt}.")
                return feedparser.parse(response.content)
            else:
                rss_logger.warning(f"Attempt {attempt}: HTTP {response.status_code} for '{url}'")
        except Exception as e:
            rss_logger.warning(f"Attempt {attempt} failed for '{url}': {e}")
        time.sleep(delay * attempt)
    
    error_logger.error(f"Failed to fetch RSS feed '{url}' after {retries} attempts.")
    return None

def fetch_and_filter_rss():
    """Fetches 16 top-tier RSS feeds, deduplicates, ranks importance, and auto-drafts based on thresholds."""
    total_found = 0
    rss_logger.info(f"Starting Ingestion Cycle across {len(TOP_16_CRICKET_SOURCES)} Reliable Sources...")
    
    for feed_info in TOP_16_CRICKET_SOURCES:
        feed = fetch_feed_with_retry(feed_info["url"])
        if not feed or not feed.entries:
            continue
            
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")
            link = entry.get("link", "")
            pub_date = entry.get("published", "") or format_ist_string()
            
            matched_players = match_player_in_text(f"{title} {summary}")
            if matched_players:
                for mp in matched_players:
                    score = calculate_importance_score(title, summary, mp)
                    category = categorize_news(title, summary)
                    
                    news_id = insert_news(
                        title=title,
                        source=feed_info["name"],
                        summary=summary[:300] + "..." if len(summary) > 300 else summary,
                        link=link,
                        published_at=pub_date,
                        player_name=mp["player_name"],
                        franchise=mp["franchise"],
                        importance_score=score,
                        category=category
                    )
                    
                    if news_id:
                        total_found += 1
                        
                        if score >= 4.0:
                            drafts = generate_tweet_drafts(mp["player_name"], mp["franchise"], summary[:200])
                            insert_tweet(drafts["draft_1"], category, mp["player_name"])
                            
                            if score >= 7.0:
                                insert_tweet(drafts["draft_2"], "High Priority News", mp["player_name"])
                                insert_notification(
                                    message=f"🔥 PRIORITY UPDATE ({score}/10): {mp['player_name']} ({mp['franchise']}) - Source: {feed_info['name']}",
                                    type_str="PRIORITY"
                                )
                                rss_logger.info(f"Auto-generated Priority Drafts for {mp['player_name']} (Score: {score})")
                            else:
                                insert_notification(
                                    message=f"New update: {mp['player_name']} ({mp['franchise']}) - Score: {score}/10",
                                    type_str="MATCH"
                                )
    
    rss_logger.info(f"16-Source Ingestion Cycle Complete. {total_found} new Sunrisers items processed.")
    return total_found
