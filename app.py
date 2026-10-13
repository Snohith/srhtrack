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
import urllib.parse
from datetime import datetime, date as date_cls
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streamlit as st
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


def _load_dotenv(path=".env"):
    """Minimal .env loader (no extra dependency): KEY=VALUE lines only."""
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        env_path = path if os.path.isabs(path) else os.path.join(base, path)
        if not os.path.exists(env_path):
            return
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


_load_dotenv()


def _get_auto_ingest_interval_secs():
    try:
        return max(60, int(os.environ.get("AUTO_INGEST_INTERVAL_SECS", "900")))
    except (TypeError, ValueError):
        return 900


AUTO_INGEST_INTERVAL_SECS = _get_auto_ingest_interval_secs()
if "last_refreshed" not in st.session_state:
    st.session_state["last_refreshed"] = format_ist_12hr()
if "last_refresh_ts" not in st.session_state:
    st.session_state["last_refresh_ts"] = 0.0
if "auto_ingest_running" not in st.session_state:
    st.session_state["auto_ingest_running"] = False
@st.cache_data(ttl=60)
def cached_get_recent_news(limit=150):
    return get_recent_news(limit=limit)
@st.cache_data(ttl=60)
def cached_search_news(query):
    return search_news(query)


def _secs_since_last_ingest():
    try:
        return time.time() - float(get_metadata("last_auto_ingest_ts", "0") or 0)
    except (TypeError, ValueError):
        return float("inf")


def _run_ingest_cycle(reason):
    """Single synchronous ingest + cache invalidation shared by auto & manual.

    Timestamp is written AFTER a successful fetch so a failed cycle retries
    on the next tick instead of silently skipping a full interval.
    """
    result = fetch_and_filter_rss()
    try:
        cached_get_recent_news.clear()
        cached_search_news.clear()
    except Exception:
        pass
    now = time.time()
    try:
        set_metadata("last_auto_ingest_ts", str(now))
    except Exception:
        pass
    st.session_state["last_refreshed"] = format_ist_12hr()
    st.session_state["last_refresh_ts"] = now
    return result


_secs_since_auto = _secs_since_last_ingest()
if _secs_since_auto >= AUTO_INGEST_INTERVAL_SECS and not st.session_state["auto_ingest_running"]:
    st.session_state["auto_ingest_running"] = True
    try:
        with st.spinner(f"Auto-syncing {_source_count} feeds..."):
            _run_ingest_cycle("auto")
    except Exception as exc:
        try:
            from utils.logger import error_logger
            error_logger.error(f"Auto RSS ingest failed: {exc}")
        except Exception:
            pass
    finally:
        st.session_state["auto_ingest_running"] = False
    _secs_since_auto = 0.0
if len(cached_get_recent_news(limit=1)) == 0:
    with st.spinner(f"Loading matchday intelligence (scanning {_source_count} feeds)..."):
        try:
            _run_ingest_cycle("bootstrap")
        except Exception:
            pass


@st.fragment(run_every=AUTO_INGEST_INTERVAL_SECS)
def _auto_refresh_tick():
    """Fires every AUTO_INGEST_INTERVAL_SECS with zero interaction.

    A fragment rerun alone would not refresh the feed list (rendered outside
    the fragment), so escalate to a full app rerun — the ingest check above
    then runs synchronously and the current render shows fresh rows.
    """
    if _secs_since_last_ingest() >= AUTO_INGEST_INTERVAL_SECS:
        st.rerun()


_auto_refresh_tick()


def get_bulletproof_sort_key(n):
    ts = n.get("pub_timestamp")
    if ts and isinstance(ts, (int, float)) and ts > 0:
        return ts
    pub_str = str(n.get("published_at", ""))
    try:
        return datetime.strptime(pub_str, "%b %d, %Y @ %I:%M %p IST").timestamp()
    except Exception:
        return 0.0
