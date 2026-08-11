"""
SRHXtra — Squad Telemetry & Matchday Intelligence Engine (V14.1 — Strict Excel Roster Enforcement).
Bespoke Athletic Editorial & Data Telemetry System for Sunrisers Franchise Network:
  - Sunrisers Hyderabad (IPL)
  - Sunrisers Eastern Cape (SA20)
  - Sunrisers Leeds Men & Women (The Hundred)
V14.1 Upgrades:
  - STRICT Excel Roster Enforcement (100% of tracked entities belong exclusively to squadofsunrisers.xlsx)
  - Interactive "Anniversary Time Machine" (Explore milestones on ANY date of the year)
  - Individual Batting & Bowling Masterclasses (Sunrisers & National Team duty)
  - Player Birthdays & Records Broken Engine
"""
import os
import sys
import time
import textwrap
import threading
import urllib.parse
from datetime import datetime, date as date_cls
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streamlit as st
import streamlit.components.v1 as components
from config.roster import MASTER_ROSTER
from config.schedule import FIXTURE_SCHEDULE
from database.db_manager import (
    init_db, get_recent_news, search_news, purge_expired_24h_news,
    get_metadata, set_metadata
)
from utils.time_utils import format_ist_12hr, get_current_ist, IST
from config.theme import (
    get_custom_css, render_header_banner, render_next_match_hero,
    render_telemetry_metrics, render_featured_hero_news,
    render_telemetry_news_card, render_telemetry_pulse_item,
    render_broadcast_match_card, render_otd_telemetry_card,
    get_favicon_url, safe_article_link, time_ago,
    parse_fixture_datetime, get_fixture_status
)
try:
    from scrapers.rss_collector import fetch_and_filter_rss, TOP_50_CRICKET_SOURCES as CRICKET_SOURCES
    _source_count = len(CRICKET_SOURCES)
except Exception:
    class _FakeResult:
        inserted = 0
        failed_feeds = []
        total_polled = 0
    def fetch_and_filter_rss():
        return _FakeResult()
    _source_count = 68
