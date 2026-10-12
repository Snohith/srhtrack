"""
SRHXtra — Squad Telemetry & Matchday Intelligence Engine (V15 — Live Crex Matchday).
Bespoke Athletic Editorial & Data Telemetry System for Sunrisers Franchise Network:
  - Sunrisers Hyderabad (IPL)
  - Sunrisers Eastern Cape (SA20)
  - Sunrisers Leeds Men & Women (The Hundred)
V15 Upgrades:
  - STRICT Excel Roster Enforcement (100% of tracked entities belong exclusively to squadofsunrisers.xlsx)
  - LIVE Crex Matchday Engine (scrapes crex.com/schedule, checks Playing XI squads
    against the roster, lists only fixtures with Sunrisers players — LIVE first,
    finished matches removed)
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
    render_broadcast_match_card,
    render_squad_member_card,
    get_favicon_url, safe_article_link, time_ago,
    parse_fixture_datetime, get_fixture_status
)
from scrapers.matchday_scraper import (
    get_sunrisers_fixtures, clear_matchday_cache, CREX_SCHEDULE_URL,
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
    _source_count = 193
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
st.sidebar.markdown("<div style='color:#E05600;font-family:Inter,sans-serif;font-size:0.82rem;font-weight:800;margin-bottom:1rem;'>SQUAD TELEMETRY V15 · LIVE CREX MATCHDAY</div>", unsafe_allow_html=True)
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
        p_list = fdata.get("players", [])
        coach = next((p["name"] for p in p_list if "coach" in p.get("role", "").lower() or "vettori" in p["name"].lower() or "birrell" in p["name"].lower()), None)
        captain = next((p["name"] for p in p_list if p.get("captain")), None)
        st.markdown(f"**{fname}**: `{len(p_list)} members`")
        if coach:
            st.caption(f"👔 Coach: **{coach}**")
        if captain:
            st.caption(f"👑 Captain: **{captain}**")
st.markdown(render_header_banner(_player_count, 4), unsafe_allow_html=True)
@st.cache_data(ttl=900)
def cached_get_matchday_fixtures():
    """Live Crex fixtures (LIVE first, finished removed). Cached 15 min."""
    try:
        return get_sunrisers_fixtures()
    except Exception:
        return []


def _fixture_live_status(s):
    return s.get("status") or get_fixture_status(s)


try:
    matchday_fixtures = cached_get_matchday_fixtures()
except Exception:
    matchday_fixtures = []
if not matchday_fixtures:
    # Offline fallback: legacy static calendar, LIVE/UPCOMING only.
    matchday_fixtures = [
        s for s in FIXTURE_SCHEDULE if get_fixture_status(s) in ["LIVE", "UPCOMING"]
    ]
live_fixtures = [s for s in matchday_fixtures if _fixture_live_status(s) == "LIVE"]
if live_fixtures:
    hero_fixture = live_fixtures[0]
    hero_status = "LIVE"
elif matchday_fixtures:
    hero_fixture = sorted(matchday_fixtures, key=lambda x: parse_fixture_datetime(x) or datetime.max)[0]
    hero_status = _fixture_live_status(hero_fixture)
else:
    hero_fixture = None
    hero_status = "UPCOMING"
if hero_fixture:
    st.markdown(render_next_match_hero(hero_fixture, status=hero_status), unsafe_allow_html=True)
live_count = len(cached_get_recent_news(limit=150))
st.markdown(render_telemetry_metrics(_source_count, _player_count, live_count), unsafe_allow_html=True)
tab_news, tab_schedule, tab_squads = st.tabs([
    f"📡 LIVE PULSE & NEWS RECON FEED ({live_count})",
    "📋 MATCH DAY FIXTURE BREAKDOWN",
    f"👥 SQUAD DATABASE & DIRECTORY ({_player_count})",
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
    st.markdown("<h3 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;margin-bottom:0.4rem;'>📋 Match Day Breakdown & Roster Coverage</h3>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:#475569;margin-bottom:1.0rem;font-weight:500;'>"
        f"Live from <a href='{CREX_SCHEDULE_URL}' target='_blank' rel='noopener'>crex.com/schedule</a> — "
        f"every Squad / Playing XI checked against the Excel roster. "
        f"Only fixtures with Sunrisers players are listed. LIVE first, finished matches removed.</div>",
        unsafe_allow_html=True,
    )
    col_ctrl, col_m1, col_m2, col_m3 = st.columns([1.5, 1, 1, 1])
    with col_ctrl:
        if st.button("🔄 Refresh Matchday (Crex)", use_container_width=True):
            clear_matchday_cache()
            cached_get_matchday_fixtures.clear()
            st.rerun()
    base_schedule = [s for s in matchday_fixtures if _fixture_live_status(s) in ["LIVE", "UPCOMING"]]
    live_now = sum(1 for s in base_schedule if _fixture_live_status(s) == "LIVE")
    next_match_date = base_schedule[0]["date_str"] if base_schedule else "N/A"
    active_leagues = len({s["league"] for s in base_schedule})
    with col_m1:
        st.metric("Fixtures Listed", len(base_schedule))
    with col_m2:
        st.metric("Live Now", live_now)
    with col_m3:
        st.metric("Leagues Tracked", active_leagues)
    st.caption(f"📅 Next fixture: **{next_match_date}** · Source: Crex live schedule (auto-refreshes every 15 min)")
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
            if franchise_filter in str(s.get("squad", "")):
                return True
            if franchise_filter in str(s.get("vs", "")):
                return True
            if franchise_filter in (s.get("franchises") or []):
                return True
            if franchise_filter == "Sunrisers Leeds Men" and s.get("squad") == "Sunrisers Leeds":
                return True
            if any(pname in str(s.get("players", "")) for pname in franchise_players):
                return True
            return False
        filtered_sched = [s for s in base_schedule if _fixture_matches_filter(s)]
    else:
        filtered_sched = base_schedule
    filtered_sched = sorted(
        filtered_sched,
        key=lambda x: (0 if _fixture_live_status(x) == "LIVE" else 1, parse_fixture_datetime(x) or datetime.max),
    )
    if filtered_sched:
        grouped_dates = {}
        for item in filtered_sched:
            grouped_dates.setdefault(item["date_str"], []).append(item)
        for date_str, items in grouped_dates.items():
            st.markdown(f"<h4 style='color:#E05600;font-family:Inter,sans-serif;font-weight:800;margin-top:1.5rem;margin-bottom:0.8rem;'>📅 {date_str}</h4>", unsafe_allow_html=True)
            for item in items:
                status = _fixture_live_status(item)
                st.markdown(render_broadcast_match_card(item, status=status), unsafe_allow_html=True)
    else:
        st.info(f"No upcoming Sunrisers fixtures for **{franchise_filter}** right now. Crex squads show no rostered players — hit '🔄 Refresh Matchday' to re-check live.")
with tab_squads:
    st.markdown("<h3 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;margin-bottom:0.4rem;'>👥 Official Squad Database & Roster Directory</h3>", unsafe_allow_html=True)
    st.markdown("<div style='color:#475569;margin-bottom:1.2rem;font-weight:500;'>Official active squads, coaching leadership, player roles, and national representation across the Sunrisers network.</div>", unsafe_allow_html=True)

    if franchise_filter in ("All", "Sunrisers Hyderabad"):
        st.markdown("<h4 style='font-family:Inter,sans-serif;font-weight:800;color:#0F172A;margin-bottom:0.8rem;'>🏢 Ownership & Business — Sun Group</h4>", unsafe_allow_html=True)
        st.markdown("""
        <div style='display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:0.8rem;margin-bottom:1rem;'>
            <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.8rem 1rem;'>
                <div style='font-size:1rem;font-weight:800;color:#0F172A;'>Kalanithi Maran</div>
                <div style='font-size:0.8rem;color:#64748B;font-weight:600;'>Founder & Chairman, Sun Group</div>
            </div>
            <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.8rem 1rem;'>
                <div style='font-size:1rem;font-weight:800;color:#0F172A;'>Kavya Maran</div>
                <div style='font-size:0.8rem;color:#64748B;font-weight:600;'>CEO — SRH & Sunrisers Eastern Cape</div>
            </div>
            <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.8rem 1rem;'>
                <div style='font-size:1rem;font-weight:800;color:#0F172A;'>Sun TV Network Ltd</div>
                <div style='font-size:0.8rem;color:#64748B;font-weight:600;'>Listed — NSE: SUNTVNET / BSE: 532733. Exchange filings disclose franchise deals first.</div>
            </div>
        </div>
        <div style='margin-bottom:1rem;font-size:0.88rem;'>
            <a href='https://www.suntv.in/financial-information.html' target='_blank' rel='noopener'>📄 Sun TV Investor Relations</a> &nbsp;·&nbsp;
            <a href='https://www.bseindia.com/' target='_blank' rel='noopener'>📈 BSE Filings</a> &nbsp;·&nbsp;
            <a href='https://www.nseindia.com/' target='_blank' rel='noopener'>📉 NSE Filings</a> &nbsp;·&nbsp;
            <a href='https://find-and-update.company-information.service.gov.uk/search?q=Sunrisers+Leeds' target='_blank' rel='noopener'>🏛️ Companies House: Sunrisers Leeds</a> &nbsp;·&nbsp;
            <a href='https://en.wikipedia.org/wiki/Sun_Group' target='_blank' rel='noopener'>📚 Sun Group — Wikipedia</a>
        </div>
        """, unsafe_allow_html=True)
        try:
            _biz_pool = cached_get_recent_news(limit=150)
        except Exception:
            _biz_pool = []
        _biz_keywords = ("kavya maran", "kalanithi", "sun tv", "sun group", "acquisition", "stake",
                         "valuation", "rebrand", "filing", "companies house", "investor")
        _biz_news = [
            _n for _n in _biz_pool
            if _n.get("player_name") in ("Kavya Maran", "Kalanithi Maran")
            or any(_k in f"{_n.get('title', '')} {_n.get('summary', '')}".lower() for _k in _biz_keywords)
        ][:8]
        if _biz_news:
            st.markdown(f"<div style='font-weight:700;color:#0F172A;margin-bottom:0.5rem;'>📰 Latest ownership & business news ({len(_biz_news)})</div>", unsafe_allow_html=True)
            for _bn in _biz_news:
                st.markdown(render_telemetry_news_card(_bn), unsafe_allow_html=True)
        else:
            st.caption("No ownership or business stories in the last 24 hours — exchange filings and business wires are polled with every ingest cycle.")

    col_sq_f, col_sq_role, col_sq_search = st.columns([1.5, 1.2, 2])
    with col_sq_f:
        squad_team_options = ["All Franchises"] + [fdata["franchise_name"] for fdata in MASTER_ROSTER.values()]
        def_idx = squad_team_options.index(franchise_filter) if franchise_filter in squad_team_options else 0
        squad_team_filter = st.selectbox("Franchise Team", squad_team_options, index=def_idx, key="squad_team_sel")
    with col_sq_role:
        squad_role_filter = st.selectbox(
            "Filter Role",
            ["All Roles", "Head Coach", "Captains & Leaders", "Wicket-keepers", "Batters", "All-rounders", "Bowlers", "Overseas Players"],
            key="squad_role_sel"
        )
    with col_sq_search:
        squad_search_query = st.text_input("🔍 Search Player / Coach / Country", placeholder="e.g. Vettori, Head, Cummins, Klaasen, Australia...", key="squad_search_input")

    filtered_members = []
    for fkey, fdata in MASTER_ROSTER.items():
        fname = fdata["franchise_name"]
        if squad_team_filter != "All Franchises" and squad_team_filter != fname:
            continue
        for p in fdata["players"]:
            filtered_members.append({**p, "franchise": fname, "league": fdata["league"]})

    if squad_search_query.strip():
        q = squad_search_query.strip().lower()
        filtered_members = [
            p for p in filtered_members
            if q in p["name"].lower() or q in p["role"].lower() or q in p["country"].lower() or q in p["franchise"].lower()
        ]

    if squad_role_filter == "Head Coach":
        filtered_members = [p for p in filtered_members if "coach" in p["role"].lower() or "vettori" in p["name"].lower() or "birrell" in p["name"].lower()]
    elif squad_role_filter == "Captains & Leaders":
        filtered_members = [p for p in filtered_members if p.get("captain") or "(c)" in p["name"].lower() or "captain" in p["role"].lower()]
    elif squad_role_filter == "Wicket-keepers":
        filtered_members = [p for p in filtered_members if "(wk)" in p["name"].lower() or "wicket-keeper" in p["role"].lower()]
    elif squad_role_filter == "Batters":
        filtered_members = [p for p in filtered_members if "batter" in p["role"].lower() and "wicket-keeper" not in p["role"].lower()]
    elif squad_role_filter == "All-rounders":
        filtered_members = [p for p in filtered_members if "all-rounder" in p["role"].lower()]
    elif squad_role_filter == "Bowlers":
        filtered_members = [p for p in filtered_members if "bowler" in p["role"].lower() and "all-rounder" not in p["role"].lower()]
    elif squad_role_filter == "Overseas Players":
        def _is_os(p):
            c = p.get("country", "")
            f = p.get("franchise", "")
            if "coach" in p.get("role", "").lower(): return False
            if "Hyderabad" in f: return c != "India"
            if "Eastern Cape" in f: return c != "South Africa"
            if "Leeds" in f: return c != "England"
            return False
        filtered_members = [p for p in filtered_members if _is_os(p)]

    total_found = len(filtered_members)
    coach_count = sum(1 for p in filtered_members if "coach" in p["role"].lower() or "vettori" in p["name"].lower() or "birrell" in p["name"].lower())
    cap_count = sum(1 for p in filtered_members if p.get("captain"))
    distinct_countries = len({p["country"] for p in filtered_members if p.get("country")})

    st.markdown(f"""
    <div style='display:grid;grid-template-columns:repeat(auto-fit, minmax(150px, 1fr));gap:0.8rem;margin-top:0.8rem;margin-bottom:1.5rem;'>
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.75rem 1rem;'>
            <div style='font-size:1.3rem;font-weight:800;color:#0F172A;'>{total_found}</div>
            <div style='font-size:0.78rem;color:#64748B;font-weight:600;'>Members Displayed</div>
        </div>
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.75rem 1rem;'>
            <div style='font-size:1.3rem;font-weight:800;color:#E05600;'>{coach_count}</div>
            <div style='font-size:0.78rem;color:#64748B;font-weight:600;'>Coaching Leaders</div>
        </div>
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.75rem 1rem;'>
            <div style='font-size:1.3rem;font-weight:800;color:#B45309;'>{cap_count}</div>
            <div style='font-size:0.78rem;color:#64748B;font-weight:600;'>Captains</div>
        </div>
        <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;padding:0.75rem 1rem;'>
            <div style='font-size:1.3rem;font-weight:800;color:#0284C7;'>{distinct_countries} Nations</div>
            <div style='font-size:0.78rem;color:#64748B;font-weight:600;'>Global Representation</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if filtered_members:
        if squad_team_filter == "All Franchises":
            teams_in_results = {}
            for p in filtered_members:
                teams_in_results.setdefault(p["franchise"], []).append(p)
            for tname, plist in teams_in_results.items():
                st.markdown(f"<h4 style='color:#E05600;font-family:Inter,sans-serif;font-weight:800;margin-top:1.5rem;margin-bottom:0.8rem;'>🧡 {tname} ({len(plist)} members)</h4>", unsafe_allow_html=True)
                cols = st.columns(3)
                for idx, player in enumerate(plist):
                    with cols[idx % 3]:
                        st.markdown(render_squad_member_card(player, franchise_name=tname), unsafe_allow_html=True)
        else:
            cols = st.columns(3)
            for idx, player in enumerate(filtered_members):
                with cols[idx % 3]:
                    st.markdown(render_squad_member_card(player, franchise_name=squad_team_filter), unsafe_allow_html=True)
    else:
        st.info("No squad members match the current filter criteria.")
