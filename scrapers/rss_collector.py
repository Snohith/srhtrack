"""
Expanded RSS Feed Collector for @SRHXtra V10.0 — Hyper-Local Expansion.
Polls the configured Top-Tier Global & Hyper-Local outlets for all rostered squad members & 4 Franchise Team Names.
Stores EXACT raw source titles and descriptions for direct ESPNcricinfo-style cards.
V9.0 changes (Phase 1):
  - Wired agents/ranker.py into ingestion pipeline (was defined but never called)
  - calculate_importance_score() called per article — real scores stored (not hardcoded 5.0)
  - categorize_news() called per article — real categories stored (not hardcoded 'General')
  - get_source_tier_boost() passed as source_name to ranker for Tier 1/2/3 quality weighting
  - insert_news() now receives importance_score= and category= kwargs
  - Log line includes category + score for every inserted article
  - player_info dict built from MASTER_ROSTER for captain-aware scoring
"""
import time
import requests
import feedparser
import bs4
import html
from config.roster import match_player_or_franchise_in_text, MASTER_ROSTER
from database.db_manager import insert_news, insert_notification
from agents.ranker import calculate_importance_score, categorize_news
from utils.logger import rss_logger, error_logger
from utils.time_utils import parse_rss_date_to_ist, format_ist_12hr
_PLAYER_INFO_CACHE: dict = {}
def get_player_info(player_name):
    if not _PLAYER_INFO_CACHE or player_name not in _PLAYER_INFO_CACHE:
        for _team_info in MASTER_ROSTER.values():
            for _p in _team_info["players"]:
                _PLAYER_INFO_CACHE[_p["name"]] = {
                    "captain": bool(_p.get("captain")),
                    "role": _p.get("role", ""),
                }
    return _PLAYER_INFO_CACHE.get(player_name, {"captain": False, "role": ""})