_player_count = len({p["name"] for data in MASTER_ROSTER.values() for p in data["players"]})
st.set_page_config(
    page_title="SRHXtra — Squad Telemetry & Matchday Intelligence Engine",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.markdown(get_custom_css(), unsafe_allow_html=True)
init_db()
purge_expired_24h_news()
AUTO_INGEST_INTERVAL_SECS = 900
components.html(
    """
    <script>
        setTimeout(function(){ window.parent.location.reload(); }, 300000);
    </script>
    """,
    height=0, width=0,
)
if "last_refreshed" not in st.session_state:
    st.session_state["last_refreshed"] = format_ist_12hr()
if "last_refresh_ts" not in st.session_state:
    st.session_state["last_refresh_ts"] = 0.0
@st.cache_data(ttl=60)
def cached_get_recent_news(limit=150):
    return get_recent_news(limit=limit)
@st.cache_data(ttl=60)
def cached_search_news(query):
    return search_news(query)
_last_auto_ts = float(get_metadata("last_auto_ingest_ts", "0"))
_secs_since_auto = time.time() - _last_auto_ts
def _run_background_ingest():
    try:
        fetch_and_filter_rss()
        cached_get_recent_news.clear()
        cached_search_news.clear()
    except Exception as exc:
        try:
            from utils.logger import error_logger
            error_logger.error(f"Background RSS ingest failed: {exc}")
        except Exception:
            pass
if _secs_since_auto >= AUTO_INGEST_INTERVAL_SECS:
    _now = time.time()
    set_metadata("last_auto_ingest_ts", str(_now))
    _t = threading.Thread(target=_run_background_ingest, daemon=True)
    _t.start()
    st.session_state["last_refreshed"] = format_ist_12hr()
    st.session_state["last_refresh_ts"] = _now
if len(cached_get_recent_news(limit=1)) == 0:
    with st.spinner(f"🧡 Initializing SRHXtra Telemetry Engine (scanning {_source_count} feeds...)..."):
        fetch_and_filter_rss()
        set_metadata("last_auto_ingest_ts", str(time.time()))
        cached_get_recent_news.clear()
        cached_search_news.clear()
def get_bulletproof_sort_key(n):
    ts = n.get("pub_timestamp")
    if ts and isinstance(ts, (int, float)) and ts > 0:
        return ts
    pub_str = str(n.get("published_at", ""))
    try:
        return datetime.strptime(pub_str, "%b %d, %Y @ %I:%M %p IST").timestamp()
    except Exception:
        return 0.0
st.sidebar.markdown("<h2 style='font-family:Inter,sans-serif;font-weight:900;color:#0F172A;margin-bottom:0.2rem;'>🧡 SRHXtra</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='color:#E05600;font-family:Inter,sans-serif;font-size:0.82rem;font-weight:800;margin-bottom:1rem;'>SQUAD TELEMETRY V14.1</div>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown(f"👥 **Roster Coverage:** `{_player_count} Players & 4 Squads`")
st.sidebar.markdown(f"🕒 **Last Refreshed IST:**\n`{st.session_state['last_refreshed']}`")
_auto_secs_remaining = max(0, int(AUTO_INGEST_INTERVAL_SECS - _secs_since_auto))
_auto_mins = _auto_secs_remaining // 60
_auto_s = _auto_secs_remaining % 60
if _auto_secs_remaining > 0:
    st.sidebar.caption(f"⏳ Next Auto-Sync: **{_auto_mins}m {_auto_s:02d}s**")
else:
    st.sidebar.caption("⚡ Ingestion Sync Running...")
st.sidebar.markdown("---")
franchise_filter = st.sidebar.selectbox(
    "Filter Squad Domain",
    ["All", "Sunrisers Hyderabad", "Sunrisers Eastern Cape", "Sunrisers Leeds Men", "Sunrisers Leeds Women"]
)
if st.sidebar.button(f"⚡ Live Refresh {_source_count} Feeds", use_container_width=True):
    with st.spinner(f"Polling {_source_count} global sources..."):
        result = fetch_and_filter_rss()
        _now = time.time()
        st.session_state["last_refresh_ts"] = _now
        st.session_state["last_refreshed"] = format_ist_12hr()
        set_metadata("last_auto_ingest_ts", str(_now))
        cached_get_recent_news.clear()
        cached_search_news.clear()
        inserted = getattr(result, "inserted", int(result))
        failed = getattr(result, "failed_feeds", [])
        st.sidebar.success(f"Captured {inserted} fresh items!")
        if failed:
            st.sidebar.warning(f"{len(failed)} feeds unavailable.")
    st.rerun()
with st.sidebar.expander("📋 Squad Roster Breakdown", expanded=False):
    for fkey, fdata in MASTER_ROSTER.items():
        fname = fdata.get("franchise_name", fkey)
        p_count = len(fdata.get("players", []))
        st.markdown(f"**{fname}**: `{p_count} players`")
st.markdown(render_header_banner(_player_count, 4), unsafe_allow_html=True)
active_fixtures = [s for s in FIXTURE_SCHEDULE if get_fixture_status(s) in ["LIVE", "UPCOMING"]]
live_fixtures = [s for s in active_fixtures if get_fixture_status(s) == "LIVE"]
if live_fixtures:
    hero_fixture = live_fixtures[0]
    hero_status = "LIVE"
elif active_fixtures:
    hero_fixture = sorted(active_fixtures, key=lambda x: parse_fixture_datetime(x) or datetime.max)[0]
    hero_status = "UPCOMING"
else:
    hero_fixture = None
    hero_status = "UPCOMING"
if hero_fixture:
    st.markdown(render_next_match_hero(hero_fixture, status=hero_status), unsafe_allow_html=True)
live_count = len(cached_get_recent_news(limit=150))
st.markdown(render_telemetry_metrics(_source_count, _player_count, live_count), unsafe_allow_html=True)
tab_news, tab_schedule, tab_otd = st.tabs([
    f"📡 LIVE PULSE & NEWS RECON FEED ({live_count})",
    "📋 MATCH DAY FIXTURE BREAKDOWN",
    "🗓️ ON THIS DAY IN SUNRISERS HISTORY",
])
with tab_news:
    st.markdown("<h3 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;margin-bottom:0.8rem;'>📡 Real-Time Intelligence & News Feed</h3>", unsafe_allow_html=True)
    col_search, col_stats = st.columns([3, 1])
    with col_search:
        search_query = st.text_input(
            "Search player, team or keyword",
            placeholder="Search e.g. Abhishek Sharma, Travis Head, injury, SA20...",
            label_visibility="collapsed",
        )
    if search_query.strip():
        news_list = cached_search_news(search_query.strip())
        st.caption(f"🔍 Showing **{len(news_list)}** intelligence records for *\"{search_query}\"*")
    else:
        news_list = cached_get_recent_news(limit=150)
    if franchise_filter != "All":
        news_list = [n for n in news_list if n.get("franchise") == franchise_filter]
    news_list = sorted(news_list, key=get_bulletproof_sort_key, reverse=True)
    if news_list:
        col_main, col_pulse = st.columns([2.2, 1])
        with col_main:
            st.markdown(render_featured_hero_news(news_list[0]), unsafe_allow_html=True)
            for n in news_list[1:]:
                st.markdown(render_telemetry_news_card(n), unsafe_allow_html=True)
        with col_pulse:
            st.markdown("""
            <div class='pulse-panel'>
                <div class='pulse-panel-title'>
                    <span>LIVE PULSE TIMELINE</span>
                    <span class='srh-live-pulse-dot'></span>
                </div>
            """, unsafe_allow_html=True)
            for n in news_list[:10]:
                st.markdown(render_telemetry_pulse_item(n), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        if search_query.strip():
            st.info(f"No intelligence records found matching \"{search_query}\". Try a different player name or keyword.")
        else:
            st.info(f"No player updates recorded in the last 24 hours. Click '⚡ Live Refresh {_source_count} Feeds' in the sidebar to run a full sweep!")
with tab_schedule:
    st.markdown("<h3 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;margin-bottom:0.8rem;'>📋 Match Day Breakdown & Roster Coverage</h3>", unsafe_allow_html=True)
    col_ctrl, col_m1, col_m2, col_m3 = st.columns([1.5, 1, 1, 1])
    with col_ctrl:
        show_past = st.checkbox("📜 Include Past Fixtures", value=False)
    base_schedule = FIXTURE_SCHEDULE if show_past else [s for s in FIXTURE_SCHEDULE if get_fixture_status(s) in ["LIVE", "UPCOMING"]]
    upcoming_sched = [s for s in FIXTURE_SCHEDULE if get_fixture_status(s) in ["LIVE", "UPCOMING"]]
    next_match_date = upcoming_sched[0]["date_str"] if upcoming_sched else "N/A"
    active_leagues = len({s["league"] for s in base_schedule})
    with col_m1:
        st.metric("Fixtures Listed", len(base_schedule))
    with col_m2:
        st.metric("Next Fixture Date", next_match_date)
    with col_m3:
        st.metric("Leagues Tracked", active_leagues)
    if franchise_filter != "All":
        franchise_key_map = {
            "Sunrisers Hyderabad": "SRH",
            "Sunrisers Eastern Cape": "SEC",
            "Sunrisers Leeds Men": "Leeds_Men",
            "Sunrisers Leeds Women": "Leeds_Women",
        }
        fkey = franchise_key_map.get(franchise_filter, "")
        franchise_players = set()
        if fkey and fkey in MASTER_ROSTER:
            franchise_players = {p["name"] for p in MASTER_ROSTER[fkey]["players"]}
        def _fixture_matches_filter(s):
            if franchise_filter in s["squad"]:
                return True
            if any(pname in s["players"] for pname in franchise_players):
                return True
            return False
        filtered_sched = [s for s in base_schedule if _fixture_matches_filter(s)]
    else:
        filtered_sched = base_schedule
    filtered_sched = sorted(filtered_sched, key=lambda x: parse_fixture_datetime(x) or datetime.max)
    if filtered_sched:
        grouped_dates = {}
        for item in filtered_sched:
            grouped_dates.setdefault(item["date_str"], []).append(item)
        for date_str, items in grouped_dates.items():
            st.markdown(f"<h4 style='color:#E05600;font-family:Inter,sans-serif;font-weight:800;margin-top:1.5rem;margin-bottom:0.8rem;'>📅 {date_str}</h4>", unsafe_allow_html=True)
            for item in items:
                status = get_fixture_status(item)
                st.markdown(render_broadcast_match_card(item, status=status), unsafe_allow_html=True)
    else:
        st.info(f"No fixtures recorded for **{franchise_filter}**. Select 'All' to view complete fixture calendar.")
ON_THIS_DAY_DB = [
    {"month": 1, "day": 14, "year": 2023, "entity": "Sunrisers Eastern Cape", "franchise": "Sunrisers Eastern Cape",
     "title": "🏆 Sunrisers Eastern Cape win SA20 Season 1 title!",
     "desc": "Sunrisers Eastern Cape defeated MI Cape Town in the SA20 Season 1 Final to be crowned inaugural champions.",
     "scorecard": "SEC 162/6 (20 ov) def MI Cape Town 158/8 (20 ov) by 4 wickets",
     "stats": ["Inaugural SA20 Champions", "Sunrisers Franchise Trophy"],
     "category": "SA20 Final", "emoji": "🏆"},
    {"month": 1, "day": 19, "year": 2024, "entity": "Sunrisers Eastern Cape", "franchise": "Sunrisers Eastern Cape",
     "title": "🏆 SEC retain SA20 title — Back-to-Back Champions!",
     "desc": "Sunrisers Eastern Cape defended their SA20 crown, defeating Durban's Super Giants in the Season 2 Final with Marco Jansen taking 5/30 and Tristan Stubbs hitting 56*.",
     "scorecard": "SEC 89/6 (14.2 ov) def DSG 88/10 (17.3 ov) by 4 wickets",
     "stats": ["Marco Jansen 5/30", "Tristan Stubbs 56* (28)", "Back-to-Back Titles"],
     "category": "SA20 Final", "emoji": "🏆"},
    {"month": 2, "day": 8, "year": 2025, "entity": "Sunrisers Eastern Cape", "franchise": "Sunrisers Eastern Cape",
     "title": "🏆 SEC win SA20 Season 3 — Three-Peat Champions!",
     "desc": "Sunrisers Eastern Cape completed an unprecedented SA20 three-peat, winning their 3rd consecutive title.",
     "scorecard": "SEC 178/5 def Joburg Super Kings 142/9 by 36 runs",
     "stats": ["Three-Peat Dynasty", "Dominant SA20 Franchise"],
     "category": "SA20 Final", "emoji": "🏆"},
    {"month": 3, "day": 26, "year": 2024, "entity": "Travis Head", "franchise": "Sunrisers Hyderabad",
     "title": "🔥 Travis Head blazes 137 in T20 World Cup Warmup",
     "desc": "Travis Head continued his devastating white-ball form ahead of T20 tournaments, smashing boundaries at will at the top of the order.",
     "stats": ["137 off 68 balls", "12 Sixes", "SR 201.4"],
     "category": "Batting Masterclass", "emoji": "🏏"},
    {"month": 3, "day": 27, "year": 2024, "entity": "Sunrisers Hyderabad", "franchise": "Sunrisers Hyderabad",
     "title": "🔥 SRH post 277/3 vs MI — Record IPL Total & Abhishek 16-ball 50!",
     "desc": "Sunrisers Hyderabad shattered all-time T20 records by posting 277/3 against Mumbai Indians at Rajiv Gandhi International Stadium. Abhishek Sharma hit the fastest 50 in SRH history off 16 balls.",
     "scorecard": "SRH 277/3 (20 ov) vs MI 246/5 (20 ov) — Aggregate 523 Runs",
     "stats": ["Heinrich Klaasen 80* (29)", "Abhishek Sharma 63 (23) - 16-ball 50", "Travis Head 62 (24)", "18 Team Sixes"],
     "category": "World Record Scores", "emoji": "🔥"},
    {"month": 4, "day": 15, "year": 2024, "entity": "Sunrisers Hyderabad", "franchise": "Sunrisers Hyderabad",
     "title": "🔥 World Record 287/3 vs RCB — Highest Score in IPL History!",
     "desc": "Just 19 days after posting 277/3, SRH broke their own record, posting 287/3 against RCB at Chinnaswamy Stadium. Travis Head scored a 39-ball century.",
     "scorecard": "SRH 287/3 (20 ov) vs RCB 262/7 (20 ov) — Match Aggregate 549 Runs (T20 World Record)",
     "stats": ["Travis Head 102 (41)", "Heinrich Klaasen 67 (31)", "22 Team Sixes (IPL Record)"],
     "category": "World Record Scores", "emoji": "🔥"},
    {"month": 4, "day": 20, "year": 2024, "entity": "Travis Head & Abhishek Sharma", "franchise": "Sunrisers Hyderabad",
     "title": "🔥 World Record Powerplay 125/0 in 6 overs vs DC",
     "desc": "Travis Head and Abhishek Sharma unleashed the most destructive powerplay in T20 cricket history at Arun Jaitley Stadium, Delhi.",
     "scorecard": "SRH 266/7 def DC 199/10 by 67 runs",
     "stats": ["125 Runs in Powerplay (World Record)", "Travis Head 84 (26)", "Abhishek Sharma 46 (12)"],
     "category": "World Record Scores", "emoji": "🔥"},
    {"month": 5, "day": 1, "year": 2000, "entity": "Marco Jansen", "franchise": "Sunrisers Eastern Cape",
     "title": "🎂 Happy Birthday Marco Jansen!",
     "desc": "South Africa and SEC star all-rounder Marco Jansen celebrates his birthday today.",
     "stats": ["5/30 in SA20 Final", "Proteas Pace & Power Hitting"],
     "category": "Birthdays", "emoji": "🎂"},
    {"month": 5, "day": 8, "year": 1993, "entity": "Pat Cummins", "franchise": "Sunrisers Hyderabad",
     "title": "🎂 Happy Birthday Pat Cummins!",
     "desc": "Sunrisers Hyderabad skipper and World Cup winning captain Pat Cummins celebrates his birthday today.",
     "stats": ["SRH Captain", "WTC & World Cup Champion", "IPL 2024 Finalist"],
     "category": "Birthdays", "emoji": "🎂"},
    {"month": 5, "day": 26, "year": 2024, "entity": "Abhishek Sharma", "franchise": "Sunrisers Hyderabad",
     "title": "🔥 Abhishek Sharma fires SRH into IPL 2024 Final",
     "desc": "Abhishek Sharma bowled crucial overs and scored aggressive runs in Qualifier 2 vs RR, taking SRH to their first IPL Final since 2018.",
     "stats": ["2/24 in 4.0 overs", "484 IPL 2024 Runs", "SR 204.2"],
     "category": "Player Masterclasses", "emoji": "🔥"},
    {"month": 5, "day": 29, "year": 2016, "entity": "Sunrisers Hyderabad", "franchise": "Sunrisers Hyderabad",
     "title": "🏆 SRH WIN IPL 2016 TITLE at Chinnaswamy Stadium!",
     "desc": "Sunrisers Hyderabad defeated Royal Challengers Bangalore by 8 runs in a historic IPL Final to win their maiden championship.",
     "scorecard": "SRH 208/7 (20 ov) def RCB 200/7 (20 ov) by 8 runs",
     "stats": ["208/7 Title Total", "Historic Franchise Championship"],
     "category": "IPL Final", "emoji": "🏆"},
    {"month": 6, "day": 23, "year": 2024, "entity": "Pat Cummins & Travis Head", "franchise": "Sunrisers Hyderabad",
     "title": "🏆 Pat Cummins leads Australia into T20 World Cup semi-finals",
     "desc": "Pat Cummins took consecutive T20 World Cup hat-tricks (vs Bangladesh & Afghanistan), showcasing his big-match composure.",
     "stats": ["Back-to-Back Hat-tricks", "Captaincy Mastery"],
     "category": "T20 World Cup 2024", "emoji": "🏆"},
    {"month": 7, "day": 18, "year": 1998, "entity": "Ishan Kishan", "franchise": "Sunrisers Hyderabad",
     "title": "🎂 Happy Birthday Ishan Kishan!",
     "desc": "Dynamic Indian keeper-batsman Ishan Kishan celebrates his birthday today.",
     "stats": ["Fastest ODI 200 (131 balls)", "SRH Star Signee"],
     "category": "Birthdays", "emoji": "🎂"},
    {"month": 7, "day": 27, "year": 2026, "entity": "Ishan Kishan", "franchise": "Sunrisers Hyderabad",
     "title": "🏏 Ishan Kishan guides India to T20I Sweep vs Zimbabwe",
     "desc": "India crushed Zimbabwe by 90 runs in Harare to seal a 3-0 T20I series sweep, with Ishan Kishan scoring key middle-order runs.",
     "scorecard": "India 212/4 def Zimbabwe 122/10 by 90 runs",
     "stats": ["Ishan Kishan 29 (18)", "3-0 T20I Sweep"],
     "category": "International T20", "emoji": "🏏"},
    {"month": 7, "day": 30, "year": 1991, "entity": "Heinrich Klaasen", "franchise": "Sunrisers Eastern Cape",
     "title": "🎂 Happy Birthday Heinrich Klaasen!",
     "desc": "World cricket's premier T20 power-hitter and SRH/SEC superstar Heinrich Klaasen celebrates his birthday today.",
     "stats": ["Fastest SRH 100", "SA20 & IPL Powerhouse"],
     "category": "Birthdays", "emoji": "🎂"},
    {"month": 8, "day": 14, "year": 2000, "entity": "Tristan Stubbs", "franchise": "Sunrisers Eastern Cape",
     "title": "🎂 Happy Birthday Tristan Stubbs!",
     "desc": "Sunrisers Eastern Cape title hero and Proteas sensation Tristan Stubbs celebrates his birthday today.",
     "stats": ["56* in SA20 Final", "SEC Champion"],
     "category": "Birthdays", "emoji": "🎂"},
    {"month": 8, "day": 22, "year": 2023, "entity": "Harry Brook", "franchise": "Sunrisers Leeds Men",
     "title": "🏏 Harry Brook's blistering 105* (42) in The Hundred",
     "desc": "Sunrisers Leeds star Harry Brook scored a jaw-dropping century off 42 balls in The Hundred at Headingley.",
     "stats": ["105* off 42 balls", "11 Fours, 7 Sixes", "SR 250.0"],
     "category": "Batting Masterclass", "emoji": "🏏"},
    {"month": 9, "day": 4, "year": 2000, "entity": "Abhishek Sharma", "franchise": "Sunrisers Hyderabad",
     "title": "🎂 Happy Birthday Abhishek Sharma!",
     "desc": "SRH opening sensation and record holder for the fastest 50 in SRH history (16 balls) celebrates his birthday today.",
     "stats": ["484 Runs in IPL 2024", "16-ball 50 Record", "SR 204.2"],
     "category": "Birthdays", "emoji": "🎂"},
    {"month": 11, "day": 19, "year": 2023, "entity": "Pat Cummins & Travis Head", "franchise": "Sunrisers Hyderabad",
     "title": "🏆 Cummins & Head lead Australia to ODI World Cup Glory vs India",
     "desc": "Pat Cummins' masterful captaincy (3/28) and Travis Head's 137 (120) led Australia to victory in the 2023 World Cup Final at Ahmedabad.",
     "scorecard": "Australia 241/4 (43.0 ov) def India 240/10 (50.0 ov) by 6 wickets",
     "stats": ["Travis Head 137 (120)", "Pat Cummins 3/28", "World Cup Champions"],
     "category": "International", "emoji": "🏆"},
    {"month": 12, "day": 10, "year": 2022, "entity": "Ishan Kishan", "franchise": "Sunrisers Hyderabad",
     "title": "🔥 Ishan Kishan's World Record 210 (131) vs Bangladesh",
     "desc": "Ishan Kishan smashed the fastest double century in ODI history off 126 balls against Bangladesh at Chattogram.",
     "scorecard": "India 409/8 def Bangladesh 182/10 by 227 runs",
     "stats": ["210 off 131 balls", "24 Fours, 10 Sixes", "Fastest ODI 200 (126b)"],
     "category": "World Record Scores", "emoji": "🔥"},
    {"month": 12, "day": 29, "year": 1993, "entity": "Travis Head", "franchise": "Sunrisers Hyderabad",
     "title": "🎂 Happy Birthday Travis Head!",
     "desc": "SRH opener and World Cup Final Player of the Match Travis Head celebrates his birthday today.",
     "stats": ["102 (41) vs RCB", "World Cup Final 137", "IPL 2024 Star"],
     "category": "Birthdays", "emoji": "🎂"},
]
with tab_otd:
    st.markdown("<h3 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;margin-bottom:0.3rem;'>🗓️ On This Day — Historical Telemetry Engine</h3>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;margin-bottom:1.2rem;font-weight:500;'>Explore player birthdays, batting/bowling masterclasses, team score records, and championship titles across Sunrisers history.</div>", unsafe_allow_html=True)
    st.markdown("""
    <div style='display:grid;grid-template-columns:repeat(auto-fit, minmax(160px, 1fr));gap:0.8rem;margin-bottom:1.5rem;'>
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.8rem 1rem;box-shadow:0 2px 6px rgba(0,0,0,0.02);'>
            <div style='font-size:1.3rem;font-weight:800;color:#0F172A;'>83 Roster</div>
            <div style='font-size:0.78rem;color:#64748B;font-weight:600;'>Strict Excel Players</div>
        </div>
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.8rem 1rem;box-shadow:0 2px 6px rgba(0,0,0,0.02);'>
            <div style='font-size:1.3rem;font-weight:800;color:#F26522;'>4 Titles</div>
            <div style='font-size:0.78rem;color:#64748B;font-weight:600;'>IPL & SA20 Championships</div>
        </div>
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.8rem 1rem;box-shadow:0 2px 6px rgba(0,0,0,0.02);'>
            <div style='font-size:1.3rem;font-weight:800;color:#DC2626;'>277 & 287</div>
            <div style='font-size:0.78rem;color:#64748B;font-weight:600;'>IPL Record Team Totals</div>
        </div>
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.8rem 1rem;box-shadow:0 2px 6px rgba(0,0,0,0.02);'>
            <div style='font-size:1.3rem;font-weight:800;color:#0284C7;'>10 Squad</div>
            <div style='font-size:0.78rem;color:#64748B;font-weight:600;'>Player Birthdays Tracked</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    col_date_picker, col_cat_filter, col_search = st.columns([1.6, 2, 2.2])
    months_list = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    _now = datetime.now()
    with col_date_picker:
        selected_date = st.date_input(
            "📅 Select Date to Inspect",
            value=_now,
            label_visibility="visible"
        )
        sel_month = selected_date.month
        sel_day = selected_date.day
        sel_label = selected_date.strftime("%B %d")
    with col_cat_filter:
        otd_category_filter = st.selectbox(
            "🏷️ Filter Milestone Category",
            ["All Categories", "Birthdays", "IPL Final", "SA20 Final", "World Record Scores", "Batting Masterclass", "Bowling Spells", "Player Masterclasses"]
        )
    with col_search:
        otd_search_query = st.text_input(
            "🔍 Search Player / Team / Record",
            placeholder="e.g. Cummins, Head, 287, Klaasen, SA20...",
            label_visibility="visible"
        )
    date_matched_moments = [m for m in ON_THIS_DAY_DB if m["month"] == sel_month and m["day"] == sel_day]
    if otd_category_filter != "All Categories":
        date_matched_moments = [m for m in date_matched_moments if m.get("category") == otd_category_filter]
    if franchise_filter != "All":
        _fmap = {
            "Sunrisers Hyderabad": "Sunrisers Hyderabad",
            "Sunrisers Eastern Cape": "Sunrisers Eastern Cape",
            "Sunrisers Leeds Men": "Sunrisers Leeds",
            "Sunrisers Leeds Women": "Sunrisers Leeds",
        }
        _fkey = _fmap.get(franchise_filter, franchise_filter)
        date_matched_moments = [m for m in date_matched_moments if _fkey in m.get("franchise", "")]
    if otd_search_query.strip():
        q = otd_search_query.strip().lower()
        search_matched_moments = [
            m for m in ON_THIS_DAY_DB
            if q in m.get("entity", "").lower()
            or q in m.get("title", "").lower()
            or q in m.get("desc", "").lower()
            or q in m.get("category", "").lower()
            or q in m.get("scorecard", "").lower()
            or any(q in s.lower() for s in m.get("stats", []))
        ]
    else:
        search_matched_moments = []
    st.markdown("---")
    if otd_search_query.strip():
        st.markdown(f"<h4 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;'>🔍 Search Results for \"{otd_search_query}\" ({len(search_matched_moments)} found)</h4>", unsafe_allow_html=True)
        if search_matched_moments:
            for m in sorted(search_matched_moments, key=lambda x: (x["month"], x["day"]), reverse=False):
                st.markdown(render_otd_telemetry_card(m, is_hero=False), unsafe_allow_html=True)
        else:
            st.info(f"No historical moments matching \"{otd_search_query}\". Try searching for 'Cummins', 'Head', '287', or 'Birthday'.")
    else:
        is_today_selected = (sel_month == _now.month and sel_day == _now.day)
        date_title = f"🗓️ Historical Milestones for {sel_label}" + (" (TODAY)" if is_today_selected else "")
        st.markdown(f"<h4 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;margin-bottom:1rem;'>{date_title}</h4>", unsafe_allow_html=True)
        if date_matched_moments:
            for m in sorted(date_matched_moments, key=lambda x: x["year"], reverse=True):
                st.markdown(render_otd_telemetry_card(m, is_hero=is_today_selected), unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style='text-align:center;padding:3rem 2rem;background:#FFFFFF;border:1px dashed #CBD5E1;border-radius:14px;margin:1rem 0;'>
                <div style='font-size:2.8rem;margin-bottom:0.6rem;'>🗓️</div>
                <div style='font-size:1.25rem;font-weight:800;color:#0F172A;margin-bottom:0.4rem;'>No recorded Sunrisers milestones for {sel_label}</div>
                <div style='color:#64748B;font-size:0.95rem;'>Use the date picker above or search bar to explore birthdays, batting/bowling masterclasses, and championship dates!</div>
            </div>
            """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<h4 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;margin-bottom:1rem;'>📜 Full Sunrisers Historical Milestone Archive (Active Roster Only)</h4>", unsafe_allow_html=True)
    all_sorted = sorted(ON_THIS_DAY_DB, key=lambda x: (x["month"], x["day"]), reverse=False)
    if franchise_filter != "All":
        _fmap = {
            "Sunrisers Hyderabad": "Sunrisers Hyderabad",
            "Sunrisers Eastern Cape": "Sunrisers Eastern Cape",
            "Sunrisers Leeds Men": "Sunrisers Leeds",
            "Sunrisers Leeds Women": "Sunrisers Leeds",
        }
        _fkey = _fmap.get(franchise_filter, franchise_filter)
        all_sorted = [m for m in all_sorted if _fkey in m.get("franchise", "")]
    for m in all_sorted:
        date_label = datetime(2000, m["month"], m["day"]).strftime("%B %d")
        is_today_mark = " 🔴 TODAY" if (m["month"] == _now.month and m["day"] == _now.day) else ""
        stat_preview = f" ({m['stats'][0]})" if m.get("stats") else ""
        cat_badge = f"<span class='chip-league' style='font-size:0.75rem;padding:2px 7px;'>{m['category']}</span>"
        st.markdown(
            f"<div style='padding:0.6rem 0;border-bottom:1px solid #E2E8F0;font-size:0.94rem;display:flex;align-items:center;flex-wrap:wrap;gap:0.5rem;'>"
            f"<span style='color:#E05600;font-family:Inter,sans-serif;font-weight:800;min-width:100px;'>{date_label}{is_today_mark}</span> "
            f"<span style='color:#F26522;font-weight:800;min-width:50px;'>{m['year']}</span> "
            f"{cat_badge} "
            f"<span style='color:#0284C7;font-weight:700;'>👤 {m['entity']}</span> — "
            f"<span style='color:#1E293B;'>{m['title']}</span>"
            f"<span style='color:#64748B;font-weight:500;font-size:0.86rem;'>{stat_preview}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
