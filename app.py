"""
@SRHXtra Premium Obsidian Command Center (V12.1 — Debugged).
Section 1: Match Day Fixture Breakdown & Player Roster (cards list, no calendar grid).
Section 2: Live Pulse News Portal — live search, cached DB reads, refresh cooldown.

V12.1 fixes:
  - Franchise filter now handles composite squad names (SRH & SEC Stars, Sri Lanka & India Tests)
  - 50th RSS source added (count now matches UI label)
  - Removed unused GRID_DATE_SLOTS import
"""

import os
import sys
import time
import textwrap
import urllib.parse
from datetime import datetime

# Ensure root directory is at the top of sys.path for Streamlit Cloud
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import streamlit.components.v1 as components

from config.roster import MASTER_ROSTER
from config.schedule import FIXTURE_SCHEDULE
from database.db_manager import init_db, get_recent_news, search_news, purge_expired_24h_news
from utils.time_utils import format_ist_12hr

try:
    from scrapers.rss_collector import fetch_and_filter_rss, TOP_50_CRICKET_SOURCES
except Exception:
    def fetch_and_filter_rss():
        return 0

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="@SRHXtra Premium Obsidian Command Center",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Database Init & Startup Purge ─────────────────────────────────────────────
init_db()
purge_expired_24h_news()

# ── 30-Minute Auto-Reload Timer ───────────────────────────────────────────────
components.html(
    """
    <script>
        setTimeout(function(){ window.parent.location.reload(); }, 1800000);
    </script>
    """,
    height=0, width=0,
)

# ── Session State Defaults ────────────────────────────────────────────────────
if "last_refreshed" not in st.session_state:
    st.session_state["last_refreshed"] = format_ist_12hr()
if "last_refresh_ts" not in st.session_state:
    st.session_state["last_refresh_ts"] = 0.0

# ── Cached DB Reads (TTL = 5 minutes) ────────────────────────────────────────
@st.cache_data(ttl=300)
def cached_get_recent_news(limit=150):
    """Cached wrapper around get_recent_news() to avoid hitting SQLite on every rerun."""
    return get_recent_news(limit=limit)

@st.cache_data(ttl=300)
def cached_search_news(query):
    """Cached wrapper around search_news() for live search."""
    return search_news(query)

# ── Auto-ingest if DB is nearly empty ────────────────────────────────────────
if len(cached_get_recent_news(limit=10)) < 3:
    fetch_and_filter_rss()
    st.session_state["last_refreshed"] = format_ist_12hr()
    cached_get_recent_news.clear()

# ── Helper Functions ──────────────────────────────────────────────────────────
def get_bulletproof_sort_key(n):
    """Returns float timestamp for 100% reliable latest-first sorting."""
    ts = n.get("pub_timestamp")
    if ts and isinstance(ts, (int, float)) and ts > 0:
        return ts
    pub_str = str(n.get("published_at", ""))
    try:
        return datetime.strptime(pub_str, "%b %d, %Y @ %I:%M %p IST").timestamp()
    except Exception:
        return 0.0

def detect_league_badge(title, summary):
    """Detects league for badge display."""
    text = (str(title) + " " + str(summary)).lower()
    if any(k in text for k in ["the hundred", "hundred", "london spirit", "super giants", "welsh fire", "trent rockets", "southern brave"]):
        return "The Hundred"
    elif any(k in text for k in ["sa20", "sunrisers eastern cape", "pretoria capitals", "paarl royals"]):
        return "SA20"
    elif any(k in text for k in ["ipl", "indian premier league", "sunrisers hyderabad"]):
        return "IPL"
    elif any(k in text for k in ["t20i", "odi", "test", "india tour", "world cup", "wtc"]):
        return "International Cricket"
    return "Global Cricket"

def safe_article_link(n):
    """Returns a valid link for a news item, falling back to Google News search."""
    if n.get("link") and n["link"] != "#":
        return n["link"]
    return f"https://news.google.com/search?q={urllib.parse.quote(n['player_name'] + ' cricket')}"

def time_ago(pub_ts):
    """Converts a Unix timestamp to a human-readable 'X time ago' string."""
    if not pub_ts or pub_ts <= 0:
        return "recently"
    diff = time.time() - float(pub_ts)
    if diff < 60:
        return "just now"
    if diff < 3600:
        mins = int(diff / 60)
        return f"{mins}m ago"
    if diff < 86400:
        hrs = int(diff / 3600)
        mins = int((diff % 3600) / 60)
        return f"{hrs}h {mins}m ago" if mins else f"{hrs}h ago"
    return "1d+ ago"

