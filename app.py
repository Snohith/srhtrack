"""Sunrisers news hub — all our teams' latest stories in one friendly place.

We follow 4 Sunrisers family teams:
  - Sunrisers Hyderabad (IPL, India)
  - Sunrisers Eastern Cape (SA20, South Africa)
  - Sunrisers Leeds Men (The Hundred, England)
  - Sunrisers Leeds Women (The Hundred, England)

How it works, in plain words:
  1. We check ~268 cricket news websites every 15 minutes.
  2. We keep only stories that mention one of our players or teams
     (the player list lives in data/squadofsunrisers.xlsx).
  3. We save those stories for 24 hours, then tidy them away.
  4. You read them here: newest first, with search and team filters.
"""
import html as html_lib
import os
import sys
import time
import random
import textwrap
import urllib.parse
from datetime import datetime, date as date_cls
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import streamlit as st
from our_teams.players import PLAYERS_BY_TEAM
from our_teams.upcoming_matches import UPCOMING_MATCHES
from saved_stories.story_storage import (
    set_up_story_box, get_latest_stories, search_stories, throw_away_old_stories,
    read_saved_fact, save_a_fact
)
from helpers.dates_and_times import show_indian_time, what_time_is_it_in_india_now, INDIAN_TIME
from our_teams.website_look import (
    get_website_style, show_top_part, show_next_match_big_box,
    show_numbers_at_top, show_big_story,
    show_story_card, show_pulse_panel,
    show_match_card,
    show_player_grid, show_stat_cards, show_empty_state,
    find_tiny_website_icon, find_good_link_for_story, how_long_ago,
    read_match_date_and_time, is_match_live_now_or_later
)
from news_collectors.find_matches import (
    find_our_upcoming_matches, forget_saved_matches, WHERE_TO_FIND_MATCHES_ONLINE,
)
try:
    from news_collectors.collect_news import collect_fresh_stories, NEWS_WEBSITES as NEWS_WEBSITES
    _source_count = len(NEWS_WEBSITES)
except Exception:
    class _FakeResult:
        inserted = 0
        failed_feeds = []
        total_polled = 0
    def collect_fresh_stories():
        return _FakeResult()
    _source_count = 268
_player_count = len({p["name"] for data in PLAYERS_BY_TEAM.values() for p in data["players"]})
st.set_page_config(
    page_title="Sunrisers News Hub — all our teams in one place",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="auto"
)
st.markdown(get_website_style(), unsafe_allow_html=True)
set_up_story_box()
throw_away_old_stories()


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


def _how_often_to_check_news():
    try:
        return max(60, int(os.environ.get("HOW_OFTEN_TO_CHECK_NEWS_SECS") or os.environ.get("AUTO_INGEST_INTERVAL_SECS", "900")))
    except (TypeError, ValueError):
        return 900


HOW_OFTEN_TO_CHECK_NEWS_SECS = _how_often_to_check_news()
if "last_refreshed" not in st.session_state:
    st.session_state["last_refreshed"] = show_indian_time()
if "last_refresh_ts" not in st.session_state:
    st.session_state["last_refresh_ts"] = 0.0
if "news_check_running" not in st.session_state:
    st.session_state["news_check_running"] = False
@st.cache_data(ttl=60)
def cached_get_recent_news(limit=150):
    return get_latest_stories(limit=limit)
@st.cache_data(ttl=60)
def cached_search_news(query):
    return search_stories(query)


def _seconds_since_last_news_check():
    try:
        return time.time() - float(read_saved_fact("last_news_check_time", "0") or 0)
    except (TypeError, ValueError):
        return float("inf")


