"""
Expanded RSS Feed Collector for @SRHXtra V10.0 — Hyper-Local Expansion.
Polls the configured Top-Tier Global & Hyper-Local outlets for all rostered squad members & 4 Franchise Team Names.
Stores EXACT raw source titles and descriptions for direct ESPNcricinfo-style cards.
Scoring removed: articles are stored with database defaults (importance_score=5.0,
category='General News'); no per-article scoring or categorization is performed.
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
CRICKET_SOURCES = [
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
def fetch_feed_with_retry(url, retries=2, delay=1, timeout=6):
    """Fetches RSS feed with exponential backoff and browser-grade User-Agent."""
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    ]
    for attempt in range(1, retries + 1):
        try:
            ua = user_agents[(attempt - 1) % len(user_agents)]
            response = requests.get(url, headers={"User-Agent": ua}, timeout=timeout)
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                if feed and feed.entries:
                    return feed
        except Exception:
            pass
        time.sleep(delay * attempt)
    return None
def fetch_and_filter_rss():
    """
    Polls all sources in CRICKET_SOURCES, filters for rostered players OR 4 franchise team names.
    STRICTLY DISCARDS any article older than 24 hours.
    Stores EXACT raw headline and description from sources.
    Articles are stored with database defaults (no per-article scoring).
    Returns:
        _RssResult — int subclass with .inserted, .failed_feeds, .total_polled
    """
    total_inserted = 0
    failed_feeds   = []
    rss_logger.info(
        f"Starting 24-Hour Ingestion Cycle across {len(CRICKET_SOURCES)} sources..."
    )
    from scrapers.web_scraper import scrape_google_news_topic

    for feed_info in CRICKET_SOURCES:
        feed = fetch_feed_with_retry(feed_info["url"])
        entries = feed.entries if feed and feed.entries else []
        if not entries:
            # Resilient fallback: attempt search mirror when primary RSS endpoint fails
            source_name = feed_info["name"]
            fallback_entries = scrape_google_news_topic(f"{source_name} cricket")
            if fallback_entries:
                entries = fallback_entries
                rss_logger.info(
                    f"Recovered {len(entries)} articles for '{source_name}' via resilient fallback."
                )
            else:
                failed_feeds.append(source_name)
                error_logger.warning(
                    f"Feed '{feed_info['url']}' unavailable and fallback yielded 0 items."
                )
                continue
        for entry in entries:
            title   = clean_text(entry.get("title", ""))
            summary = clean_text(entry.get("summary", "") or entry.get("description", ""))
            link    = entry.get("link", "")
            pub_date, age_hours, pub_ts = parse_rss_date_to_ist(entry)
            if age_hours > 24.0:
                continue
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
                        message=(
                            f"⚡ {mt['player_name']} ({mt['franchise']})"
                        ),
                        type_str="INFO",
                    )
                    rss_logger.info(
                        f"  ↳ {mt['player_name']} — {title[:60]}"
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
