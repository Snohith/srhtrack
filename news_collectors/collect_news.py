"""RSS discovery for SRHXtra.

This module only collects and stores articles.  Telegram delivery happens in
helpers/phone_alerts.py after the sweep, so a network failure in either half
cannot silently lose the other half.

The feed list below is the existing 268-source list from the repository.  A
broken feed is logged, given exponential backoff in SQLite, and never stops
the rest of the sweep.
"""
from __future__ import annotations

import concurrent.futures
import time
from dataclasses import dataclass, field

import bs4
import feedparser
import html
import requests

from helpers.dates_and_times import read_story_date_as_indian_time
from helpers.links import canonicalize_url
from helpers.log_books import news_diary, problems_diary
from our_teams.players import find_our_players_in_story
from saved_stories.story_storage import (
    feed_is_due,
    record_feed_failure,
    record_feed_success,
    save_article,
)

MAX_ARTICLE_AGE_HOURS = 24.0
FETCH_TIMEOUT_SECS = 8
FETCH_RETRIES = 1
MAX_WORKERS = 16
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


@dataclass
class CollectionResult:
    inserted: int = 0
    matched: int = 0
    duplicates: int = 0
    stale: int = 0
    invalid_links: int = 0
    total_feeds: int = 0
    polled_feeds: int = 0
    skipped_feeds: int = 0
    failed_feeds: list = field(default_factory=list)
    new_articles: list = field(default_factory=list)

    def __int__(self):
        return self.inserted