def _do_one_news_check_and_refresh(reason):
    """Check the news once, then refresh what you see. Used by auto + manual.

    Timestamp is written AFTER a successful fetch so a failed cycle retries
    on the next tick instead of silently skipping a full interval. A cycle
    only counts as failed when EVERY polled feed failed.
    """
    result = collect_fresh_stories()
    try:
        cached_get_recent_news.clear()
        cached_search_news.clear()
    except Exception:
        pass
    now = time.time()
    try:
        failed = getattr(result, "failed_feeds", []) or []
        total = getattr(result, "total_polled", 0) or 0
        all_failed = bool(total) and len(failed) >= total
    except Exception:
        all_failed = False
    if not all_failed:
        try:
            save_a_fact("last_news_check_time", str(now))
        except Exception:
            pass
    st.session_state["last_refreshed"] = show_indian_time()
    st.session_state["last_refresh_ts"] = now
    return result


_seconds_since_last_check = _seconds_since_last_news_check()
if _seconds_since_last_check >= HOW_OFTEN_TO_CHECK_NEWS_SECS and not st.session_state["news_check_running"]:
    st.session_state["news_check_running"] = True
    try:
        with st.spinner(f"Checking {_source_count} feeds..."):
            # Cross-session race guard: two tabs whose fragment timers align
            # would both pass the gate above and check twice (double texts;
            # saved stories skip copies quietly). A short random pause keeps them apart;
            # the loser re-reads a fresh timestamp and skips.
            time.sleep(random.uniform(1.0, 8.0))
            if _seconds_since_last_news_check() >= HOW_OFTEN_TO_CHECK_NEWS_SECS:
                _do_one_news_check_and_refresh("auto")
    except Exception as exc:
        try:
            from helpers.log_books import problems_diary
            problems_diary.error(f"Auto news check failed: {exc}")
        except Exception:
            pass
    finally:
        st.session_state["news_check_running"] = False
    _seconds_since_last_check = _seconds_since_last_news_check()
if len(cached_get_recent_news(limit=1)) == 0:
    with st.spinner(f"Loading the latest stories (checking {_source_count} feeds)..."):
        try:
            _do_one_news_check_and_refresh("bootstrap")
        except Exception:
            pass


