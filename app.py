"""
@SRHXtra Premium Obsidian Command Center (V9.0 - Bulletproof Single-Block CSS Calendar Grid).
Section 1: 30-Day Obsidian Calendar Grid built with native single-block CSS grid (No Streamlit HTML breaks).
Section 2: Live Pulse News Portal (Exact Raw Headlines | Direct Source Redirection | Strict 24h Expiry).
"""

import os
import sys
import urllib.parse
from datetime import datetime

# Ensure root directory is at the top of sys.path for Streamlit Cloud
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from config.roster import MASTER_ROSTER
from database.db_manager import init_db, get_recent_news, search_news, purge_expired_24h_news
from utils.time_utils import format_ist_12hr

try:
    from scrapers.rss_collector import fetch_and_filter_rss, TOP_50_CRICKET_SOURCES
except Exception:
    def fetch_and_filter_rss():
        return 0

# Page Configuration
st.set_page_config(
    page_title="@SRHXtra Premium Obsidian Command Center",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database & Purge Expired >24h Articles
init_db()
purge_expired_24h_news()

# Clean 30-Minute JavaScript Timer (1,800,000 ms = 30 mins, NO 5-second loop)
components.html(
    """
    <script>
        setTimeout(function(){
            window.parent.location.reload();
        }, 1800000);
    </script>
    """,
    height=0,
    width=0
)

# Session State for Last Refreshed IST Timestamp
if "last_refreshed" not in st.session_state:
    st.session_state["last_refreshed"] = format_ist_12hr()

# Auto-ingest fresh live RSS if database has < 3 fresh items in last 24h
current_news = get_recent_news(limit=100)
if len(current_news) < 3:
    fetch_and_filter_rss()
    st.session_state["last_refreshed"] = format_ist_12hr()

def get_bulletproof_sort_key(n):
    """Returns float timestamp for 100% reliable latest-first sorting."""
    ts = n.get("pub_timestamp")
    if ts and isinstance(ts, (int, float)) and ts > 0:
        return ts
    pub_str = str(n.get("published_at", ""))
    try:
        dt = datetime.strptime(pub_str, "%b %d, %Y @ %I:%M %p IST")
        return dt.timestamp()
    except Exception:
        return 0.0

def detect_league_badge(title, summary):
    """Detects league for badge display (The Hundred, SA20, IPL, International)."""
    text = (str(title) + " " + str(summary)).lower()
    if any(k in text for k in ["the hundred", "hundred", "london spirit", "super giants", "welsh fire", "trent rockets", "southern brave"]):
        return "The Hundred"
    elif any(k in text for k in ["sa20", "sunrisers eastern cape", "pretoria capitals", "paarl royals"]):
        return "SA20"
    elif any(k in text for k in ["ipl", "indian premier league", "sunrisers hyderabad"]):
        return "IPL"
    elif any(k in text for k in ["t20i", "odi", "test", "india tour", "world cup", "wtc"]):
        return "International Cricket"
    else:
        return "Global Cricket"

# Premium Obsidian Dark Theme & Native CSS Grid
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
    .metric-bar {
        display: flex;
        gap: 1rem;
        flex-wrap: wrap;
        margin-bottom: 1.8rem;
    }

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

    .metric-val {
        font-size: 1.25rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1;
    }

    .metric-lbl {
        font-size: 0.8rem;
        color: #94A3B8;
        font-weight: 500;
    }

    /* Single-Block Native Obsidian Calendar Grid */
    .obsidian-calendar-grid {
        display: grid;
        grid-template-columns: repeat(7, 1fr);
        gap: 10px;
        margin-bottom: 2rem;
    }

    .cal-day-header {
        text-align: center;
        font-weight: 700;
        color: #94A3B8;
        font-size: 0.85rem;
        padding: 8px 0;
        background: rgba(18, 22, 33, 0.9);
        border-radius: 8px;
        letter-spacing: 1px;
    }

    .cal-cell {
        background: rgba(18, 22, 33, 0.65);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 0.75rem;
        min-height: 120px;
        transition: all 0.2s ease;
    }

    .cal-cell.has-match {
        border-color: rgba(242, 101, 34, 0.45);
        background: radial-gradient(circle at top right, rgba(242, 101, 34, 0.15) 0%, rgba(18, 22, 33, 0.85) 85%);
    }

    .cal-num {
        font-family: 'Playfair Display', serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: #64748B;
        margin-bottom: 0.4rem;
    }

    .cal-num.active-num {
        color: #FFFFFF;
    }

    .cal-match-item {
        background: rgba(10, 13, 20, 0.9);
        border: 1px solid rgba(242, 101, 34, 0.5);
        border-radius: 8px;
        padding: 5px 7px;
        margin-bottom: 5px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
    }

    .cal-teams {
        font-size: 0.78rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.2;
        margin-bottom: 2px;
    }

    .cal-time {
        font-size: 0.7rem;
        color: #FF8844;
        font-weight: 700;
    }

    /* Obsidian Glass Cards */
    a.obsidian-card-link {
        text-decoration: none !important;
        color: inherit !important;
        display: block;
        margin-bottom: 1.2rem;
    }

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

    .obsidian-card:hover .obsidian-card-title {
        color: #FF8844 !important;
    }

    /* Badges */
    .card-tags {
        display: flex;
        gap: 0.6rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.8rem;
    }

    .badge-player {
        background: #F26522;
        color: #FFFFFF;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.84rem;
        font-weight: 700;
        box-shadow: 0 2px 10px rgba(242, 101, 34, 0.4);
    }

    .badge-squad {
        background: #FFB703;
        color: #0F172A;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.84rem;
        font-weight: 800;
    }

    .badge-league {
        background: #0284C7;
        color: #FFFFFF;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.84rem;
        font-weight: 700;
    }

    .obsidian-card-title {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0 0 0.6rem 0;
        line-height: 1.35;
        transition: color 0.2s ease;
    }

    .obsidian-card-desc {
        color: #CBD5E1;
        font-size: 1.02rem;
        line-height: 1.6;
        margin: 0 0 1.1rem 0;
        font-weight: 400;
    }

    .obsidian-card-footer {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.8rem;
        font-size: 0.86rem;
        color: #94A3B8;
        border-top: 1px solid rgba(255, 255, 255, 0.07);
        padding-top: 0.9rem;
    }

    .source-pill {
        color: #38BDF8;
        font-weight: 700;
        background: rgba(56, 189, 248, 0.12);
        padding: 3px 10px;
        border-radius: 6px;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }

    .time-text {
        color: #E2E8F0;
        font-weight: 600;
    }

    .read-hint {
        margin-left: auto;
        color: #F26522;
        font-weight: 700;
        font-size: 0.88rem;
    }

    /* Live Pulse Right Sidebar */
    .pulse-container {
        background: rgba(18, 22, 33, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 1.2rem;
    }

    .pulse-title {
        font-family: 'Playfair Display', serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #F26522;
        border-radius: 50%;
        display: inline-block;
        box-shadow: 0 0 10px #F26522;
    }

    .pulse-item {
        border-left: 2px solid rgba(242, 101, 34, 0.4);
        padding-left: 0.9rem;
        margin-bottom: 1rem;
    }

    .pulse-item:hover {
        border-left-color: #F26522;
    }

    .pulse-time {
        font-size: 0.78rem;
        color: #F26522;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }

    .pulse-headline {
        font-size: 0.92rem;
        color: #E2E8F0;
        font-weight: 600;
        line-height: 1.35;
        text-decoration: none;
    }

    .pulse-headline:hover {
        color: #FF8844;
    }

    @media (max-width: 992px) {
        .obsidian-title { font-size: 2.1rem; }
        .obsidian-card { padding: 1.1rem; }
        .obsidian-calendar-grid { grid-template-columns: repeat(4, 1fr); }
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("# 🧡 @SRHXtra")
st.sidebar.markdown("**Obsidian Calendar V9.0**")
st.sidebar.markdown("📡 **System:** `Command Center`")
st.sidebar.markdown("🗓️ **Calendar:** `Obsidian Native Matrix`")
st.sidebar.markdown("👥 **Coverage:** `73 Players & 4 Squads`")

st.sidebar.markdown("---")
st.sidebar.markdown(f"🕒 **Last Refreshed IST:**\n`{st.session_state['last_refreshed']}`")

st.sidebar.markdown("---")
franchise_filter = st.sidebar.selectbox(
    "Filter Squad Domain",
    ["All", "Sunrisers Hyderabad", "Sunrisers Eastern Cape", "Sunrisers Leeds Men", "Sunrisers Leeds Women"]
)

if st.sidebar.button("⚡ Live Refresh 50 Feeds"):
    with st.spinner("Polling 50 top global cricket sources..."):
        count = fetch_and_filter_rss()
        st.session_state["last_refreshed"] = format_ist_12hr()
        st.sidebar.success(f"Captured {count} fresh 24h Sunrisers items!")
        st.rerun()

# Dashboard Brand Header
st.markdown("<div class='obsidian-title'>Premium Obsidian Command Center</div>", unsafe_allow_html=True)
st.markdown("<div class='obsidian-subtitle'>Real-Time Reconnaissance Hub & Obsidian Calendar Matrix | 73 Squad Members Across 4 Franchises</div>", unsafe_allow_html=True)

# Top KPI Metric Bar
st.markdown(f"""
<div class='metric-bar'>
    <div class='metric-pill'>
        <div class='metric-icon'>📡</div>
        <div>
            <div class='metric-val'>50</div>
            <div class='metric-lbl'>Global Feeds</div>
        </div>
    </div>
    <div class='metric-pill'>
        <div class='metric-icon'>📅</div>
        <div>
            <div class='metric-val'>30-Day</div>
            <div class='metric-lbl'>Calendar Matrix</div>
        </div>
    </div>
    <div class='metric-pill'>
        <div class='metric-icon'>👥</div>
        <div>
            <div class='metric-val'>73</div>
            <div class='metric-lbl'>Players Tracked</div>
        </div>
    </div>
    <div class='metric-pill'>
        <div class='metric-icon'>🧡</div>
        <div>
            <div class='metric-val'>4</div>
            <div class='metric-lbl'>Global Franchises</div>
        </div>
    </div>
    <div class='metric-pill'>
        <div class='metric-icon'>⚡</div>
        <div>
            <div class='metric-val'>Live</div>
            <div class='metric-lbl'>Auto Sync</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main Navigation Tabs
tab_schedule, tab_news = st.tabs([
    "🗓️ OBSIDIAN MONTH CALENDAR GRID (30-DAY FIXTURE MATRIX)",
    "📡 LIVE PULSE & NEWS RECON FEED"
])

# ---------------------------------------------------------
# TAB 1: OBSIDIAN MONTH CALENDAR GRID (SINGLE-BLOCK CSS MATRIX)
# ---------------------------------------------------------
with tab_schedule:
    st.subheader("🗓️ Obsidian Month Fixture Grid (July / August 2026)")
    
    raw_schedules = [
        {"date_num": 25, "month": "July 2026", "date_str": "July 25, 2026", "day_name": "Sat", "time": "03:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson (C), Phoebe Litchfield, Deepti Sharma & Squad", "vs": "Southern Brave Women", "league": "The Hundred Women"},
        {"date_num": 25, "month": "July 2026", "date_str": "July 25, 2026", "day_name": "Sat", "time": "04:30 PM IST", "squad": "Sunrisers Hyderabad", "players": "Abhishek Sharma, Ishan Kishan, Harsh Dubey", "vs": "Zimbabwe", "league": "India Tour of Zimbabwe - 2nd T20I"},
        {"date_num": 25, "month": "July 2026", "date_str": "July 25, 2026", "day_name": "Sat", "time": "07:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Zak Crawley (C), Harry Brook, Mitchell Marsh & Squad", "vs": "Southern Brave Men", "league": "The Hundred Men"},
        
        {"date_num": 26, "month": "July 2026", "date_str": "July 26, 2026", "day_name": "Sun", "time": "04:30 PM IST", "squad": "Sunrisers Hyderabad", "players": "Abhishek Sharma, Ishan Kishan, Harsh Dubey", "vs": "Zimbabwe", "league": "India Tour of Zimbabwe - 3rd T20I"},
        {"date_num": 26, "month": "July 2026", "date_str": "July 26, 2026", "day_name": "Sun", "time": "10:30 PM IST", "squad": "SRH & SEC Stars", "players": "Heinrich Klaasen, Jonny Bairstow, Liam Livingstone", "vs": "Trent Rockets", "league": "The Hundred Men"},
        
        {"date_num": 27, "month": "July 2026", "date_str": "July 27, 2026", "day_name": "Mon", "time": "11:00 PM IST", "squad": "Sunrisers Eastern Cape", "players": "Quinton de Kock vs Tristan Stubbs, Marco Jansen", "vs": "MI London vs Southern Brave", "league": "The Hundred Men"},
        
        {"date_num": 28, "month": "July 2026", "date_str": "July 28, 2026", "day_name": "Tue", "time": "07:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson, Phoebe Litchfield, Deepti Sharma", "vs": "Manchester Super Giants Women", "league": "The Hundred Women"},
        {"date_num": 28, "month": "July 2026", "date_str": "July 28, 2026", "day_name": "Tue", "time": "11:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Harry Brook, Mitchell Marsh, Brydon Carse", "vs": "Manchester Super Giants Men", "league": "The Hundred Men"},
        
        {"date_num": 29, "month": "July 2026", "date_str": "July 29, 2026", "day_name": "Wed", "time": "11:00 PM IST", "squad": "SRH & SEC Stars", "players": "Heinrich Klaasen, Jonny Bairstow vs Tristan Stubbs", "vs": "London Spirit vs MI London", "league": "The Hundred Men"},
        
        {"date_num": 1, "month": "August 2026", "date_str": "August 01, 2026", "day_name": "Sat", "time": "07:00 PM IST", "squad": "SRH & SEC Stars", "players": "Heinrich Klaasen vs Quinton de Kock", "vs": "London Spirit vs Southern Brave", "league": "The Hundred Men"},
        
        {"date_num": 2, "month": "August 2026", "date_str": "August 02, 2026", "day_name": "Sun", "time": "03:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Phoebe Litchfield, Deepti Sharma & Squad", "vs": "Trent Rockets Women", "league": "The Hundred Women"},
        {"date_num": 2, "month": "August 2026", "date_str": "August 02, 2026", "day_name": "Sun", "time": "07:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Mitchell Marsh, Brydon Carse & Squad", "vs": "Trent Rockets Men", "league": "The Hundred Men"},
        
        {"date_num": 4, "month": "August 2026", "date_str": "August 04, 2026", "day_name": "Tue", "time": "07:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson, Phoebe Litchfield & Squad", "vs": "London Spirit Women", "league": "The Hundred Women"},
        {"date_num": 4, "month": "August 2026", "date_str": "August 04, 2026", "day_name": "Tue", "time": "11:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Brydon Carse vs Heinrich Klaasen, Jonny Bairstow", "vs": "London Spirit", "league": "The Hundred Men"},
        
        {"date_num": 7, "month": "August 2026", "date_str": "August 07, 2026", "day_name": "Fri", "time": "07:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Phoebe Litchfield, Deepti Sharma & Squad", "vs": "Welsh Fire Women", "league": "The Hundred Women"},
        {"date_num": 7, "month": "August 2026", "date_str": "August 07, 2026", "day_name": "Fri", "time": "11:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Harry Brook, Mitchell Marsh & Squad", "vs": "Welsh Fire Men", "league": "The Hundred Men"},
        
        {"date_num": 9, "month": "August 2026", "date_str": "August 09, 2026", "day_name": "Sun", "time": "03:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson, Phoebe Litchfield & Squad", "vs": "Birmingham Phoenix Women", "league": "The Hundred Women"},
        {"date_num": 9, "month": "August 2026", "date_str": "August 09, 2026", "day_name": "Sun", "time": "07:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Harry Brook, Mitchell Marsh & Squad", "vs": "Birmingham Phoenix Men", "league": "The Hundred Men"},
        
        {"date_num": 12, "month": "August 2026", "date_str": "August 12, 2026", "day_name": "Wed", "time": "07:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Phoebe Litchfield, Deepti Sharma & Squad", "vs": "MI London Women", "league": "The Hundred Women"},
        {"date_num": 12, "month": "August 2026", "date_str": "August 12, 2026", "day_name": "Wed", "time": "11:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Harry Brook, Mitchell Marsh vs Tristan Stubbs", "vs": "MI London Men", "league": "The Hundred Men"},
        
        {"date_num": 15, "month": "August 2026", "date_str": "August 15, 2026", "day_name": "Sat", "time": "10:00 AM IST", "squad": "Sri Lanka & India Tests", "players": "Kamindu Mendis vs Ishan Kishan, Mohammed Shami", "vs": "India vs Sri Lanka (1st Test)", "league": "ICC World Test Championship"},
        
        {"date_num": 16, "month": "August 2026", "date_str": "August 16, 2026", "day_name": "Sun", "time": "06:45 PM IST", "squad": "The Hundred Finals", "players": "Sunrisers Leeds / SEC / SRH Stars", "vs": "The Hundred Men & Women Finals", "league": "The Hundred Final"}
    ]

    # Filter Domain
    if franchise_filter != "All":
        filtered_sched = [s for s in raw_schedules if franchise_filter in s["squad"] or franchise_filter in s["players"] or "SRH" in s["squad"]]
    else:
        filtered_sched = raw_schedules

    # 35-Day Calendar Grid Representation (July 25 to August 2026)
    grid_dates = [
        {"num": 25, "month": "Jul", "day": "Sat", "matches": [m for m in filtered_sched if m["date_num"] == 25 and "July" in m["month"]]},
        {"num": 26, "month": "Jul", "day": "Sun", "matches": [m for m in filtered_sched if m["date_num"] == 26 and "July" in m["month"]]},
        {"num": 27, "month": "Jul", "day": "Mon", "matches": [m for m in filtered_sched if m["date_num"] == 27 and "July" in m["month"]]},
        {"num": 28, "month": "Jul", "day": "Tue", "matches": [m for m in filtered_sched if m["date_num"] == 28 and "July" in m["month"]]},
        {"num": 29, "month": "Jul", "day": "Wed", "matches": [m for m in filtered_sched if m["date_num"] == 29 and "July" in m["month"]]},
        {"num": 30, "month": "Jul", "day": "Thu", "matches": []},
        {"num": 31, "month": "Jul", "day": "Fri", "matches": []},
        {"num": 1, "month": "Aug", "day": "Sat", "matches": [m for m in filtered_sched if m["date_num"] == 1 and "August" in m["month"]]},
        {"num": 2, "month": "Aug", "day": "Sun", "matches": [m for m in filtered_sched if m["date_num"] == 2 and "August" in m["month"]]},
        {"num": 3, "month": "Aug", "day": "Mon", "matches": []},
        {"num": 4, "month": "Aug", "day": "Tue", "matches": [m for m in filtered_sched if m["date_num"] == 4 and "August" in m["month"]]},
        {"num": 5, "month": "Aug", "day": "Wed", "matches": []},
        {"num": 6, "month": "Aug", "day": "Thu", "matches": []},
        {"num": 7, "month": "Aug", "day": "Fri", "matches": [m for m in filtered_sched if m["date_num"] == 7 and "August" in m["month"]]},
        {"num": 8, "month": "Aug", "day": "Sat", "matches": []},
        {"num": 9, "month": "Aug", "day": "Sun", "matches": [m for m in filtered_sched if m["date_num"] == 9 and "August" in m["month"]]},
        {"num": 10, "month": "Aug", "day": "Mon", "matches": []},
        {"num": 11, "month": "Aug", "day": "Tue", "matches": []},
        {"num": 12, "month": "Aug", "day": "Wed", "matches": [m for m in filtered_sched if m["date_num"] == 12 and "August" in m["month"]]},
        {"num": 13, "month": "Aug", "day": "Thu", "matches": []},
        {"num": 14, "month": "Aug", "day": "Fri", "matches": []},
        {"num": 15, "month": "Aug", "day": "Sat", "matches": [m for m in filtered_sched if m["date_num"] == 15 and "August" in m["month"]]},
        {"num": 16, "month": "Aug", "day": "Sun", "matches": [m for m in filtered_sched if m["date_num"] == 16 and "August" in m["month"]]}
    ]

    # Build 100% Valid Single HTML Grid String (Prevents Streamlit HTML Column Escaping)
    grid_html_parts = [
        "<div class='obsidian-calendar-grid'>",
        "<div class='cal-day-header'>SUN</div>",
        "<div class='cal-day-header'>MON</div>",
        "<div class='cal-day-header'>TUE</div>",
        "<div class='cal-day-header'>WED</div>",
        "<div class='cal-day-header'>THU</div>",
        "<div class='cal-day-header'>FRI</div>",
        "<div class='cal-day-header'>SAT</div>"
    ]

    for item in grid_dates:
        has_matches = len(item["matches"]) > 0
        cell_cls = "cal-cell has-match" if has_matches else "cal-cell"
        num_cls = "cal-num active-num" if has_matches else "cal-num"
        
        matches_html_str = ""
        for m in item["matches"][:2]:
            matches_html_str += f"""
            <div class='cal-match-item'>
                <div class='cal-teams'>vs {m['vs'].split(' ')[0]}</div>
                <div class='cal-time'>⏰ {m['time'].split(' ')[0]}</div>
            </div>
            """

        grid_html_parts.append(f"""
        <div class='{cell_cls}'>
            <div class='{num_cls}'>{item['num']} <small style='font-size:0.72rem; color:#94A3B8;'>{item['month']}</small></div>
            {matches_html_str}
        </div>
        """)

    grid_html_parts.append("</div>")
    full_grid_html = "".join(grid_html_parts)
    
    st.markdown(full_grid_html, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📋 Full Match Day Breakdown & Player Roster")
    
    # Detailed Day Breakdown Cards
    grouped_dates = {}
    for item in filtered_sched:
        d = item["date_str"]
        if d not in grouped_dates:
            grouped_dates[d] = []
        grouped_dates[d].append(item)

    for date_str, items in grouped_dates.items():
        st.markdown(f"<div class='date-header'>📅 {date_str}</div>", unsafe_allow_html=True)
        for item in items:
            st.markdown(f"""
            <div class='obsidian-card'>
                <div class='card-tags'>
                    <span class='badge-player'>⏰ {item['time']}</span>
                    <span class='badge-squad'>{item['squad']}</span>
                    <span class='badge-league'>🏏 {item['league']}</span>
                </div>
                <h3 style='margin: 0.4rem 0; color: #FFFFFF; font-size: 1.35rem; font-family: "Plus Jakarta Sans", sans-serif;'>vs {item['vs']}</h3>
                <p style='color: #CBD5E1; margin-bottom: 0.2rem; font-size: 1.02rem;'><strong>Squad Players:</strong> {item['players']}</p>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2: LIVE PULSE & NEWS RECON FEED (2-COLUMN DASHBOARD)
# ---------------------------------------------------------
with tab_news:
    st.subheader("📡 Live Pulse & News Feed (Click Any Card to Open Original Article)")
    
    news_list = get_recent_news(limit=150)
    
    # Filter Domain for News
    if franchise_filter != "All":
        news_list = [n for n in news_list if n["franchise"] == franchise_filter]

    # Explicit Bulletproof Sorting by Datetime / Float Epoch (Latest First)
    news_list = sorted(news_list, key=get_bulletproof_sort_key, reverse=True)

    if news_list:
        col_main, col_pulse = st.columns([2.2, 1])
        
        # Left Main Feed Column
        with col_main:
            for n in news_list:
                article_link = n['link'] if n['link'] and n['link'] != "#" else f"https://news.google.com/search?q={urllib.parse.quote(n['player_name'] + ' cricket')}"
                league_context = detect_league_badge(n['title'], n['summary'])

                st.markdown(f"""
                <a href='{article_link}' target='_blank' class='obsidian-card-link'>
                    <div class='obsidian-card'>
                        <div class='card-tags'>
                            <span class='badge-player'>👤 {n['player_name']}</span>
                            <span class='badge-squad'>🧡 {n['franchise']} Squad</span>
                            <span class='badge-league'>🏏 {league_context}</span>
                        </div>
                        <h2 class='obsidian-card-title'>{n['title']}</h2>
                        <p class='obsidian-card-desc'>{n['summary']}</p>
                        <div class='obsidian-card-footer'>
                            <span class='time-text'>📅 {n['published_at']}</span>
                            <span class='source-pill'>🔗 {n['source']}</span>
                            <span class='read-hint'>Read Story ↗</span>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)

        # Right "Live Pulse 🔴" Column
        with col_pulse:
            st.markdown("""
            <div class='pulse-container'>
                <div class='pulse-title'><span class='pulse-dot'></span> Live Pulse Timeline</div>
            """, unsafe_allow_html=True)
            
            for n in news_list[:8]:
                article_link = n['link'] if n['link'] and n['link'] != "#" else f"https://news.google.com/search?q={urllib.parse.quote(n['player_name'] + ' cricket')}"
                st.markdown(f"""
                <div class='pulse-item'>
                    <div class='pulse-time'>🕒 {n['published_at'].split('@')[-1].strip() if '@' in n['published_at'] else n['published_at']}</div>
                    <a href='{article_link}' target='_blank' class='pulse-headline'>
                        👤 {n['player_name']} — {n['title'][:70]}...
                    </a>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("No player or franchise updates reported in the last 24 hours. Click 'Live Refresh 50 Feeds' in the sidebar to scan all 50 global outlets now!")
