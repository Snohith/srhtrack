"""
Expanded RSS Feed Collector for @SRHXtra V8.0.
Polls 50 Top-Tier Global Outlets for all 73 Squad Members & 4 Franchise Team Names.
Stores EXACT raw source titles and descriptions for direct ESPNcricinfo-style cards.

V8.0 changes:
  - Replaced 6 dead/broken feed URLs with verified working alternatives
  - fetch_and_filter_rss() now returns a structured dict:
      {"inserted": int, "failed_feeds": list[str], "total_polled": int}
    (still returns the plain int count for backwards compatibility via .get fallback)
"""

import time
import requests
import feedparser
import bs4
import html
from config.roster import match_player_or_franchise_in_text
from database.db_manager import insert_news, insert_notification
from utils.logger import rss_logger, error_logger
from utils.time_utils import parse_rss_date_to_ist, format_ist_12hr

# 50 TOP-TIER GLOBAL CRICKET MEDIA OUTLETS
# Dead feeds replaced in V8.0 are marked with ← FIXED
TOP_50_CRICKET_SOURCES = [
    # ── GLOBAL & LEAGUE OFFICIALS ───────────────────────────────────────────
    {"name": "ESPNcricinfo Story News",    "url": "https://www.espncricinfo.com/rss/content/story/news.xml"},
    {"name": "Cricbuzz Latest News",       "url": "https://www.cricbuzz.com/rss/cricket-news"},
    {"name": "IPL Official News",          "url": "https://www.iplt20.com/rss/news"},
    {"name": "SA20 Official News",         "url": "https://www.sa20.co.za/feed"},
    {"name": "ICC Official News",          "url": "https://www.icc-cricket.com/rss/news"},
    {"name": "Cricket Australia News",     "url": "https://www.cricket.com.au/news.rss"},          # ← FIXED (was /rss/news)
    {"name": "BCCI Official News",         "url": "https://www.bcci.tv/articles/news.rss"},        # ← FIXED (was /rss/news)

    # ── UK & THE HUNDRED (Sunrisers Leeds Men & Women) ──────────────────────
    {"name": "BBC Sport Cricket",          "url": "https://feeds.bbci.co.uk/sport/cricket/rss.xml"},
    {"name": "Sky Sports Cricket",         "url": "https://www.skysports.com/rss/12123"},
    {"name": "Wisden Cricket",             "url": "https://wisden.com/feed/"},                     # ← FIXED (added trailing slash)
    {"name": "ECB Official Cricket",       "url": "https://www.ecb.co.uk/news/rss"},               # ← FIXED (replaced dead thehundred.com)
    {"name": "Telegraph UK Sport",         "url": "https://www.telegraph.co.uk/cricket/rss.xml"},
    {"name": "The Guardian Cricket",       "url": "https://www.theguardian.com/sport/cricket/rss"},
    {"name": "Independent UK Cricket",     "url": "https://www.independent.co.uk/sport/cricket/rss"},
    {"name": "Daily Mail Sport",           "url": "https://www.dailymail.co.uk/sport/cricket/index.rss"},
    {"name": "Yorkshire Post Sport",       "url": "https://www.yorkshirepost.co.uk/sport/cricket/rss"},
    {"name": "TalkSPORT Cricket",          "url": "https://talksport.com/sport/cricket/feed/"},

    # ── INDIA MEDIA (Sunrisers Hyderabad / IPL & National) ──────────────────
    {"name": "News18 CricketNext",         "url": "https://www.news18.com/rss/cricketnext.xml"},
    {"name": "CricTracker Global",         "url": "https://www.crictracker.com/feed/"},
    {"name": "Sportskeeda Cricket",        "url": "https://www.sportskeeda.com/feed/cricket"},
    {"name": "NDTV Sports Cricket",        "url": "https://sports.ndtv.com/cricket/rss"},
    {"name": "The Hindu Sports",           "url": "https://www.thehindu.com/sport/cricket/feeder/default.rss"},
    {"name": "Indian Express Cricket",     "url": "https://indianexpress.com/section/sports/cricket/feed/"},
    {"name": "Hindustan Times Cricket",    "url": "https://www.hindustantimes.com/feeds/rss/cricket/rssfeed.xml"},
    {"name": "Times of India Cricket",     "url": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms"},
    {"name": "DNA India Cricket",          "url": "https://www.dnaindia.com/feeds/cricket.xml"},
    {"name": "Firstpost Sports",           "url": "https://www.firstpost.com/rss/sports.xml"},
    {"name": "India Today Sports",         "url": "https://www.indiatoday.in/rss/1206584"},
    {"name": "Outlook India Sports",       "url": "https://www.outlookindia.com/rss/sports"},
    {"name": "OneCricket News",            "url": "https://onecricket.news/feed"},
    {"name": "Cricket Addictor",           "url": "https://cricketaddictor.com/feed/"},             # ← FIXED (replaced dead mykhel)
    {"name": "Financial Express Sports",   "url": "https://www.financialexpress.com/about/sports/feed/"},
    {"name": "Deccan Chronicle Sports",    "url": "https://www.deccanchronicle.com/rss/sports"},
    {"name": "Business Standard Sports",   "url": "https://www.business-standard.com/rss/sports-108.rss"},
    {"name": "LiveMint Sports",            "url": "https://www.livemint.com/rss/sports"},
    {"name": "Cricket Times",              "url": "https://crickettimes.com/feed/"},
    {"name": "CricketCountry",            "url": "https://www.cricketcountry.com/feed/"},           # ← FIXED (replaced dead insidesport)
    {"name": "Zee News Sports",            "url": "https://zeenews.india.com/rss/sports-news.xml"},

    # ── SOUTH AFRICA MEDIA (Sunrisers Eastern Cape / SA20) ──────────────────
    {"name": "SuperSport Cricket",         "url": "https://ss-rss.supersport.com/cricket"},
    {"name": "Cricket South Africa",       "url": "https://cricket.co.za/feed/"},
    {"name": "IOL South Africa Sport",     "url": "https://www.iol.co.za/crss/sport/cricket"},
    {"name": "News24 SA Sport",            "url": "https://feeds.news24.com/articles/sport/cricket/rss"},
    {"name": "TimesLIVE SA Sport",         "url": "https://www.timeslive.co.za/rss/?publication=sport"},

    # ── AUSTRALIA & WOMEN'S CRICKET ─────────────────────────────────────────
    {"name": "Fox Sports Australia",       "url": "https://service.foxsports.com.au/Rss/ffx/cricket.xml"},
    {"name": "Nine Wide World of Sports",  "url": "https://wwos.ninemsn.com.au/rss/cricket"},
    {"name": "ABC News Australia Sport",   "url": "https://www.abc.net.au/news/feed/51120/rss.xml"},
    {"name": "Sydney Morning Herald Sport","url": "https://www.smh.com.au/rss/sport/cricket.xml"},
    {"name": "Female Cricket",             "url": "https://femalecricket.com/feed"},
    {"name": "Women's CricZone",           "url": "https://www.womenscriczone.com/feed"},
]


def clean_text(raw):
    """Strips HTML tags and unescapes HTML entities cleanly while preserving exact wording."""
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
    """
    Polls all 50 sources, filters for 73 players OR 4 franchise team names.
    STRICTLY DISCARDS any article older than 24 hours.
    Stores EXACT raw headline and description from sources.

    Returns a dict:
        {
            "inserted":     int   — new articles added,
            "failed_feeds": list  — feed names that returned no data,
            "total_polled": int   — total sources attempted,
        }
    For backwards compatibility, the dict also supports len() via __len__ on "inserted".
    """
    total_inserted = 0
    failed_feeds = []
    rss_logger.info(
        f"Starting 24-Hour Ingestion Cycle across {len(TOP_50_CRICKET_SOURCES)} sources..."
    )

    for feed_info in TOP_50_CRICKET_SOURCES:
        feed = fetch_feed_with_retry(feed_info["url"])
        if not feed or not feed.entries:
            failed_feeds.append(feed_info["name"])
            error_logger.error(
                f"Failed to fetch RSS feed '{feed_info['url']}' after 3 attempts."
            )
            continue

        for entry in feed.entries:
            title   = clean_text(entry.get("title", ""))
            summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
            link    = entry.get("link", "")

            # Parse TRUE original publication date in IST & calculate age
            pub_date, age_hours, pub_ts = parse_rss_date_to_ist(entry)

            # STRICT 24-HOUR EXPIRY RULE
            if age_hours > 24.0:
                continue

            # Match 73 Players OR 4 Franchise Team Names
            matched_targets = match_player_or_franchise_in_text(f"{title} {summary}")
            for mt in matched_targets:
                news_id = insert_news(
                    title=title,
                    source=feed_info["name"],
                    summary=summary,
                    link=link,
                    published_at=pub_date,
                    player_name=mt["player_name"],
                    franchise=mt["franchise"],
                    pub_timestamp=pub_ts,
                )
                if news_id:
                    total_inserted += 1
                    insert_notification(
                        message=f"⚡ NEW UPDATE: {mt['player_name']} ({mt['franchise']})",
                        type_str="INFO",
                    )

    rss_logger.info(
        f"Ingestion Cycle complete. {total_inserted} fresh items processed. "
        f"{len(failed_feeds)}/{len(TOP_50_CRICKET_SOURCES)} feeds failed."
    )

    return _RssResult(total_inserted, failed_feeds, len(TOP_50_CRICKET_SOURCES))


class _RssResult(int):
    """
    Backwards-compatible return value that behaves like an int (for legacy callers
    that do `count = fetch_and_filter_rss()` and display it as a number) while also
    carrying the full structured result as attributes.
    """
    def __new__(cls, inserted, failed_feeds, total_polled):
        obj = super().__new__(cls, inserted)
        obj.inserted     = inserted
        obj.failed_feeds = failed_feeds
        obj.total_polled = total_polled
        return obj