CRICKET_SOURCES = [
    {"name": "ESPNcricinfo England",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/1.xml"},  
    {"name": "ESPNcricinfo Australia",      "url": "https://www.espncricinfo.com/rss/content/story/feeds/2.xml"},  
    {"name": "ESPNcricinfo South Africa",   "url": "https://www.espncricinfo.com/rss/content/story/feeds/3.xml"},  
    {"name": "ESPNcricinfo India",          "url": "https://www.espncricinfo.com/rss/content/story/feeds/6.xml"},  
    {"name": "ESPNcricinfo Sri Lanka",      "url": "https://www.espncricinfo.com/rss/content/story/feeds/8.xml"},  
    {"name": "Cricbuzz (FeedBurner)",       "url": "https://feeds.feedburner.com/cricbuzz"},                       
    {"name": "ABC News Australia Sport",    "url": "https://www.abc.net.au/news/feed/51120/rss.xml"},              
    {"name": "Telangana Today Sport",       "url": "https://telanganatoday.com/sport/feed"},
    {"name": "The Siasat Daily Hyderabad",  "url": "https://www.siasat.com/feed/"},
    {"name": "Munsif Daily Sports",         "url": "https://munsifdaily.com/category/sports/feed/"},
    {"name": "JioCinema / Sports18 News",   "url": "https://www.news18.com/rss/sports.xml"},
    {"name": "Namasthe Telangana",          "url": "https://www.ntnews.com/feed"},              
    {"name": "V6 Velugu Telangana",         "url": "https://www.v6velugu.com/feed"},
    {"name": "NTV Telugu Sports",           "url": "https://ntvtelugu.com/feed"},
    {"name": "Sakshi Telugu Sports",        "url": "https://www.sakshi.com/rss.xml"},           
    {"name": "BBC Sport Cricket",           "url": "https://feeds.bbci.co.uk/sport/cricket/rss.xml"},
    {"name": "Sky Sports Cricket",          "url": "https://www.skysports.com/rss/12123"},
    {"name": "Yorkshire CCC Official",      "url": "https://yorkshireccc.com/feed/"},
    {"name": "Yorkshire Post Sport",        "url": "https://www.yorkshirepost.co.uk/sport/cricket/rss"},
    {"name": "The Guardian Cricket",        "url": "https://www.theguardian.com/sport/cricket/rss"},
    {"name": "Telegraph UK Sport",          "url": "https://www.telegraph.co.uk/cricket/rss.xml"},
    {"name": "Independent UK Cricket",      "url": "https://www.independent.co.uk/sport/cricket/rss"},
    {"name": "Daily Mail Sport",            "url": "https://www.dailymail.co.uk/sport/cricket/index.rss"},
    {"name": "Evening Standard Sport",      "url": "https://www.standard.co.uk/sport/rss"},
    {"name": "TalkSPORT Cricket",           "url": "https://talksport.com/sport/cricket/feed/"},
    {"name": "Sportstar (The Hindu)",       "url": "https://sportstar.thehindu.com/feeder/default.rss"},  
    {"name": "The Hindu Sports",            "url": "https://www.thehindu.com/sport/cricket/feeder/default.rss"},
    {"name": "NDTV Sports Cricket",         "url": "https://sports.ndtv.com/rss/cricket"},                
    {"name": "Times of India Cricket",      "url": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms"},
    {"name": "Hindustan Times Cricket",     "url": "https://www.hindustantimes.com/feeds/rss/cricket/rssfeed.xml"},
    {"name": "Indian Express Cricket",      "url": "https://indianexpress.com/section/sports/cricket/feed/"},
    {"name": "News18 CricketNext",          "url": "https://www.news18.com/rss/cricketnext.xml"},
    {"name": "CricTracker Global",          "url": "https://www.crictracker.com/feed/"},
    {"name": "Sportskeeda Cricket",         "url": "https://www.sportskeeda.com/feed/cricket"},
    {"name": "OneCricket News",             "url": "https://onecricket.news/feed"},
    {"name": "Cricket Addictor",            "url": "https://cricketaddictor.com/feed/"},
    {"name": "Deccan Chronicle Sports",     "url": "https://www.deccanchronicle.com/rss/sports"},
    {"name": "Business Standard Sports",    "url": "https://www.business-standard.com/rss/sports-108.rss"},
    {"name": "LiveMint Sports",             "url": "https://www.livemint.com/rss/sports"},
    {"name": "Cricket Times",               "url": "https://crickettimes.com/feed/"},
    {"name": "CricketCountry",             "url": "https://www.cricketcountry.com/feed/"},
    {"name": "Zee News Sports",             "url": "https://zeenews.india.com/rss/sports-news.xml"},
    {"name": "RevSportz India",             "url": "https://revsportz.in/feed/"},
    {"name": "InsideSport India",           "url": "https://www.insidesport.in/feed/"},        
    {"name": "KhelNow Cricket",             "url": "https://khelnow.com/feed"},
    {"name": "ABP Live Sports",             "url": "https://news.abplive.com/sports/feed"},
    {"name": "SMH Sport",                   "url": "https://www.smh.com.au/rss/sport.xml"},    
    {"name": "Female Cricket",              "url": "https://femalecricket.com/feed"},
]
TOP_50_CRICKET_SOURCES = CRICKET_SOURCES
RSS_FEEDS = CRICKET_SOURCES
def clean_text(raw):
    """
    Strips HTML tags and unescapes HTML entities, handling double-encoded feeds.
    Some RSS sources (e.g. ABP Live, NTV Telugu) store HTML as entity-encoded text:
      &lt;p&gt;Some text&lt;/p&gt;
    BeautifulSoup parses these as plain text (no tags), then html.unescape() decodes
    them into real <p> tags — which then remain in the output string.
    Fix: run a second BeautifulSoup pass after unescaping to strip any tags that
    appeared after entity decoding.
    """
    if not raw:
        return ""
    pass1 = bs4.BeautifulSoup(raw, "html.parser").get_text()
    pass1 = html.unescape(pass1)
    pass2 = bs4.BeautifulSoup(pass1, "html.parser").get_text()
    return " ".join(pass2.split()).strip()
def fetch_feed_with_retry(url, retries=2, delay=1):
    """Fetches RSS feed with exponential backoff. Makes up to `retries` attempts (default 2)."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for attempt in range(1, retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=3)
            if response.status_code == 200:
                return feedparser.parse(response.content)
        except Exception:
            pass
        time.sleep(delay * attempt)
    return None
def fetch_and_filter_rss():
    """
    Polls all sources in CRICKET_SOURCES, filters for rostered players OR 4 franchise team names.
    STRICTLY DISCARDS any article older than 24 hours.
    Stores EXACT raw headline and description from sources.
    V9.0: Every article is now scored by agents/ranker.py before insertion.
    importance_score (1.0–10.0) and category are stored in the DB.
    Returns:
        _RssResult — int subclass with .inserted, .failed_feeds, .total_polled
    """
    total_inserted = 0
    failed_feeds   = []
    rss_logger.info(
        f"Starting 24-Hour Ingestion Cycle across {len(CRICKET_SOURCES)} sources..."
    )
    for feed_info in CRICKET_SOURCES:
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
            pub_date, age_hours, pub_ts = parse_rss_date_to_ist(entry)
            if age_hours > 24.0:
                continue
            matched_targets = match_player_or_franchise_in_text(f"{title} {summary}")
            for mt in matched_targets:
                player_info = get_player_info(mt["player_name"])
                score    = calculate_importance_score(
                    title=title,
                    summary=summary,
                    player_info=player_info,
                    source_name=feed_info["name"],
                )
                category = categorize_news(title=title, summary=summary)
                news_id = insert_news(
                    title=title,
                    source=feed_info["name"],
                    summary=summary,
                    link=link,
                    published_at=pub_date,
                    player_name=mt["player_name"],
                    franchise=mt["franchise"],
                    pub_timestamp=pub_ts,
                    importance_score=score,
                    category=category,
                )
                if news_id:
                    total_inserted += 1
                    insert_notification(
                        message=(
                            f"⚡ {category} | {mt['player_name']} ({mt['franchise']}) "
                            f"[score={score}]"
                        ),
                        type_str="INFO",
                    )
                    rss_logger.info(
                        f"  ↳ [{score:>5}] [{category}] {mt['player_name']} — {title[:60]}"
                    )
    rss_logger.info(
        f"Ingestion Cycle complete. {total_inserted} fresh items stored. "
        f"{len(failed_feeds)}/{len(CRICKET_SOURCES)} feeds failed."
    )
    return _RssResult(total_inserted, failed_feeds, len(CRICKET_SOURCES))
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