st.sidebar.markdown("<div class='srh-side-brand'><span class='dot'>●</span> SRHXtra</div><div class='srh-side-label' style='margin-bottom:1rem;'>Squad telemetry · V15</div>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown(f"<span class='srh-side-label'>Roster</span>\n`{_player_count} players · 4 squads`")
st.sidebar.markdown(f"<span class='srh-side-label'>Last refreshed · IST</span>\n`{st.session_state['last_refreshed']}`")
_auto_mins_total = AUTO_INGEST_INTERVAL_SECS // 60
_auto_secs_remaining = max(0, int(AUTO_INGEST_INTERVAL_SECS - _secs_since_auto))
_auto_mins = _auto_secs_remaining // 60
_auto_s = _auto_secs_remaining % 60
if _auto_secs_remaining > 0:
    st.sidebar.caption(f"Auto-sync every {_auto_mins_total}m · next in {_auto_mins}m {_auto_s:02d}s")
else:
    st.sidebar.caption("Sync running…")
try:
    from utils.telegram import is_telegram_configured, get_telegram_config as _tg_cfg
    if is_telegram_configured():
        st.sidebar.caption(f"🔔 Telegram alerts ON ({_tg_cfg()['mode']})")
    else:
        st.sidebar.caption("🔕 Telegram alerts off — set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env")
except Exception:
    pass
st.sidebar.markdown("---")
franchise_filter = st.sidebar.selectbox(
    "Squad",
    ["All", "Sunrisers Hyderabad", "Sunrisers Eastern Cape", "Sunrisers Leeds Men", "Sunrisers Leeds Women"]
)
if st.sidebar.button(f"Refresh feeds ({_source_count})", use_container_width=True):
    with st.spinner(f"Polling {_source_count} global sources..."):
        result = _run_ingest_cycle("manual")
        inserted = getattr(result, "inserted", int(result))
        failed = getattr(result, "failed_feeds", [])
        st.sidebar.success(f"Captured {inserted} fresh items!")
        if failed:
            st.sidebar.warning(f"{len(failed)} feeds unavailable.")
    st.rerun()
with st.sidebar.expander("Squad roster", expanded=False):
    for fkey, fdata in MASTER_ROSTER.items():
        fname = fdata.get("franchise_name", fkey)
        p_list = fdata.get("players", [])
        coach = next((p["name"] for p in p_list if "coach" in p.get("role", "").lower() or "vettori" in p["name"].lower() or "birrell" in p["name"].lower()), None)
        captain = next((p["name"] for p in p_list if p.get("captain")), None)
        st.markdown(f"**{fname}**: `{len(p_list)} members`")
        if coach:
            st.caption(f"Coach · **{coach}**")
        if captain:
            st.caption(f"Captain · **{captain}**")
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
    f"Live feed ({live_count})",
    "Matchday",
    f"Squads ({_player_count})",
])
with tab_news:
    st.markdown("<div class='srh-section-title'>Live feed</div><div class='srh-section-sub'>Real-time squad intelligence from every ingestion cycle.</div>", unsafe_allow_html=True)
    col_search, col_stats = st.columns([3, 1])
    with col_search:
        search_query = st.text_input(
            "Search player, team or keyword",
            placeholder="Search e.g. Abhishek Sharma, Travis Head, injury, SA20...",
            label_visibility="collapsed",
        )
    if search_query.strip():
        news_list = cached_search_news(search_query.strip())
        st.caption(f"{len(news_list)} results for *\"{search_query}\"*")
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
                    <span>Live timeline</span>
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
            st.info(f"No player updates in the last 24 hours. Use 'Refresh feeds' in the sidebar for a full sweep.")
with tab_schedule:
    st.markdown("<div class='srh-section-title'>Matchday</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='srh-section-sub'>"
        f"Live from <a href='{CREX_SCHEDULE_URL}' target='_blank' rel='noopener'>crex.com/schedule</a> · "
        f"today through the next 4 days. "
        f"Every squad checked against the roster — Sunrisers fixtures only, live first.</div>",
        unsafe_allow_html=True,
    )
    col_ctrl, col_m1, col_m2, col_m3 = st.columns([1.5, 1, 1, 1])
    with col_ctrl:
        if st.button("Refresh matchday", use_container_width=True):
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
    st.caption(f"Next fixture · **{next_match_date}** · Crex live schedule, refreshes every 15 min")
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
            st.markdown(f"<div class='srh-date-group'>{date_str}</div>", unsafe_allow_html=True)
            for item in items:
                status = _fixture_live_status(item)
                st.markdown(render_broadcast_match_card(item, status=status), unsafe_allow_html=True)
    else:
        st.info(f"No upcoming Sunrisers fixtures for **{franchise_filter}** right now. Refresh matchday to re-check live.")