NEWS_WEBSITES = [
    # ── Global & Multi-National Cricket Coverage ───────────────────────────
    {"name": "ESPNcricinfo England",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/1.xml"},  
    {"name": "ESPNcricinfo Australia",      "url": "https://www.espncricinfo.com/rss/content/story/feeds/2.xml"},  
    {"name": "ESPNcricinfo South Africa",   "url": "https://www.espncricinfo.com/rss/content/story/feeds/3.xml"},  
    {"name": "ESPNcricinfo India",          "url": "https://www.espncricinfo.com/rss/content/story/feeds/6.xml"},  
    {"name": "ESPNcricinfo Sri Lanka",      "url": "https://www.espncricinfo.com/rss/content/story/feeds/8.xml"},  
    {"name": "Cricbuzz (FeedBurner)",       "url": "https://feeds.feedburner.com/cricbuzz"},                       
    {"name": "CricTracker Global",          "url": "https://www.crictracker.com/feed/"},
    {"name": "Sportskeeda Cricket",         "url": "https://www.sportskeeda.com/feed/cricket"},
    {"name": "OneCricket News",             "url": "https://onecricket.news/feed"},
    {"name": "Cricket Addictor",            "url": "https://cricketaddictor.com/feed/"},
    {"name": "Cricket Times",               "url": "https://crickettimes.com/feed/"},

    # ── Franchise 1: Sunrisers Hyderabad (IPL & Regional Media) ─────────────
    {"name": "Google News: Sunrisers Hyderabad", "url": "https://news.google.com/rss/search?q=Sunrisers+Hyderabad+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Telangana Today Sport",       "url": "https://telanganatoday.com/sport/feed"},
    {"name": "The Siasat Daily Hyderabad",  "url": "https://www.siasat.com/feed/"},
    {"name": "Munsif Daily Sports",         "url": "https://munsifdaily.com/category/sports/feed/"},
    {"name": "Namasthe Telangana",          "url": "https://www.ntnews.com/feed"},              
    {"name": "V6 Velugu Telangana",         "url": "https://www.v6velugu.com/feed"},
    {"name": "NTV Telugu Sports",           "url": "https://ntvtelugu.com/feed"},
    {"name": "Sakshi Telugu Sports",        "url": "https://www.sakshi.com/rss.xml"},           
    {"name": "JioCinema / Sports18 News",   "url": "https://www.news18.com/rss/sports.xml"},
    {"name": "Sportstar (The Hindu)",       "url": "https://sportstar.thehindu.com/feeder/default.rss"},  
    {"name": "The Hindu Sports",            "url": "https://www.thehindu.com/sport/cricket/feeder/default.rss"},
    {"name": "NDTV Sports Cricket",         "url": "https://feeds.feedburner.com/ndtvsports-cricket"},                
    {"name": "Times of India Cricket",      "url": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms"},
    {"name": "Hindustan Times Cricket",     "url": "https://www.hindustantimes.com/feeds/rss/cricket/rssfeed.xml"},
    {"name": "Indian Express Cricket",      "url": "https://indianexpress.com/section/sports/cricket/feed/"},
    {"name": "News18 CricketNext",          "url": "https://www.news18.com/rss/cricketnext.xml"},
    {"name": "Deccan Chronicle Sports",     "url": "https://news.google.com/rss/search?q=site:deccanchronicle.com+sports&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Business Standard Sports",    "url": "https://www.business-standard.com/rss/sports-108.rss"},
    {"name": "LiveMint Sports",             "url": "https://www.livemint.com/rss/sports"},
    {"name": "Zee News Sports",             "url": "https://news.google.com/rss/search?q=site:zeenews.india.com+sports&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "RevSportz India",             "url": "https://revsportz.in/feed/"},
    {"name": "InsideSport India",           "url": "https://www.insidesport.in/feed/"},        
    {"name": "KhelNow Cricket",             "url": "https://khelnow.com/feed"},
    {"name": "ABP Live Sports",             "url": "https://news.abplive.com/sports/feed"},

    # ── Franchise 2: Sunrisers Eastern Cape (SA20 & South African Media) ────
    {"name": "Google News: Sunrisers Eastern Cape", "url": "https://news.google.com/rss/search?q=Sunrisers+Eastern+Cape+SA20&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: SA20 Cricket League",   "url": "https://news.google.com/rss/search?q=SA20+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "SA Cricket Mag",              "url": "https://www.sacricketmag.com/feed/"},

    # ── Franchise 3: Sunrisers Leeds Men (The Hundred & UK Media) ───────────
    {"name": "Google News: Sunrisers Leeds Men", "url": "https://news.google.com/rss/search?q=Sunrisers+Leeds+The+Hundred&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: The Hundred Cricket", "url": "https://news.google.com/rss/search?q=The+Hundred+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "BBC Sport Cricket",           "url": "https://feeds.bbci.co.uk/sport/cricket/rss.xml"},
    {"name": "Sky Sports Cricket",          "url": "https://www.skysports.com/rss/12123"},
    {"name": "Yorkshire CCC Official",      "url": "https://yorkshireccc.com/feed/"},
    {"name": "The Guardian Cricket",        "url": "https://www.theguardian.com/sport/cricket/rss"},
    {"name": "Independent UK Cricket",      "url": "https://www.independent.co.uk/sport/cricket/rss"},
    {"name": "Daily Mail Sport",            "url": "https://www.dailymail.co.uk/sport/cricket/index.rss"},
    {"name": "Evening Standard Sport",      "url": "https://www.standard.co.uk/sport/rss"},
    {"name": "TalkSPORT Cricket",           "url": "https://talksport.com/sport/cricket/feed/"},

    # ── Franchise 4: Sunrisers Leeds Women (The Hundred Women & Women's Cricket) ─
    {"name": "Google News: Sunrisers Leeds Women", "url": "https://news.google.com/rss/search?q=Sunrisers+Leeds+Women+The+Hundred&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Women's Cricket World", "url": "https://news.google.com/rss/search?q=womens+cricket+The+Hundred+or+IPL&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Female Cricket",              "url": "https://femalecricket.com/feed"},

    # ── Premium Editorial & Long-Form ────────────────────────────────────
    {"name": "Wisden Cricket",              "url": "https://www.wisden.com/feed"},

    # ── Official League, Board & Franchise Channels (search mirrors) ──────
    # These publishers expose no public RSS/Atom feed (verified 2026-10-07:
    # /feed and /rss return 404 on iplt20.com, bcci.tv, sa20.co.za,
    # thehundred.com, sunrisershyderabad.in, sunriserseasterncape.co), so each
    # is polled via a site-restricted Google News RSS mirror — the same pattern
    # already used for Deccan Chronicle / Zee News above.
    {"name": "Google News: IPL Official",   "url": "https://news.google.com/rss/search?q=site:iplt20.com&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: SRH Official Site", "url": "https://news.google.com/rss/search?q=site:sunrisershyderabad.in&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: BCCI Official",  "url": "https://news.google.com/rss/search?q=site:bcci.tv&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: SA20 Official",  "url": "https://news.google.com/rss/search?q=site:sa20.co.za&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: SEC Official Site", "url": "https://news.google.com/rss/search?q=site:sunriserseasterncape.co&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: The Hundred Official", "url": "https://news.google.com/rss/search?q=site:thehundred.com&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: ECB Official",   "url": "https://news.google.com/rss/search?q=site:ecb.co.uk&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── Women's Game Depth ───────────────────────────────────────────────
    {"name": "Google News: England Women's Cricket", "url": "https://news.google.com/rss/search?q=England+women+cricket+Hundred+or+WPL&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── Ownership, Business & Leadership (Sun Group umbrella) ────────────
    # Sun TV Network IR pages, Companies House filings and Wikipedia are
    # reference sources with no news RSS, so business/leadership coverage is
    # tracked via targeted topic mirrors: exchange-disclosure reporting, the
    # Leeds Companies House / rebrand paper trail, and CEO Kavya Maran.
    {"name": "Economic Times Cricket",      "url": "https://news.google.com/rss/search?q=site:economictimes.indiatimes.com+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Sun TV Network Business", "url": "https://news.google.com/rss/search?q=Sun+TV+Network+revenue+or+valuation+or+filings+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Kavya Maran",    "url": "https://news.google.com/rss/search?q=Kavya+Maran+Sunrisers&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Sunrisers Leeds Business", "url": "https://news.google.com/rss/search?q=Sunrisers+Leeds+Companies+House+or+stake+or+rebrand&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── Australia & International (Cummins, Head, Sutherland, Marsh) ───────
    {"name": "ABC News Australia Sport",    "url": "https://www.abc.net.au/news/feed/51120/rss.xml"},
    {"name": "SMH Sport",                   "url": "https://www.smh.com.au/rss/sport.xml"},

    # ── ESPNcricinfo Feed Expansion (IDs beyond the core 5) ───────────────
    {"name": "ESPNcricinfo Feed 4",         "url": "https://www.espncricinfo.com/rss/content/story/feeds/4.xml"},
    {"name": "ESPNcricinfo Feed 5",         "url": "https://www.espncricinfo.com/rss/content/story/feeds/5.xml"},
    {"name": "ESPNcricinfo Feed 7",         "url": "https://www.espncricinfo.com/rss/content/story/feeds/7.xml"},
    {"name": "ESPNcricinfo Feed 9",         "url": "https://www.espncricinfo.com/rss/content/story/feeds/9.xml"},
    {"name": "ESPNcricinfo Feed 11",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/11.xml"},
    {"name": "ESPNcricinfo Feed 15",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/15.xml"},
    {"name": "ESPNcricinfo Feed 17",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/17.xml"},
    {"name": "ESPNcricinfo Feed 19",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/19.xml"},
    {"name": "ESPNcricinfo Feed 20",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/20.xml"},
    {"name": "ESPNcricinfo Feed 25",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/25.xml"},
    {"name": "ESPNcricinfo Feed 27",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/27.xml"},
    {"name": "ESPNcricinfo Feed 28",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/28.xml"},
    {"name": "ESPNcricinfo Feed 29",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/29.xml"},
    {"name": "ESPNcricinfo Feed 30",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/30.xml"},
    {"name": "ESPNcricinfo Feed 33",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/33.xml"},
    {"name": "ESPNcricinfo Feed 35",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/35.xml"},
    {"name": "ESPNcricinfo Feed 37",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/37.xml"},
    {"name": "ESPNcricinfo Feed 40",        "url": "https://www.espncricinfo.com/rss/content/story/feeds/40.xml"},

    # ── League & Domestic Topics (Google News mirrors) ────────────────────
    {"name": "Google News: SA20 Betway",    "url": "https://news.google.com/rss/search?q=SA20+OR+Betway+SA20&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: CSA Provincial 4-Day", "url": "https://news.google.com/rss/search?q=CSA+OR+provincial+OR+4-Day+Series+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: CSA T20 Challenge", "url": "https://news.google.com/rss/search?q=CSA+T20+Challenge&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: The Hundred Exact", "url": "https://news.google.com/rss/search?q=%22The+Hundred%22+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: County Championship", "url": "https://news.google.com/rss/search?q=County+Championship+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Vitality Blast", "url": "https://news.google.com/rss/search?q=Vitality+Blast+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Big Bash League", "url": "https://news.google.com/rss/search?q=Big+Bash+League+cricket&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "Google News: WBBL",           "url": "https://news.google.com/rss/search?q=WBBL+OR+Women%27s+Big+Bash&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "Google News: Caribbean Premier League", "url": "https://news.google.com/rss/search?q=Caribbean+Premier+League&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News: PSL",            "url": "https://news.google.com/rss/search?q=PSL+OR+Pakistan+Super+League&hl=en-PK&gl=PK&ceid=PK:en"},
    {"name": "Google News: ILT20",          "url": "https://news.google.com/rss/search?q=ILT20+OR+International+League+T20&hl=en-AE&gl=AE&ceid=AE:en"},
    {"name": "Google News: Major League Cricket", "url": "https://news.google.com/rss/search?q=Major+League+Cricket&hl=en-US&gl=US&ceid=US:en"},
    {"name": "Google News: Duleep Trophy Domestic", "url": "https://news.google.com/rss/search?q=Duleep+Trophy+OR+Syed+Mushtaq+Ali+OR+state+T20&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: IPL League Wide", "url": "https://news.google.com/rss/search?q=Indian+Premier+League+OR+IPL&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: WPL League",     "url": "https://news.google.com/rss/search?q=WPL+OR+Women%27s+Premier+League&hl=en-IN&gl=IN&ceid=IN:en"},

    # ── Country Topics (Google News mirrors) ──────────────────────────────
    {"name": "Google News: New Zealand Cricket", "url": "https://news.google.com/rss/search?q=New+Zealand+cricket&hl=en-NZ&gl=NZ&ceid=NZ:en"},
    {"name": "Google News: Pakistan Cricket", "url": "https://news.google.com/rss/search?q=Pakistan+cricket&hl=en-PK&gl=PK&ceid=PK:en"},
    {"name": "Google News: Bangladesh Cricket", "url": "https://news.google.com/rss/search?q=Bangladesh+cricket&hl=en-BD&gl=BD&ceid=BD:en"},
    {"name": "Google News: Zimbabwe Cricket", "url": "https://news.google.com/rss/search?q=Zimbabwe+cricket&hl=en-ZW&gl=ZW&ceid=ZW:en"},
    {"name": "Google News: Ireland Cricket", "url": "https://news.google.com/rss/search?q=Ireland+cricket&hl=en-IE&gl=IE&ceid=IE:en"},
    {"name": "Google News: Scotland Cricket", "url": "https://news.google.com/rss/search?q=Scotland+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Netherlands Cricket", "url": "https://news.google.com/rss/search?q=Netherlands+cricket&hl=en-NL&gl=NL&ceid=NL:en"},
    {"name": "Google News: Nepal Cricket",  "url": "https://news.google.com/rss/search?q=Nepal+cricket&hl=en-NP&gl=NP&ceid=NP:en"},
    {"name": "Google News: UAE Cricket",    "url": "https://news.google.com/rss/search?q=UAE+cricket&hl=en-AE&gl=AE&ceid=AE:en"},
    {"name": "Google News: Afghanistan Cricket", "url": "https://news.google.com/rss/search?q=Afghanistan+cricket&hl=en-AF&gl=AF&ceid=AF:en"},

    # ── Franchise Exact-Phrase Mirrors ────────────────────────────────────
    {"name": "Google News: SRH Exact",      "url": "https://news.google.com/rss/search?q=%22Sunrisers+Hyderabad%22+OR+%22SRH%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: SEC Exact",      "url": "https://news.google.com/rss/search?q=%22Sunrisers+Eastern+Cape%22&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Leeds Men Superchargers", "url": "https://news.google.com/rss/search?q=%22Sunrisers+Leeds%22+OR+%22Northern+Superchargers%22+men&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Leeds Women Superchargers", "url": "https://news.google.com/rss/search?q=%22Sunrisers+Leeds%22+OR+%22Northern+Superchargers%22+women&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── Site-Restricted Mirrors (no public RSS on these domains) ──────────
    {"name": "Google News: ICC Official",  "url": "https://news.google.com/rss/search?q=site:icc-cricket.com&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Yorkshire CCC Site", "url": "https://news.google.com/rss/search?q=site:yorkshireccc.com&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: ESPNcricinfo Site", "url": "https://news.google.com/rss/search?q=site:espncricinfo.com&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Cricbuzz Site",  "url": "https://news.google.com/rss/search?q=site:cricbuzz.com&hl=en-IN&gl=IN&ceid=IN:en"},

    # ── Player & Coach Topics (filtered by roster matcher downstream) ─────
    {"name": "Google News: Abhishek Sharma", "url": "https://news.google.com/rss/search?q=Abhishek+Sharma+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Pat Cummins",    "url": "https://news.google.com/rss/search?q=Pat+Cummins+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Heinrich Klaasen", "url": "https://news.google.com/rss/search?q=Heinrich+Klaasen&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Aiden Markram",  "url": "https://news.google.com/rss/search?q=Aiden+Markram&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Marco Jansen",   "url": "https://news.google.com/rss/search?q=Marco+Jansen+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Harry Brook",    "url": "https://news.google.com/rss/search?q=Harry+Brook+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Tristan Stubbs", "url": "https://news.google.com/rss/search?q=Tristan+Stubbs+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Ishan Kishan",   "url": "https://news.google.com/rss/search?q=Ishan+Kishan+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Deepti Sharma",  "url": "https://news.google.com/rss/search?q=Deepti+Sharma+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Phoebe Litchfield", "url": "https://news.google.com/rss/search?q=Phoebe+Litchfield&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Coaches Vettori Birrell Bond", "url": "https://news.google.com/rss/search?q=%22Daniel+Vettori%22+OR+%22Adrian+Birrell%22+OR+%22Shane+Bond%22+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Leeds Women Stars", "url": "https://news.google.com/rss/search?q=%22Deepti+Sharma%22+OR+%22Phoebe+Litchfield%22+OR+%22Annabel+Sutherland%22+OR+%22Kate+Cross%22&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── Ownership, Business & Leadership ─────────────────────────────────
    {"name": "Google News: Sun TV Network Exact", "url": "https://news.google.com/rss/search?q=%22Sun+TV+Network%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Kavya Maran Exact", "url": "https://news.google.com/rss/search?q=Kavya+Maran&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Sun Group Cricket", "url": "https://news.google.com/rss/search?q=%22Sun+Group%22+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Sunrisers Valuation", "url": "https://news.google.com/rss/search?q=Sunrisers+valuation+OR+demerger+OR+acquisition&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: IPL Valuation",  "url": "https://news.google.com/rss/search?q=IPL+franchise+valuation+OR+revenue+OR+stake&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Yorkshire Investment", "url": "https://news.google.com/rss/search?q=Yorkshire+cricket+OR+Headingley+investment+OR+stake&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── Women's Game Expansion ────────────────────────────────────────────
    {"name": "Google News: Womens Cricket Global", "url": "https://news.google.com/rss/search?q=women%27s+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: England Women",  "url": "https://news.google.com/rss/search?q=England+women+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: India Women Cricket", "url": "https://news.google.com/rss/search?q=women+cricket+India&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: WPL Auction",    "url": "https://news.google.com/rss/search?q=WPL+auction+OR+retention&hl=en-IN&gl=IN&ceid=IN:en"},

    # ── Community (honest post dates; aggregator mirrors removed — Bing
    # re-surfaces evergreen pages with fresh timestamps, defeating the 24h cutoff)
    {"name": "Reddit r/Cricket",            "url": "https://www.reddit.com/r/Cricket/.rss"},

    # ── UK & SA Direct Feeds ─────────────────────────────────────────────
    {"name": "BBC Sport The Hundred",       "url": "https://feeds.bbci.co.uk/sport/cricket/the-hundred/rss.xml"},
    {"name": "Sky Sports Feed 12040",       "url": "https://www.skysports.com/rss/12040"},
    {"name": "Yorkshire Post Sport",        "url": "https://www.yorkshirepost.co.uk/rss"},
    {"name": "The Citizen SA",              "url": "https://www.citizen.co.za/feed/"},
    {"name": "CricToday",                   "url": "https://crictoday.com/feed"},

    # ── Business Direct Feeds ─────────────────────────────────────────────
    {"name": "LiveMint Markets",            "url": "https://www.livemint.com/rss/markets"},
    {"name": "Hindu BusinessLine Markets",  "url": "https://www.thehindubusinessline.com/markets/feeder/default.rss"},
    {"name": "Economic Times Top Stories",  "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"},
    {"name": "Business Today",              "url": "https://www.businesstoday.in/rss/home"},

    # ── Telugu Regional Depth ─────────────────────────────────────────────
    {"name": "Telangana Today General",     "url": "https://telanganatoday.com/feed"},
    {"name": "Vaartha Telugu",              "url": "https://www.vaartha.com/feed/"},
    {"name": "Hans India Sports",           "url": "https://www.thehansindia.com/rss/sports"},
    {"name": "GreatAndhra Telugu",          "url": "https://www.greatandhra.com/feed"},

    # ── Overseas Depth (non-India coverage: SA/AUS/NZ/SL/BD/PK/SCO/UK) ──
    {"name": "SA Daily Maverick",           "url": "https://www.dailymaverick.co.za/rss"},
    {"name": "SA IOL News",                 "url": "https://www.iol.co.za/rss"},
    {"name": "Google News: News24 SA",      "url": "https://news.google.com/rss/search?q=site:news24.com+cricket+Proteas+or+SA20&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: SuperSport SA",  "url": "https://news.google.com/rss/search?q=site:supersport.com+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Cricket Australia", "url": "https://news.google.com/rss/search?q=site:cricket.com.au+Australia&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "Google News: Fox Sports Aus", "url": "https://news.google.com/rss/search?q=site:foxsports.com.au+cricket+Australia&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "NZ Stuff Sport",              "url": "https://www.stuff.co.nz/rss/sport"},
    {"name": "Google News: NZ Herald",      "url": "https://news.google.com/rss/search?q=site:nzherald.co.nz+Black+Caps+cricket&hl=en-NZ&gl=NZ&ceid=NZ:en"},
    {"name": "SL ThePapare",                "url": "https://www.thepapare.com/feed"},
    {"name": "SL AdaDerana News",           "url": "https://www.adaderana.lk/rss.php"},
    {"name": "PK Dawn Sport",               "url": "https://www.dawn.com/feeds/sport"},
    {"name": "Google News: Daily Star BD",  "url": "https://news.google.com/rss/search?q=site:thedailystar.net+sports+cricket+Bangladesh&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Scotsman Sport", "url": "https://news.google.com/rss/search?q=site:scotsman.com+cricket+Scotland&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: The Cricketer",  "url": "https://news.google.com/rss/search?q=site:thecricketer.com+county+or+Hundred&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── National Teams & Overseas Press (players on country duty) ──
    {"name": "SA SABC Sport",               "url": "https://www.sabcsport.com/rss"},
    {"name": "PK Tribune Sport",             "url": "https://tribune.com.pk/feed/sports"},
    {"name": "Google News: England Men",    "url": "https://news.google.com/rss/search?q=England+cricket+team+Tests+Ashes&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Australia Men",  "url": "https://news.google.com/rss/search?q=Australia+cricket+team+Baggy+Greens&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "Google News: Proteas",        "url": "https://news.google.com/rss/search?q=Proteas+South+Africa+cricket+team&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Black Caps",     "url": "https://news.google.com/rss/search?q=Black+Caps+New+Zealand+cricket+team&hl=en-NZ&gl=NZ&ceid=NZ:en"},
    {"name": "Google News: Pakistan Team",  "url": "https://news.google.com/rss/search?q=Pakistan+cricket+team+Shaheens&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Bangladesh Team", "url": "https://news.google.com/rss/search?q=Bangladesh+Tigers+cricket+team&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Sri Lanka Team", "url": "https://news.google.com/rss/search?q=Sri+Lanka+cricket+team+Lions&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Scotland Team",  "url": "https://news.google.com/rss/search?q=Scotland+cricket+team+Saltires&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Dhaka Tribune",  "url": "https://news.google.com/rss/search?q=site:dhakatribune.com+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Daily Mirror LK", "url": "https://news.google.com/rss/search?q=site:dailymirror.lk+cricket&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── SA Depth + Women's Weight (Proteas Women, domestic, women's game) ──
    {"name": "SA HeraldLive",               "url": "https://www.heraldlive.co.za/rss"},
    {"name": "Google News: Proteas Women",  "url": "https://news.google.com/rss/search?q=Proteas+Women+South+Africa+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: SA Domestic",    "url": "https://news.google.com/rss/search?q=Warriors+Titans+Lions+Dolphins+CSA+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: ICC Women",      "url": "https://news.google.com/rss/search?q=site:icc-cricket.com+women+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: England Women Domestic", "url": "https://news.google.com/rss/search?q=Charlotte+Edwards+Cup+or+Rachael+Heyhoe+Flint&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: WBBL Ashes Women", "url": "https://news.google.com/rss/search?q=Women+Ashes+or+WBBL+final+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: India Women Stars", "url": "https://news.google.com/rss/search?q=India+Women+cricket+Mandhana+or+Shafali+or+Deepti&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Hundred Women Clubs", "url": "https://news.google.com/rss/search?q=%22The+Hundred%22+women+Phoenix+or+Invincibles+or+Spirit&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: WPL Stars",      "url": "https://news.google.com/rss/search?q=womens+cricket+Smriti+or+Perry+or+Wolvaardt&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── Ownership Filings & Leadership (exchange disclosures surface here first)
    {"name": "Google News: BSE Filings Sun TV", "url": "https://news.google.com/rss/search?q=site:bseindia.com+Sun+TV+Network&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Moneycontrol Sun TV", "url": "https://news.google.com/rss/search?q=site:moneycontrol.com+Sun+TV+Network+Sunrisers&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Kavya Maran Statements", "url": "https://news.google.com/rss/search?q=%22Kavya+Maran%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Sun Group Filings", "url": "https://news.google.com/rss/search?q=%22Sun+Group%22+Kalanithi+Maran+filing+or+stake+or+acquisition&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Leeds Companies House", "url": "https://news.google.com/rss/search?q=Sunrisers+Leeds+Companies+House+or+filing&hl=en-GB&gl=GB&ceid=GB:en"},

    # ══ Deep-Scan Additions — Oct 2026 (75 lanes, world-coverage round 2) ══
    # Every URL below was identity-verified live on 17 Oct 2026. A few lanes
    # refuse scripted polling (Reddit 429; Firstpost / Zee direct 403; Telegraph
    # UK 402) — they stay listed intentionally and fail gracefully; the
    # resilient fallback in _poll_one_source recovers what it can.

    # ── Community & direct feeds ──────────────────────────────────────────
    {"name": "Reddit r/SunrisersHyderabad",  "url": "https://www.reddit.com/r/SunrisersHyderabad/.rss"},
    {"name": "Reddit r/ipl",                 "url": "https://www.reddit.com/r/ipl/.rss"},
    {"name": "Reddit r/CricketAus",          "url": "https://www.reddit.com/r/CricketAus/.rss"},
    {"name": "The Age Sport",                "url": "https://www.theage.com.au/rss/sport.xml"},
    {"name": "ESPNcricinfo All Stories",     "url": "https://www.espncricinfo.com/rss/content/story/feeds/0.xml"},
    {"name": "Firstpost Cricket",            "url": "https://www.firstpost.com/rss/cricket.xml"},
    {"name": "Zee News Sports (direct)",     "url": "https://zeenews.india.com/rss/sports-news.xml"},
    {"name": "The Telegraph Sport (UK)",     "url": "https://www.telegraph.co.uk/rss.xml"},

    # ── League market mirrors (IPL window, trades, releases) ─────────────
    {"name": "Google News: IPL Retention Deadline / Mini Auction", "url": "https://news.google.com/rss/search?q=IPL+retention+deadline+OR+%22mini+auction%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: IPL Trade Window", "url": "https://news.google.com/rss/search?q=IPL+%22trade+window%22+OR+traded&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Impact Player Rule", "url": "https://news.google.com/rss/search?q=IPL+%22Impact+Player%22+rule&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Liam Livingstone", "url": "https://news.google.com/rss/search?q=%22Liam+Livingstone%22+IPL&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Harshal Patel",   "url": "https://news.google.com/rss/search?q=%22Harshal+Patel%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: T Natarajan",     "url": "https://news.google.com/rss/search?q=%22Natarajan%22+IPL+OR+SRH&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: SRH Factory Kids (Hinge/Sakib/Arora)", "url": "https://news.google.com/rss/search?q=%22Praful+Hinge%22+OR+%22Sakib+Hussain%22+OR+%22Salil+Arora%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Eshan Malinga",   "url": "https://news.google.com/rss/search?q=%22Eshan+Malinga%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: SRH Release List", "url": "https://news.google.com/rss/search?q=SRH+released+OR+releases+OR+%22released+players%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Cricket Australia Workload / IPL Availability", "url": "https://news.google.com/rss/search?q=%22Cricket+Australia%22+workload+IPL&hl=en-IN&gl=IN&ceid=IN:en"},

    # ── Insider bylines (journalists who break Sunrisers news first) ─────
    {"name": "Google News: Daniel Brettig (The Age/SMH)", "url": "https://news.google.com/rss/search?q=%22Daniel+Brettig%22+cricket&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "Google News: Peter Lalor (The Australian)", "url": "https://news.google.com/rss/search?q=%22Peter+Lalor%22+cricket&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "Google News: Andrew McGlashan (ESPNcricinfo)", "url": "https://news.google.com/rss/search?q=%22Andrew+McGlashan%22+cricket&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Nagraj Gollapudi (ESPNcricinfo/IPL)", "url": "https://news.google.com/rss/search?q=%22Nagraj+Gollapudi%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Sidharth Monga (ESPNcricinfo)", "url": "https://news.google.com/rss/search?q=%22Sidharth+Monga%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Shashank Kishore (ESPNcricinfo)", "url": "https://news.google.com/rss/search?q=%22Shashank+Kishore%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Bharat Sundaresan (Cricbuzz)", "url": "https://news.google.com/rss/search?q=%22Bharat+Sundaresan%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Sahil Malhotra (TOI/IPL)", "url": "https://news.google.com/rss/search?q=%22Sahil+Malhotra%22+IPL&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: K Shriniwas Rao (TOI/IPL)", "url": "https://news.google.com/rss/search?q=%22Shriniwas+Rao%22+IPL&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Vijay Lokapally (The Hindu)", "url": "https://news.google.com/rss/search?q=%22Vijay+Lokapally%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Amol Karhadkar (ESPNcricinfo)", "url": "https://news.google.com/rss/search?q=%22Amol+Karhadkar%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Deivarayan Muthu (ESPNcricinfo)", "url": "https://news.google.com/rss/search?q=%22Deivarayan+Muthu%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Abhishek Purohit (ESPNcricinfo)", "url": "https://news.google.com/rss/search?q=%22Abhishek+Purohit%22+cricket&hl=en-IN&gl=IN&ceid=IN:en"},

    # ── Full-squad player feeds (filtered by roster matcher downstream) ──
    {"name": "Google News: Travis Head",     "url": "https://news.google.com/rss/search?q=%22Travis+Head%22+cricket&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "Google News: Nitish Kumar Reddy", "url": "https://news.google.com/rss/search?q=%22Nitish+Kumar+Reddy%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Jaydev Unadkat",  "url": "https://news.google.com/rss/search?q=%22Jaydev+Unadkat%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Kamindu Mendis",  "url": "https://news.google.com/rss/search?q=%22Kamindu+Mendis%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Brydon Carse",    "url": "https://news.google.com/rss/search?q=%22Brydon+Carse%22&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Jack Edwards",    "url": "https://news.google.com/rss/search?q=%22Jack+Edwards%22+cricket&hl=en-AU&gl=AU&ceid=AU:en"},
    {"name": "Google News: Ravichandran Smaran", "url": "https://news.google.com/rss/search?q=%22Smaran+Ravichandran%22+OR+%22Ravichandran+Smaran%22&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Aniket Verma",    "url": "https://news.google.com/rss/search?q=%22Aniket+Verma%22+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Shivang Kumar",   "url": "https://news.google.com/rss/search?q=%22Shivang+Kumar%22+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Harsh Dubey",     "url": "https://news.google.com/rss/search?q=%22Harsh+Dubey%22+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Ottniel Baartman (SEC)", "url": "https://news.google.com/rss/search?q=%22Ottniel+Baartman%22&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Jordan Hermann (SEC)", "url": "https://news.google.com/rss/search?q=%22Jordan+Hermann%22+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Adil Rashid (Leeds lane)", "url": "https://news.google.com/rss/search?q=%22Adil+Rashid%22&hl=en-GB&gl=GB&ceid=GB:en"},
    {"name": "Google News: Yuvraj Singh (mentor lane)", "url": "https://news.google.com/rss/search?q=%22Yuvraj+Singh%22+mentor+OR+coach&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Gautam Gambhir (India coach lane)", "url": "https://news.google.com/rss/search?q=%22Gautam+Gambhir%22+IPL+OR+rest+OR+coach&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Kalanithi Maran (owner lane)", "url": "https://news.google.com/rss/search?q=%22Kalanithi+Maran%22&hl=en-IN&gl=IN&ceid=IN:en"},

    # ── League mechanics & market ─────────────────────────────────────────
    {"name": "Google News: BCCI Governing Council / IPL Decisions", "url": "https://news.google.com/rss/search?q=BCCI+%22governing+council%22+IPL&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: IPL Auction Goa Logistics", "url": "https://news.google.com/rss/search?q=IPL+auction+Goa+December&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Hardik Pandya Trade", "url": "https://news.google.com/rss/search?q=%22Hardik+Pandya%22+trade+IPL&hl=en-IN&gl=IN&ceid=IN:en"},

    # ── Wires & agencies ──────────────────────────────────────────────────
    {"name": "Google News: ANI Cricket",     "url": "https://news.google.com/rss/search?q=site:aninews.in+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: IANS Cricket",    "url": "https://news.google.com/rss/search?q=site:ianslive.in+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: PTI Cricket",     "url": "https://news.google.com/rss/search?q=site:ptinews.com+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: UNI Cricket",     "url": "https://news.google.com/rss/search?q=site:uniindia.com+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "Google News: Rediff Cricket",  "url": "https://news.google.com/rss/search?q=site:rediff.com+cricket&hl=en-IN&gl=IN&ceid=IN:en"},
    {"name": "The Bridge",                   "url": "https://thebridge.in/feed"},

    # ── Telugu & regional depth ───────────────────────────────────────────
    {"name": "Google News: Eenadu Cricket",  "url": "https://news.google.com/rss/search?q=site:eenadu.net+%E0%B0%95%E0%B1%8D%E0%B0%B0%E0%B0%BF%E0%B0%95%E0%B1%86%E0%B0%9F%E0%B1%8D&hl=te&gl=IN&ceid=IN:te"},
    {"name": "Google News: TV9 Telugu Cricket", "url": "https://news.google.com/rss/search?q=site:tv9telugu.com+cricket+OR+SRH&hl=te&gl=IN&ceid=IN:te"},
    {"name": "Google News: Telugu Oneindia Cricket", "url": "https://news.google.com/rss/search?q=site:telugu.oneindia.com+cricket&hl=te&gl=IN&ceid=IN:te"},
    {"name": "Google News: Andhra Jyothy Cricket", "url": "https://news.google.com/rss/search?q=site:andhrajyothy.com+cricket&hl=te&gl=IN&ceid=IN:te"},

    # ── Overseas plus ─────────────────────────────────────────────────────
    {"name": "Google News: Sport24 SA Cricket", "url": "https://news.google.com/rss/search?q=site:sport24.co.za+cricket&hl=en-ZA&gl=ZA&ceid=ZA:en"},
    {"name": "Google News: Yorkshire Evening Post Cricket", "url": "https://news.google.com/rss/search?q=site:yorkshireeveningpost.co.uk+cricket&hl=en-GB&gl=GB&ceid=GB:en"},

    # ── YouTube official channels (identity-verified channel IDs) ─────────
    # SRH and SA20 use the channels linked from the clubs' own websites
    # (sunrisershyderabad.in → @SunrisersIPL; sa20.co.za → the SA20 channel).
    {"name": "YouTube: Sunrisers Hyderabad", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCScgEv0U9Wcnk24KfAzGTXg"},
    {"name": "YouTube: IPL",                 "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC0oyi_CF3v9fsKmBM2m6wPA"},
    {"name": "YouTube: Cricbuzz",            "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCSRQXk5yErn4e14vN76upOw"},
    {"name": "YouTube: Sky Sports Cricket",  "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCkd4takjjF1EGD1TKIK2QiA"},
    {"name": "YouTube: The Hundred",         "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCPDAFa3eTpUhugfKPuvxPww"},
    {"name": "YouTube: Star Sports India",   "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC2iihojySb58j_Q4zL7VI5w"},
    {"name": "YouTube: Betway SA20",         "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCjDO4cIaxrazb74tA4r2C9g"},
    {"name": "YouTube: Fox Cricket",         "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCOkT6dccQ1vsnMFK1xJanmA"},
    {"name": "YouTube: BBC Sport",           "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCW6-BQWFA70Dyyc7ZpZ9Xlg"},
    {"name": "YouTube: cricket.com.au",      "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCkBY0aHJP9BwjZLDYxAQrKg"},
    {"name": "YouTube: Wisden Cricket",      "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCms-xnI50pEtJC06xdw4J6A"},
    {"name": "YouTube: ICC",                 "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCt2JXOLNxqry7B_4rRZME3Q"},
    {"name": "YouTube: Ashwin Ravi",         "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCYKlz4OFBA-ZInrNWB91BWg"},
]

def clean_up_story_text(raw):
    """Strip HTML tags and unescape double-encoded feed text."""
    if not raw:
        return ""
    first = bs4.BeautifulSoup(raw, "html.parser").get_text()
    first = html.unescape(first)
    second = bs4.BeautifulSoup(first, "html.parser").get_text()
    return " ".join(second.split()).strip()


def _download_feed(url, retries=FETCH_RETRIES, timeout=FETCH_TIMEOUT_SECS):
    """Return (parsed_feed_or_None, short_reason). Never raises."""
    safe_url = canonicalize_url(url)
    if not safe_url:
        return None, "unsafe feed URL"
    last_reason = "unknown error"
    for attempt in range(max(1, int(retries))):
        try:
            response = requests.get(
                safe_url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if feed and feed.entries:
                    return feed, ""
                last_reason = "HTTP 200 but 0 entries"
            else:
                last_reason = f"HTTP {response.status_code}"
                if 400 <= response.status_code < 500:
                    break
        except Exception as exc:
            last_reason = type(exc).__name__
        if attempt + 1 < retries:
            time.sleep(min(4, 2 ** attempt))
    return None, last_reason


def try_to_download_one_website(url, retries=FETCH_RETRIES, delay=1, timeout=FETCH_TIMEOUT_SECS):
    """Fetch and parse one RSS feed; retry only transient failures."""
    feed, reason = _download_feed(url, retries=retries, timeout=timeout)
    if feed is None:
        problems_diary.warning(f"Feed unavailable '{url}': {reason}.")
    return feed


def _poll_one_source(feed_info):
    """Network-only worker. One bad source never aborts the sweep."""
    try:
        feed, reason = _download_feed(feed_info["url"])
        if feed and feed.entries:
            return feed_info, feed.entries, None
        return feed_info, [], reason or "no entries"
    except Exception as exc:
        return feed_info, [], f"poll crashed: {type(exc).__name__}"


def _summarise_matches(matches):
    people = sorted({
        match["player_name"] for match in matches
        if match.get("kind") in ("player", "person")
    })
    franchises = sorted({match["franchise"] for match in matches if match.get("franchise")})
    topics = sorted({
        match["player_name"] for match in matches if match.get("kind") == "topic"
    })
    return people, franchises, topics


def collect_fresh_stories(feeds=None, max_workers=MAX_WORKERS):
    """Poll due feeds, keep relevant fresh stories, and queue alert deliveries."""
    feed_list = list(feeds if feeds is not None else NEWS_WEBSITES)
    result = CollectionResult(total_feeds=len(feed_list))
    due_feeds = []
    for feed_info in feed_list:
        if feed_is_due(feed_info["url"]):
            due_feeds.append(feed_info)
    result.polled_feeds = len(due_feeds)
    result.skipped_feeds = len(feed_list) - len(due_feeds)
    news_diary.info(
        f"Starting sweep: {len(due_feeds)} due feeds, {result.skipped_feeds} backing off."
    )
    if not due_feeds:
        return result

    polled = []
    workers = max(1, min(int(max_workers), len(due_feeds)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for item in pool.map(_poll_one_source, due_feeds):
            polled.append(item)

    for feed_info, entries, fetch_error in polled:
        if not entries:
            result.failed_feeds.append(feed_info["name"])
            record_feed_failure(feed_info["url"], feed_info["name"], fetch_error)
            problems_diary.warning(
                f"Feed '{feed_info['name']}' unavailable: {fetch_error}."
            )
            continue
        record_feed_success(feed_info["url"])
        for entry in entries:
            title = clean_up_story_text(entry.get("title", ""))
            summary = clean_up_story_text(
                entry.get("summary", "") or entry.get("description", "")
            )
            link = canonicalize_url(entry.get("link", ""))
            published_at, age_hours, published_ts = read_story_date_as_indian_time(entry)
            if not title or not link:
                result.invalid_links += 1
                continue
            if age_hours is not None and age_hours > MAX_ARTICLE_AGE_HOURS:
                result.stale += 1
                continue
            matches = find_our_players_in_story(f"{title} {summary}")
            if not matches:
                continue
            result.matched += 1
            people, franchises, topics = _summarise_matches(matches)
            article_id = save_article(
                title=title,
                source=feed_info["name"],
                summary=summary,
                link=link,
                published_at=published_at,
                published_ts=published_ts,
                people=people,
                franchises=franchises,
                topics=topics,
            )
            if article_id:
                result.inserted += 1
                result.new_articles.append(
                    {
                        "id": article_id,
                        "title": title,
                        "source": feed_info["name"],
                        "link": link,
                        "published_at": published_at,
                        "published_ts": published_ts,
                        "people": people,
                        "franchises": franchises,
                        "topics": topics,
                    }
                )
            else:
                result.duplicates += 1

    news_diary.info(
        f"Sweep complete: {result.inserted} new, {result.matched} matched, "
        f"{result.duplicates} duplicate, {result.stale} stale, "
        f"{result.invalid_links} invalid links, "
        f"{len(result.failed_feeds)}/{result.polled_feeds} feeds failed."
    )
    return result


# Old names used by earlier guides and scripts.
fetch_and_filter_rss = collect_fresh_stories
fetch_feed_with_retry = try_to_download_one_website
clean_text = clean_up_story_text
TOP_50_CRICKET_SOURCES = NEWS_WEBSITES
RSS_FEEDS = NEWS_WEBSITES
CRICKET_SOURCES = NEWS_WEBSITES