def is_new_article(pub_ts, hours=2):
    """Returns True if the article was published within the last N hours."""
    if not pub_ts or pub_ts <= 0:
        return False
    return (time.time() - float(pub_ts)) < (hours * 3600)

def get_favicon_url(link):
    """Returns a Google favicon URL for a given article link."""
    try:
        domain = urllib.parse.urlparse(link).netloc
        if domain:
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=16"
    except Exception:
        pass
    return ""

import html as html_lib

def render_news_card(n):
    """Renders a full news card as an HTML string (main feed).
    Bulletproof V12.3:
      - Strips all internal newlines from title/summary to prevent Markdown code block triggers
      - Returns a zero-newline single-line HTML string for 100% reliable Streamlit rendering
    """
    link          = safe_article_link(n)
    league        = detect_league_badge(n["title"], n["summary"])
    pub_ts        = n.get("pub_timestamp", 0)
    ago           = time_ago(pub_ts)
    new_badge     = "<span class='badge-new'>🔴 NEW</span>" if is_new_article(pub_ts) else ""
    favicon       = get_favicon_url(link)
    fav_html      = f"<img src='{favicon}' class='source-fav' onerror='this.style.display=\"none\"'>" if favicon else ""
    
    clean_title   = html_lib.escape(str(n.get("title", "")).replace("\n", " ").strip())
    clean_summary = html_lib.escape(str(n.get("summary", "")).replace("\n", " ").strip())
    player_name   = html_lib.escape(str(n.get("player_name", "")).strip())
    franchise     = html_lib.escape(str(n.get("franchise", "")).strip())
    source        = html_lib.escape(str(n.get("source", "")).strip())
    pub_at        = html_lib.escape(str(n.get("published_at", "")).strip())

    card_html = (
        f"<a href='{link}' target='_blank' class='obsidian-card-link'>"
        f"<div class='obsidian-card'>"
        f"<div class='card-tags'>{new_badge}<span class='badge-player'>👤 {player_name}</span><span class='badge-squad'>🧡 {franchise} Squad</span><span class='badge-league'>🏏 {league}</span></div>"
        f"<h2 class='obsidian-card-title'>{clean_title}</h2>"
        f"<p class='obsidian-card-desc'>{clean_summary}</p>"
        f"<div class='obsidian-card-footer'>"
        f"<span class='time-ago-pill'>🕒 {ago}</span>"
        f"<span class='time-text muted-text'>{pub_at}</span>"
        f"<span class='source-pill'>{fav_html} {source}</span>"
        f"<span class='read-hint'>Read Story ↗</span>"
        f"</div>"
        f"</div>"
        f"</a>"
    )
    return card_html

def render_pulse_item(n):
    """Renders a compact pulse sidebar item as a single-line HTML string."""
    link          = safe_article_link(n)
    pub_ts        = n.get("pub_timestamp", 0)
    ago           = time_ago(pub_ts)
    is_new        = is_new_article(pub_ts)
    dot           = "<span class='pulse-new-dot'></span>" if is_new else ""
    raw_title     = str(n.get("title", "")).replace("\n", " ").strip()
    headline      = html_lib.escape(raw_title[:65] + ("..." if len(raw_title) > 65 else ""))
    player_name   = html_lib.escape(str(n.get("player_name", "")).strip())

    pulse_html = (
        f"<div class='pulse-item'>"
        f"<div class='pulse-time'>{dot}🕒 {ago}</div>"
        f"<a href='{link}' target='_blank' class='pulse-headline'>👤 {player_name} — {headline}</a>"
        f"</div>"
    )
    return pulse_html