with tab_squads:
    st.markdown("<div class='srh-section-title'>Squads</div><div class='srh-section-sub'>Active rosters, staff and national representation across the Sunrisers network.</div>", unsafe_allow_html=True)

    if franchise_filter in ("All", "Sunrisers Hyderabad"):
        st.markdown("<div class='srh-date-group'>Ownership & business · Sun Group</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='srh-stat-grid'>
            <div class='srh-stat'>
                <div class='srh-stat-num'>Kalanithi Maran</div>
                <div class='srh-stat-lbl'>Founder & Chairman, Sun Group</div>
            </div>
            <div class='srh-stat'>
                <div class='srh-stat-num'>Kavya Maran</div>
                <div class='srh-stat-lbl'>CEO — SRH & Sunrisers Eastern Cape</div>
            </div>
            <div class='srh-stat'>
                <div class='srh-stat-num'>Sun TV Network Ltd</div>
                <div class='srh-stat-lbl'>NSE: SUNTVNET / BSE: 532733</div>
            </div>
        </div>
        <div class='srh-section-sub'>
            <a href='https://www.suntv.in/financial-information.html' target='_blank' rel='noopener'>Sun TV Investor Relations</a> ·
            <a href='https://www.bseindia.com/' target='_blank' rel='noopener'>BSE Filings</a> ·
            <a href='https://www.nseindia.com/' target='_blank' rel='noopener'>NSE Filings</a> ·
            <a href='https://find-and-update.company-information.service.gov.uk/search?q=Sunrisers+Leeds' target='_blank' rel='noopener'>Companies House</a> ·
            <a href='https://en.wikipedia.org/wiki/Sun_Group' target='_blank' rel='noopener'>Sun Group</a>
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
            st.markdown(f"<div class='srh-note' style='margin-bottom:0.5rem;'>Ownership & business · {len(_biz_news)}</div>", unsafe_allow_html=True)
            for _bn in _biz_news:
                st.markdown(render_telemetry_news_card(_bn), unsafe_allow_html=True)
        else:
            st.caption("No ownership or business stories in the last 24 hours — exchange filings and business wires are polled with every ingest cycle.")

    col_sq_f, col_sq_role, col_sq_search = st.columns([1.5, 1.2, 2])
    with col_sq_f:
        squad_team_options = ["All Franchises"] + [fdata["franchise_name"] for fdata in MASTER_ROSTER.values()]
        def_idx = squad_team_options.index(franchise_filter) if franchise_filter in squad_team_options else 0
        squad_team_filter = st.selectbox("Team", squad_team_options, index=def_idx, key="squad_team_sel")
    with col_sq_role:
        squad_role_filter = st.selectbox(
            "Role",
            ["All Roles", "Head Coach", "Captains & Leaders", "Wicket-keepers", "Batters", "All-rounders", "Bowlers", "Overseas Players"],
            key="squad_role_sel"
        )
    with col_sq_search:
        squad_search_query = st.text_input("Search", placeholder="Player, coach or country…", key="squad_search_input")

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
    <div class='srh-stat-grid'>
        <div class='srh-stat'>
            <div class='srh-stat-num'>{total_found}</div>
            <div class='srh-stat-lbl'>Members shown</div>
        </div>
        <div class='srh-stat'>
            <div class='srh-stat-num'>{coach_count}</div>
            <div class='srh-stat-lbl'>Coaches</div>
        </div>
        <div class='srh-stat'>
            <div class='srh-stat-num'>{cap_count}</div>
            <div class='srh-stat-lbl'>Captains</div>
        </div>
        <div class='srh-stat'>
            <div class='srh-stat-num'>{distinct_countries}</div>
            <div class='srh-stat-lbl'>Nations</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if filtered_members:
        if squad_team_filter == "All Franchises":
            teams_in_results = {}
            for p in filtered_members:
                teams_in_results.setdefault(p["franchise"], []).append(p)
            for tname, plist in teams_in_results.items():
                st.markdown(f"<div class='srh-date-group'>{tname} · {len(plist)}</div>", unsafe_allow_html=True)
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