@st.fragment(run_every=HOW_OFTEN_TO_CHECK_NEWS_SECS)
def _auto_refresh_tick():
    """Fires every HOW_OFTEN_TO_CHECK_NEWS_SECS with zero interaction.

    A fragment rerun alone would not refresh the feed list (rendered outside
    the fragment), so ask for a full refresh — the news check above
    then runs synchronously and the current render shows fresh rows.
    """
    if _seconds_since_last_news_check() >= HOW_OFTEN_TO_CHECK_NEWS_SECS:
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
st.sidebar.markdown("""
<div class='srh-side-brand'><span class='srh-brand-mark' aria-hidden='true'>S</span><span>SRHXtra</span></div>
<div class='srh-side-tagline'>Sunrisers News Hub</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.markdown(f"""
<div class='srh-side-meta'>
    <div class='srh-side-meta-row'>
        <span class='srh-side-label'>Roster</span>
        <span class='srh-side-value'>{_player_count} players · 4 squads</span>
    </div>
    <div class='srh-side-meta-row'>
        <span class='srh-side-label'>Last refreshed · IST</span>
        <span class='srh-side-value'>{html_lib.escape(str(st.session_state['last_refreshed']))}</span>
    </div>
</div>
""", unsafe_allow_html=True)
_auto_mins_total = HOW_OFTEN_TO_CHECK_NEWS_SECS // 60
_auto_secs_remaining = max(0, int(HOW_OFTEN_TO_CHECK_NEWS_SECS - _seconds_since_last_check))
_auto_mins = _auto_secs_remaining // 60
_auto_s = _auto_secs_remaining % 60
if _auto_secs_remaining > 0:
    st.sidebar.caption(f"Next check in {_auto_mins}m {_auto_s:02d}s · every {_auto_mins_total} min")
else:
    st.sidebar.caption("Checking for new stories now…")
try:
    from helpers.phone_alerts import are_phone_alerts_ready, what_are_our_phone_settings as _tg_cfg
    if are_phone_alerts_ready():
        st.sidebar.caption(f"🔔 Telegram alerts on · {str(_tg_cfg()['mode']).replace('_', ' ')}")
    else:
        st.sidebar.caption("🔕 Telegram alerts off — set TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env")
except Exception:
    pass
st.sidebar.markdown("---")
franchise_filter = st.sidebar.selectbox(
    "Filter by squad",
    ["All", "Sunrisers Hyderabad", "Sunrisers Eastern Cape", "Sunrisers Leeds Men", "Sunrisers Leeds Women"]
)
if st.sidebar.button("Check for new stories", icon=":material/refresh:", use_container_width=True, type="primary"):
    with st.spinner(f"Checking {_source_count} global sources..."):
        result = _do_one_news_check_and_refresh("manual")
        inserted = getattr(result, "inserted", int(result))
        failed = getattr(result, "failed_feeds", [])
    st.session_state["refresh_notice"] = {
        "ok": f"Saved {inserted} new stories." if inserted else "Everything is up to date.",
        "warn": f"{len(failed)} sources were unavailable." if failed else "",
    }
    st.rerun()
_refresh_notice = st.session_state.pop("refresh_notice", None)
if _refresh_notice:
    st.sidebar.success(_refresh_notice["ok"])
    if _refresh_notice.get("warn"):
        st.sidebar.warning(_refresh_notice["warn"])
with st.sidebar.expander("Squads at a glance", expanded=False):
    for fkey, fdata in PLAYERS_BY_TEAM.items():
        fname = fdata.get("franchise_name", fkey)
        p_list = fdata.get("players", [])
        coach = next((p["name"] for p in p_list if "coach" in p.get("role", "").lower() or "vettori" in p["name"].lower() or "birrell" in p["name"].lower()), None)
        captain = next((p["name"] for p in p_list if p.get("captain")), None)
        st.markdown(f"**{fname}**: `{len(p_list)} members`")
        if coach:
            st.caption(f"Coach · **{coach}**")
        if captain:
            st.caption(f"Captain · **{captain}**")
st.html(show_top_part(_player_count, 4))
@st.cache_data(ttl=900)
def cached_get_matchday_fixtures():
    """Live Crex fixtures (LIVE first, finished removed). Cached 15 min."""
    try:
        return find_our_upcoming_matches()
    except Exception:
        return []


def _fixture_live_status(s):
    return s.get("status") or is_match_live_now_or_later(s)


try:
    matchday_fixtures = cached_get_matchday_fixtures()
except Exception:
    matchday_fixtures = []
if not matchday_fixtures:
    # Offline fallback: legacy static calendar, LIVE/UPCOMING only.
    matchday_fixtures = [
        s for s in UPCOMING_MATCHES if is_match_live_now_or_later(s) in ["LIVE", "UPCOMING"]
    ]
live_fixtures = [s for s in matchday_fixtures if _fixture_live_status(s) == "LIVE"]
if live_fixtures:
    hero_fixture = live_fixtures[0]
    hero_status = "LIVE"
elif matchday_fixtures:
    hero_fixture = sorted(matchday_fixtures, key=lambda x: read_match_date_and_time(x) or datetime.max)[0]
    hero_status = _fixture_live_status(hero_fixture)
else:
    hero_fixture = None
    hero_status = "UPCOMING"
if hero_fixture:
    st.html(show_next_match_big_box(hero_fixture, status=hero_status))
live_count = len(cached_get_recent_news(limit=150))
st.html(show_numbers_at_top(_source_count, _player_count, live_count))
tab_news, tab_schedule, tab_squads = st.tabs([
    f"Stories ({live_count})",
    "Matchday",
    f"Squads ({_player_count})",
])
with tab_news:
    st.html("<h2 class='sr-only'>Latest stories</h2>")
    st.html("<p class='srh-section-sub'>Fresh stories about our players, newest first.</p>")
    search_query = st.text_input(
        "Search stories",
        placeholder="Player, team or keyword",
        icon=":material/search:",
    )
    if search_query.strip():
        news_list = cached_search_news(search_query.strip())
    else:
        news_list = cached_get_recent_news(limit=150)
    if franchise_filter != "All":
        news_list = [n for n in news_list if n.get("franchise") == franchise_filter]
    news_list = sorted(news_list, key=get_bulletproof_sort_key, reverse=True)
    if search_query.strip():
        st.html(
            f"<p class='srh-result-count'><strong>{len(news_list)}</strong> results for "
            f"“{html_lib.escape(search_query.strip())}”</p>"
        )
    if franchise_filter != "All":
        st.html(
            f"<div class='srh-active-filter'><span>Squad</span>{html_lib.escape(franchise_filter)}</div>"
        )
    if news_list:
        col_main, col_pulse = st.columns([2.2, 1], gap="large")
        with col_main:
            st.html(show_big_story(news_list[0]))
            for n in news_list[1:]:
                st.html(show_story_card(n))
        with col_pulse:
            st.html(show_pulse_panel(news_list))
    else:
        if search_query.strip():
            st.html(
                show_empty_state(
                    "No matching stories",
                    f"No stories match “{search_query.strip()}”. Try another player, team or keyword.",
                )
            )
        else:
            st.html(
                show_empty_state(
                    "All quiet for now",
                    "No player updates in the last 24 hours. Use Check for new stories in the sidebar for a full sweep.",
                )
            )
with tab_schedule:
    st.html("<h2 class='sr-only'>Matchday fixtures</h2>")
    base_schedule = [s for s in matchday_fixtures if _fixture_live_status(s) in ["LIVE", "UPCOMING"]]
    live_now = sum(1 for s in base_schedule if _fixture_live_status(s) == "LIVE")
    next_match_date = base_schedule[0]["date_str"] if base_schedule else "N/A"
    active_leagues = len({s["league"] for s in base_schedule})
    col_info, col_btn = st.columns([3, 1], vertical_alignment="center")
    with col_info:
        st.html(
            f"<p class='srh-section-sub'>"
            f"Live from <a href='{WHERE_TO_FIND_MATCHES_ONLINE}' target='_blank' rel='noopener noreferrer'>crex.com/schedule</a> · "
            f"today through the next 4 days. "
            f"Every squad checked against the roster — Sunrisers fixtures only, live first.</p>"
        )
    with col_btn:
        if st.button("Refresh fixtures", icon=":material/event_repeat:", use_container_width=True):
            forget_saved_matches()
            cached_get_matchday_fixtures.clear()
            st.rerun()
    st.html(
        show_stat_cards([
            (len(base_schedule), "Fixtures listed"),
            (live_now, "Live now"),
            (active_leagues, "Leagues tracked"),
        ])
    )
    st.caption(f"Next fixture · **{next_match_date}** · refreshes every 15 min")
    if franchise_filter != "All":
        franchise_key_map = {
            "Sunrisers Hyderabad": "SRH",
            "Sunrisers Eastern Cape": "SEC",
            "Sunrisers Leeds Men": "Leeds_Men",
            "Sunrisers Leeds Women": "Leeds_Women",
        }
        fkey = franchise_key_map.get(franchise_filter, "")
        franchise_players = set()
        if fkey and fkey in PLAYERS_BY_TEAM:
            franchise_players = {p["name"] for p in PLAYERS_BY_TEAM[fkey]["players"]}
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
        key=lambda x: (0 if _fixture_live_status(x) == "LIVE" else 1, read_match_date_and_time(x) or datetime.max),
    )
    if filtered_sched:
        grouped_dates = {}
        for item in filtered_sched:
            grouped_dates.setdefault(item["date_str"], []).append(item)
        for date_str, items in grouped_dates.items():
            st.html(f"<h2 class='srh-date-group'>{html_lib.escape(date_str)}</h2>")
            for item in items:
                status = _fixture_live_status(item)
                st.html(show_match_card(item, status=status))
    else:
        st.html(
            show_empty_state(
                "No fixtures found",
                f"No upcoming Sunrisers fixtures for {franchise_filter} right now. Refresh fixtures to re-check the live schedule.",
            )
        )
with tab_squads:
    st.html("<h2 class='sr-only'>Squads</h2>")
    st.html("<p class='srh-section-sub'>Active rosters, staff and national representation across the Sunrisers network.</p>")

    if franchise_filter in ("All", "Sunrisers Hyderabad"):
        st.html("<h2 class='srh-date-group'>Ownership & business · Sun Group</h2>")
        st.html("""
        <div class='srh-stat-grid'>
            <div class='srh-stat is-info'>
                <div class='srh-stat-num'>Kalanithi Maran</div>
                <div class='srh-stat-lbl'>Founder & Chairman, Sun Group</div>
            </div>
            <div class='srh-stat is-info'>
                <div class='srh-stat-num'>Kavya Maran</div>
                <div class='srh-stat-lbl'>CEO — SRH & Sunrisers Eastern Cape</div>
            </div>
            <div class='srh-stat is-info'>
                <div class='srh-stat-num'>Sun TV Network Ltd</div>
                <div class='srh-stat-lbl'>NSE: SUNTVNET / BSE: 532733</div>
            </div>
        </div>
        <div class='srh-section-sub'>
            <a href='https://www.suntv.in/financial-information.html' target='_blank' rel='noopener noreferrer'>Sun TV Investor Relations</a> ·
            <a href='https://www.bseindia.com/' target='_blank' rel='noopener noreferrer'>BSE Filings</a> ·
            <a href='https://www.nseindia.com/' target='_blank' rel='noopener noreferrer'>NSE Filings</a> ·
            <a href='https://find-and-update.company-information.service.gov.uk/search?q=Sunrisers+Leeds' target='_blank' rel='noopener noreferrer'>Companies House</a> ·
            <a href='https://en.wikipedia.org/wiki/Sun_Group' target='_blank' rel='noopener noreferrer'>Sun Group</a>
        </div>
        """)
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
            st.html(f"<h3 class='srh-note-title'>Ownership & business stories · {len(_biz_news)}</h3>")
            for _bn in _biz_news:
                st.html(show_story_card(_bn))
        else:
            st.caption("No ownership or business stories in the last 24 hours — exchange filings and business wires are checked with every news round.")

    col_sq_f, col_sq_role, col_sq_search = st.columns([1.5, 1.2, 2])
    with col_sq_f:
        squad_team_options = ["All Franchises"] + [fdata["franchise_name"] for fdata in PLAYERS_BY_TEAM.values()]
        def_idx = squad_team_options.index(franchise_filter) if franchise_filter in squad_team_options else 0
        squad_team_filter = st.selectbox("Team", squad_team_options, index=def_idx, key="squad_team_sel")
    with col_sq_role:
        squad_role_filter = st.selectbox(
            "Role",
            ["All Roles", "Head Coach", "Captains & Leaders", "Wicket-keepers", "Batters", "All-rounders", "Bowlers", "Overseas Players"],
            key="squad_role_sel"
        )
    with col_sq_search:
        squad_search_query = st.text_input(
            "Search",
            placeholder="Player, coach or country",
            icon=":material/search:",
            key="squad_search_input",
        )

    filtered_members = []
    for fkey, fdata in PLAYERS_BY_TEAM.items():
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

    st.html(
        show_stat_cards([
            (total_found, "Members shown"),
            (coach_count, "Coaches"),
            (cap_count, "Captains"),
            (distinct_countries, "Nations"),
        ])
    )

    if filtered_members:
        if squad_team_filter == "All Franchises":
            teams_in_results = {}
            for p in filtered_members:
                teams_in_results.setdefault(p["franchise"], []).append(p)
            for tname, plist in teams_in_results.items():
                st.html(f"<h2 class='srh-date-group'>{html_lib.escape(tname)} · {len(plist)}</h2>")
                st.html(show_player_grid(plist, franchise_name=tname))
        else:
            st.html(show_player_grid(filtered_members, franchise_name=squad_team_filter))
    else:
        st.html(
            show_empty_state(
                "No squad members found",
                "No squad members match these filters. Try a different team, role or search term.",
            )
        )
