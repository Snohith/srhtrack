"""
Expanded RSS Feed Collector for @SRHXtra V3.0.
Features 50 Top-Tier Relevant Global Cricket Data & Media Outlets.
Ingestion Engine storing deduplicated single-topic multi-source player reconnaissance updates in 12-Hour AM/PM IST.
"""

import time
import requests
import feedparser
import bs4
import html
from config.roster import match_player_in_text
from agents.ranker import calculate_importance_score, categorize_news
from database.db_manager import insert_or_consolidate_news, insert_notification
from utils.logger import rss_logger, error_logger
from utils.time_utils import format_ist_12hr

# 50 TOP-TIER RELEVANT GLOBAL CRICKET MEDIA OUTLETS
TOP_50_CRICKET_SOURCES = [
    # --- GLOBAL & LEAGUE OFFICIALS ---
    {"name": "ESPNcricinfo Story News", "url": "https://www.espncricinfo.com/rss/content/story/news.xml"},
    {"name": "Cricbuzz Latest News", "url": "https://www.cricbuzz.com/rss/cricket-news"},
    {"name": "IPL Official News", "url": "https://www.iplt20.com/rss/news"},
    {"name": "SA20 Official News", "url": "https://www.sa20.co.za/feed"},
    {"name": "ICC Official News", "url": "https://www.icc-cricket.com/rss/news"},
    {"name": "Cricket Australia", "url": "https://www.cricket.com.au/rss/news"},
    {"name": "BCCI Official News", "url": "https://www.bcci.tv/rss/news"},
    
    # --- UK & THE HUNDRED (Sunrisers Leeds Men & Women) ---
    {"name": "BBC Sport Cricket", "url": "https://feeds.bbci.co.uk/sport/cricket/rss.xml"},
    {"name": "Sky Sports Cricket", "url": "https://www.skysports.com/rss/12123"},
    {"name": "Wisden Cricket", "url": "https://wisden.com/feed"},
    {"name": "The Hundred Official", "url": "https://www.thehundred.com/rss/news"},
    {"name": "Telegraph UK Sport", "url": "https://www.telegraph.co.uk/cricket/rss.xml"},
    {"name": "The Guardian Cricket", "url": "https://www.theguardian.com/sport/cricket/rss"},
    {"name": "Independent UK Cricket", "url": "https://www.independent.co.uk/sport/cricket/rss"},
    {"name": "Daily Mail Sport", "url": "https://www.dailymail.co.uk/sport/cricket/index.rss"},
    {"name": "Yorkshire Post Sport", "url": "https://www.yorkshirepost.co.uk/sport/cricket/rss"},
    {"name": "TalkSPORT Cricket", "url": "https://talksport.com/sport/cricket/feed/"},
    
    # --- INDIA MEDIA (Sunrisers Hyderabad / IPL & National) ---
    {"name": "News18 CricketNext", "url": "https://www.news18.com/rss/cricketnext.xml"},
    {"name": "CricTracker Global", "url": "https://www.crictracker.com/feed/"},
    {"name": "Sportskeeda Cricket", "url": "https://www.sportskeeda.com/feed/cricket"},
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
    {"name": "MyKhel Cricket News", "url": "https://www.mykhel.com/rss/cricket-fb.xml"},
    {"name": "Financial Express Sports", "url": "https://www.financialexpress.com/about/sports/feed/"},
    {"name": "Deccan Chronicle Sports", "url": "https://www.deccanchronicle.com/rss/sports"},
    {"name": "Business Standard Sports", "url": "https://www.business-standard.com/rss/sports-108.rss"},
    {"name": "LiveMint Sports", "url": "https://www.livemint.com/rss/sports"},
    {"name": "Cricket Times", "url": "https://crickettimes.com/feed/"},
    {"name": "InsideSport Cricket", "url": "https://www.insidesport.in/cricket/feed/"},
    {"name": "Zee News Sports", "url": "https://zeenews.india.com/rss/sports-news.xml"},
    
    # --- SOUTH AFRICA MEDIA (Sunrisers Eastern Cape / SA20) ---
    {"name": "SuperSport Cricket", "url": "https://ss-rss.supersport.com/cricket"},
    {"name": "Cricket South Africa", "url": "https://cricket.co.za/feed/"},
    {"name": "IOL South Africa Sport", "url": "https://www.iol.co.za/crss/sport/cricket"},
    {"name": "News24 SA Sport", "url": "https://feeds.news24.com/articles/sport/cricket/rss"},
    {"name": "TimesLIVE SA Sport", "url": "https://www.timeslive.co.za/rss/?publication=sport"},
    
    # --- AUSTRALIA & WOMEN'S CRICKET ---
    {"name": "Fox Sports Australia", "url": "https://service.foxsports.com.au/Rss/ffx/cricket.xml"},
    {"name": "Nine Wide World of Sports", "url": "https://wwos.ninemsn.com.au/rss/cricket"},
    {"name": "ABC News Australia Sport", "url": "https://www.abc.net.au/news/feed/51120/rss.xml"},
    {"name": "Sydney Morning Herald Sport", "url": "https://www.smh.com.au/rss/sport/cricket.xml"},
    {"name": "Female Cricket", "url": "https://femalecricket.com/feed"},
    {"name": "Women's CricZone", "url": "https://www.womenscriczone.com/feed"}
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
        except Exception:
            pass
        time.sleep(delay * attempt)
    return None

def fetch_and_filter_rss():
    """Polls 50 top global sources, filters Sunrisers players, ranks impact, and stores clean single-topic consolidated entries."""
    total_found = 0
    rss_logger.info(f"Starting Ingestion Cycle across {len(TOP_50_CRICKET_SOURCES)} Reliable Sources...")
    
    for feed_info in TOP_50_CRICKET_SOURCES:
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
                    
                    news_id = insert_or_consolidate_news(
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
                        if score >= 7.0:
                            insert_notification(
                                message=f"🔥 PRIORITY UPDATE ({score}/10): {mp['player_name']} ({mp['franchise']})",
                                type_str="PRIORITY"
                            )
    
    rss_logger.info(f"50-Source Ingestion Cycle Complete. {total_found} new Sunrisers items processed.")
    return total_found
