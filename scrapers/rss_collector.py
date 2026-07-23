"""
Expanded RSS Feed Collector for @SRHXtra V2.2.
Features 30 Top-Tier Reliable Global Cricket Data & News Outlets.
Stores ISO timestamps and formats strictly into 12-hour AM/PM IST.
"""

import time
import requests
import feedparser
import bs4
import html
from config.roster import match_player_in_text
from agents.ranker import calculate_importance_score, categorize_news
from agents.tweet_generator import generate_tweet_drafts
from database.db_manager import insert_news, insert_tweet, insert_notification
from utils.logger import rss_logger, error_logger
from utils.time_utils import format_ist_12hr

# 30 Top-Tier Reliable Global Cricket Outlets
TOP_30_CRICKET_SOURCES = [
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
    {"name": "Indian Express Cricket", "url": "https://indianexpress.com/section/sports/cricket/feed/"},
    {"name": "Hindustan Times Cricket", "url": "https://www.hindustantimes.com/feeds/rss/cricket/rssfeed.xml"},
    {"name": "Times of India Cricket", "url": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms"},
    {"name": "DNA India Cricket", "url": "https://www.dnaindia.com/feeds/cricket.xml"},
    {"name": "Firstpost Sports", "url": "https://www.firstpost.com/rss/sports.xml"},
    {"name": "India Today Sports", "url": "https://www.indiatoday.in/rss/1206584"},
    {"name": "Outlook India Sports", "url": "https://www.outlookindia.com/rss/sports"},
    {"name": "OneCricket News", "url": "https://onecricket.news/feed"},
    {"name": "Sportskeeda Cricket", "url": "https://www.sportskeeda.com/feed/cricket"},
    {"name": "Financial Express Sports", "url": "https://www.financialexpress.com/about/sports/feed/"},
    {"name": "Deccan Chronicle Sports", "url": "https://www.deccanchronicle.com/rss/sports"},
    {"name": "Telegraph UK Sport", "url": "https://www.telegraph.co.uk/cricket/rss.xml"},
    {"name": "The Guardian Cricket", "url": "https://www.theguardian.com/sport/cricket/rss"},
    {"name": "Independent UK Cricket", "url": "https://www.independent.co.uk/sport/cricket/rss"},
    {"name": "Fox Sports Australia", "url": "https://service.foxsports.com.au/Rss/ffx/cricket.xml"},
    {"name": "SuperSport Cricket", "url": "https://ss-rss.supersport.com/cricket"},
    {"name": "ICC Official News", "url": "https://www.icc-cricket.com/rss/news"},
    {"name": "Wisden Cricket", "url": "https://wisden.com/feed"}
]

def clean_text(raw):
    """Strips HTML tags and unescapes HTML entities cleanly."""
    if not raw:
        return ""
    text_no_html = bs4.BeautifulSoup(raw, "html.parser").get_text()
    return html.unescape(text_no_html).strip()

def fetch_feed_with_retry(url, retries=2, delay=1):
    """Fetches RSS feed with exponential backoff retry logic."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response.status_code == 200:
                return feedparser.parse(response.content)
        except Exception as e:
            pass
        time.sleep(delay * attempt)
    return None

def fetch_and_filter_rss():
    """Polls 30 top global sources, filters Sunrisers players, ranks impact, and stores clean 12hr AM/PM IST entries."""
    total_found = 0
    rss_logger.info(f"Starting Ingestion Cycle across {len(TOP_30_CRICKET_SOURCES)} Reliable Sources...")
    
    for feed_info in TOP_30_CRICKET_SOURCES:
        feed = fetch_feed_with_retry(feed_info["url"])
        if not feed or not feed.entries:
            continue
            
        for entry in feed.entries:
            title = clean_text(entry.get("title", ""))
            summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
            link = entry.get("link", "")
            pub_date = format_ist_12hr()
            
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
                                    message=f"🔥 PRIORITY UPDATE ({score}/10): {mp['player_name']} ({mp['franchise']})",
                                    type_str="PRIORITY"
                                )
    
    rss_logger.info(f"30-Source Ingestion Cycle Complete. {total_found} new Sunrisers items processed.")
    return total_found