# ── CSS Theme ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
        background-color: #07090E !important;
        color: #E2E8F0;
    }

    .stApp {
        background: radial-gradient(circle at 50% 8%, rgba(242, 101, 34, 0.08) 0%, rgba(7, 9, 14, 1) 90%);
    }

    section[data-testid="stSidebar"] {
        background-color: #0D101A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    .obsidian-title {
        font-family: 'Playfair Display', serif;
        font-size: 2.6rem;
        font-weight: 800;
        color: #FFFFFF;
        margin-bottom: 0.2rem;
        letter-spacing: -0.5px;
    }

    .obsidian-subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    /* Top Metric Pills Bar */
    .metric-bar { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.8rem; }
    .metric-pill {
        background: rgba(18, 22, 33, 0.85);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 0.75rem 1.4rem;
        display: flex;
        align-items: center;
        gap: 0.9rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    }
    .metric-icon {
        font-size: 1.4rem;
        background: rgba(242, 101, 34, 0.15);
        padding: 0.5rem;
        border-radius: 10px;
        color: #F26522;
    }
    .metric-val { font-size: 1.25rem; font-weight: 800; color: #FFFFFF; line-height: 1; }
    .metric-lbl { font-size: 0.8rem; color: #94A3B8; font-weight: 500; }

    /* Obsidian Glass Cards */
    a.obsidian-card-link { text-decoration: none !important; color: inherit !important; display: block; margin-bottom: 1.2rem; }
    .obsidian-card {
        background: rgba(18, 22, 33, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.09);
        border-radius: 16px;
        padding: 1.5rem 1.7rem;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        cursor: pointer;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45);
    }
    .obsidian-card:hover {
        transform: translateY(-3px);
        border-color: #F26522;
        background: rgba(24, 29, 44, 0.95);
        box-shadow: 0 12px 35px rgba(242, 101, 34, 0.25);
    }
    .obsidian-card:hover .obsidian-card-title { color: #FF8844 !important; }

    /* Badges */
    .card-tags { display: flex; gap: 0.6rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.8rem; }
    .badge-player { background: #F26522; color: #FFFFFF; padding: 4px 12px; border-radius: 20px; font-size: 0.84rem; font-weight: 700; box-shadow: 0 2px 10px rgba(242, 101, 34, 0.4); }
    .badge-squad  { background: #FFB703; color: #0F172A;  padding: 4px 12px; border-radius: 20px; font-size: 0.84rem; font-weight: 800; }
    .badge-league { background: #0284C7; color: #FFFFFF;  padding: 4px 12px; border-radius: 20px; font-size: 0.84rem; font-weight: 700; }

    .obsidian-card-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.35rem; font-weight: 700; color: #FFFFFF; margin: 0 0 0.6rem 0; line-height: 1.35; transition: color 0.2s ease; }
    .obsidian-card-desc  { color: #CBD5E1; font-size: 1.02rem; line-height: 1.6; margin: 0 0 1.1rem 0; font-weight: 400; }
    .obsidian-card-footer { display: flex; flex-wrap: wrap; align-items: center; gap: 0.8rem; font-size: 0.86rem; color: #94A3B8; border-top: 1px solid rgba(255, 255, 255, 0.07); padding-top: 0.9rem; }
    .source-pill { color: #38BDF8; font-weight: 700; background: rgba(56, 189, 248, 0.12); padding: 3px 10px; border-radius: 6px; border: 1px solid rgba(56, 189, 248, 0.3); }
    .time-text   { color: #E2E8F0; font-weight: 600; }
    .read-hint   { margin-left: auto; color: #F26522; font-weight: 700; font-size: 0.88rem; }

    /* NEW badge */
    .badge-new {
        background: linear-gradient(135deg, #EF4444, #DC2626);
        color: #FFFFFF;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.5px;
        animation: pulse-glow 1.8s ease-in-out infinite;
        box-shadow: 0 0 12px rgba(239, 68, 68, 0.6);
    }
    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 8px rgba(239, 68, 68, 0.5); }
        50%       { box-shadow: 0 0 20px rgba(239, 68, 68, 0.9); }
    }

    /* Time-ago pill */
    .time-ago-pill {
        background: rgba(242, 101, 34, 0.15);
        border: 1px solid rgba(242, 101, 34, 0.35);
        color: #FF8844;
        font-size: 0.82rem;
        font-weight: 700;
        padding: 2px 10px;
        border-radius: 8px;
    }
    .muted-text { color: #64748B !important; font-size: 0.78rem !important; }

    /* Source favicon */
    .source-fav {
        width: 14px;
        height: 14px;
        vertical-align: middle;
        border-radius: 3px;
        margin-right: 4px;
        display: inline-block;
    }

    /* Live Pulse Sidebar */
    .pulse-container { background: rgba(18, 22, 33, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 1.2rem; }
    .pulse-title { font-family: 'Playfair Display', serif; font-size: 1.25rem; font-weight: 700; color: #FFFFFF; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
    .pulse-dot { width: 8px; height: 8px; background-color: #F26522; border-radius: 50%; display: inline-block; box-shadow: 0 0 10px #F26522; }
    .pulse-new-dot { width: 7px; height: 7px; background: #EF4444; border-radius: 50%; display: inline-block; margin-right: 4px; box-shadow: 0 0 6px rgba(239,68,68,0.8); animation: pulse-glow 1.8s ease-in-out infinite; }
    .pulse-item { border-left: 2px solid rgba(242, 101, 34, 0.4); padding-left: 0.9rem; margin-bottom: 1rem; }
    .pulse-item:hover { border-left-color: #F26522; }
    .pulse-time { font-size: 0.78rem; color: #F26522; font-weight: 700; margin-bottom: 0.2rem; display: flex; align-items: center; gap: 0.3rem; }
    .pulse-headline { font-size: 0.92rem; color: #E2E8F0; font-weight: 600; line-height: 1.35; text-decoration: none; }
    .pulse-headline:hover { color: #FF8844; }

    @media (max-width: 992px) {
        .obsidian-title { font-size: 2.1rem; }
        .obsidian-card { padding: 1.1rem; }
    }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.markdown("# 🧡 @SRHXtra")
st.sidebar.markdown("**Obsidian Command Center V12.0**")
st.sidebar.markdown("📡 **System:** `Command Center`")
st.sidebar.markdown("👥 **Coverage:** `74 Players & 4 Squads`")
st.sidebar.markdown("---")
st.sidebar.markdown(f"🕒 **Last Refreshed IST:**\n`{st.session_state['last_refreshed']}`")
st.sidebar.markdown("---")

franchise_filter = st.sidebar.selectbox(
    "Filter Squad Domain",
    ["All", "Sunrisers Hyderabad", "Sunrisers Eastern Cape", "Sunrisers Leeds Men", "Sunrisers Leeds Women"]
)

# ── Live Refresh Button with 5-Minute Cooldown ────────────────────────────────
REFRESH_COOLDOWN_SECS = 300
seconds_since_last = time.time() - st.session_state["last_refresh_ts"]
cooldown_remaining = int(REFRESH_COOLDOWN_SECS - seconds_since_last)

if cooldown_remaining > 0:
    st.sidebar.button(
        f"⏳ Cooldown ({cooldown_remaining}s)",
        disabled=True,
        help=f"Live refresh available in {cooldown_remaining} seconds"
    )
else:
    if st.sidebar.button("⚡ Live Refresh 50 Feeds"):
        with st.spinner("Polling 50 top global cricket sources..."):
            result = fetch_and_filter_rss()
            st.session_state["last_refresh_ts"] = time.time()
            st.session_state["last_refreshed"] = format_ist_12hr()
            cached_get_recent_news.clear()
            cached_search_news.clear()
            inserted = getattr(result, "inserted", int(result))
            failed   = getattr(result, "failed_feeds", [])
            st.sidebar.success(f"✅ Captured {inserted} fresh Sunrisers items!")
            if failed:
                st.sidebar.warning(f"⚠️ {len(failed)} feeds unavailable: {', '.join(failed[:3])}{'…' if len(failed) > 3 else ''}")
        st.rerun()

# ── Dashboard Header ──────────────────────────────────────────────────────────
st.markdown("<div class='obsidian-title'>Premium Obsidian Command Center</div>", unsafe_allow_html=True)
st.markdown("<div class='obsidian-subtitle'>Real-Time Reconnaissance Hub | 74 Squad Members Across 4 Franchises</div>", unsafe_allow_html=True)

# ── KPI Metric Bar ────────────────────────────────────────────────────────────
live_count = len(cached_get_recent_news(limit=150))
st.markdown(f"""
<div class='metric-bar'>
    <div class='metric-pill'><div class='metric-icon'>📡</div><div><div class='metric-val'>50</div><div class='metric-lbl'>Global Feeds</div></div></div>
    <div class='metric-pill'><div class='metric-icon'>👥</div><div><div class='metric-val'>74</div><div class='metric-lbl'>Players Tracked</div></div></div>
    <div class='metric-pill'><div class='metric-icon'>🧡</div><div><div class='metric-val'>4</div><div class='metric-lbl'>Global Franchises</div></div></div>
    <div class='metric-pill'><div class='metric-icon'>📰</div><div><div class='metric-val'>{live_count}</div><div class='metric-lbl'>Live Articles</div></div></div>
    <div class='metric-pill'><div class='metric-icon'>⚡</div><div><div class='metric-val'>Live</div><div class='metric-lbl'>Auto Sync</div></div></div>
</div>
""", unsafe_allow_html=True)

# ── Navigation Tabs ───────────────────────────────────────────────────────────
tab_schedule, tab_news = st.tabs([
    "📋 MATCH DAY FIXTURE BREAKDOWN",
    f"📡 LIVE PULSE & NEWS RECON FEED ({live_count})",
])

# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: MATCH DAY FIXTURE BREAKDOWN (calendar grid removed, cards kept)
# ─────────────────────────────────────────────────────────────────────────────
with tab_schedule:
    st.subheader("📋 Full Match Day Breakdown & Player Roster (July / August 2026)")

    # Build a set of player names for the selected franchise for rich matching
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
            # Direct franchise name in squad
            if franchise_filter in s["squad"]:
                return True
            # Any player from this franchise mentioned in the players field
            if any(pname in s["players"] for pname in franchise_players):
                return True
            return False

        filtered_sched = [s for s in FIXTURE_SCHEDULE if _fixture_matches_filter(s)]
    else:
        filtered_sched = FIXTURE_SCHEDULE

    if filtered_sched:
        grouped_dates = {}
        for item in filtered_sched:
            grouped_dates.setdefault(item["date_str"], []).append(item)

        for date_str, items in grouped_dates.items():
            st.markdown(f"<h3 style='color:#F26522;margin-top:1.5rem;font-family:\"Plus Jakarta Sans\",sans-serif;'>📅 {date_str}</h3>", unsafe_allow_html=True)
            for item in items:
                match_card_html = (
                    f"<div class='obsidian-card' style='margin-bottom:1rem;'>"
                    f"<div class='card-tags'>"
                    f"<span class='badge-player'>⏰ {item['time']}</span>"
                    f"<span class='badge-squad'>{item['squad']}</span>"
                    f"<span class='badge-league'>🏏 {item['league']}</span>"
                    f"</div>"
                    f"<h3 style='margin:0.4rem 0;color:#FFFFFF;font-size:1.35rem;font-family:\"Plus Jakarta Sans\",sans-serif;'>vs {item['vs']}</h3>"
                    f"<p style='color:#CBD5E1;margin-bottom:0.2rem;font-size:1.02rem;'><strong>Squad Players:</strong> {item['players']}</p>"
                    f"</div>"
                )
                st.markdown(match_card_html, unsafe_allow_html=True)
    else:
        st.info(f"No fixtures found for **{franchise_filter}**. Try selecting 'All' to see every franchise.")

# ─────────────────────────────────────────────────────────────────────────────
# TAB 2: LIVE PULSE & NEWS RECON FEED
# ─────────────────────────────────────────────────────────────────────────────
with tab_news:
    st.subheader("📡 Live Pulse & News Feed (Click Any Card to Open Original Article)")

    search_query = st.text_input(
        "🔍 Search player, team or keyword",
        placeholder="e.g. Abhishek Sharma, injury, The Hundred...",
        label_visibility="collapsed",
    )

    if search_query.strip():
        news_list = cached_search_news(search_query.strip())
        st.caption(f"🔍 Showing **{len(news_list)}** results for *\"{search_query}\"*")
    else:
        news_list = cached_get_recent_news(limit=150)

    if franchise_filter != "All":
        news_list = [n for n in news_list if n["franchise"] == franchise_filter]

    news_list = sorted(news_list, key=get_bulletproof_sort_key, reverse=True)

    if news_list:
        col_main, col_pulse = st.columns([2.2, 1])

        with col_main:
            for n in news_list:
                st.markdown(render_news_card(n), unsafe_allow_html=True)

        with col_pulse:
            st.markdown("""
            <div class='pulse-container'>
                <div class='pulse-title'><span class='pulse-dot'></span> Live Pulse Timeline</div>
            """, unsafe_allow_html=True)

            for n in news_list[:8]:
                st.markdown(render_pulse_item(n), unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
    else:
        if search_query.strip():
            st.info(f"No results found for \"{search_query}\". Try a different player name or keyword.")
        else:
            st.info("No player or franchise updates in the last 24 hours. Click '⚡ Live Refresh 50 Feeds' in the sidebar to scan all sources now!")
