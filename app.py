"""
@SRHXtra Global Command Center Dashboard (V5.1 - ESPNcricinfo Live News Portal UI).
Section 1: 30-Day Global Schedule Grouped by Date (12-hr AM/PM IST).
Section 2: Live ESPNcricinfo-Style News Cards with Tournament Context & Direct Redirection.
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
from agents.ranker import detect_league_context

try:
    from scrapers.rss_collector import fetch_and_filter_rss, TOP_50_CRICKET_SOURCES
except Exception:
    def fetch_and_filter_rss():
        return 0

# Page Configuration
st.set_page_config(
    page_title="@SRHXtra Global Command Center",
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
    """
    Returns float timestamp for 100% reliable latest-first sorting.
    Tries pub_timestamp first, then parses published_at string ("Jul 24, 2026 @ 09:07 AM IST").
    """
    ts = n.get("pub_timestamp")
    if ts and isinstance(ts, (int, float)) and ts > 0:
        return ts
    pub_str = str(n.get("published_at", ""))
    try:
        dt = datetime.strptime(pub_str, "%b %d, %Y @ %I:%M %p IST")
        return dt.timestamp()
    except Exception:
        return 0.0

# Premium ESPNcricinfo Dark Portal CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&family=Outfit:wght@600;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0B0C10;
        color: #E2E8F0;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(242, 101, 34, 0.06) 0%, rgba(11, 12, 16, 1) 90%);
    }

    section[data-testid="stSidebar"] {
        background-color: #12131C !important;
        border-right: 1px solid rgba(242, 101, 34, 0.25);
    }
    
    .brand-title {
        background: linear-gradient(135deg, #FF6B00 0%, #FFA800 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif;
        font-size: 2.8rem;
        font-weight: 900;
        margin-bottom: 0.2rem;
        line-height: 1.1;
    }
    
    .brand-subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    .date-header {
        background: linear-gradient(90deg, rgba(242, 101, 34, 0.2) 0%, rgba(18, 19, 28, 0.8) 100%);
        border-left: 4px solid #F26522;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        font-weight: 800;
        font-size: 1.3rem;
        color: #FF8844;
    }

    /* ESPNcricinfo Style News Card Link Wrapper */
    a.cricinfo-card-link {
        text-decoration: none !important;
        color: inherit !important;
        display: block;
        margin-bottom: 1.2rem;
    }

    /* ESPNcricinfo Style Card Container */
    .cricinfo-news-card {
        background: #141622;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 1.4rem 1.6rem;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        cursor: pointer;
        position: relative;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }

    .cricinfo-news-card:hover {
        transform: translateY(-3px);
        border-color: rgba(242, 101, 34, 0.6);
        background: #191C2C;
        box-shadow: 0 10px 30px rgba(242, 101, 34, 0.15);
    }

    .cricinfo-news-card:hover .cricinfo-title {
        color: #FF8844 !important;
    }

    /* Priority Card Accent */
    .cricinfo-news-card.priority-card {
        border-left: 5px solid #FF3D00;
        background: linear-gradient(135deg, rgba(35, 18, 15, 0.9) 0%, rgba(20, 12, 10, 0.95) 100%);
    }

    /* Header Tags */
    .card-meta-top {
        display: flex;
        gap: 0.6rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.6rem;
    }

    .player-tag {
        background: rgba(242, 101, 34, 0.15);
        color: #FF8844;
        border: 1px solid rgba(242, 101, 34, 0.3);
        padding: 3px 10px;
        border-radius: 16px;
        font-size: 0.82rem;
        font-weight: 700;
    }

    .franchise-tag {
        background: rgba(255, 215, 0, 0.12);
        color: #FFD700;
        border: 1px solid rgba(255, 215, 0, 0.25);
        padding: 3px 10px;
        border-radius: 16px;
        font-size: 0.82rem;
        font-weight: 700;
    }

    .league-tag {
        background: rgba(56, 189, 248, 0.12);
        color: #38BDF8;
        border: 1px solid rgba(56, 189, 248, 0.25);
        padding: 3px 10px;
        border-radius: 16px;
        font-size: 0.82rem;
        font-weight: 700;
    }

    /* Main Headline */
    .cricinfo-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: #F8FAFC;
        margin: 0 0 0.5rem 0;
        line-height: 1.35;
        transition: color 0.2s ease;
    }

    /* Summary Sub-headline */
    .cricinfo-summary {
        color: #94A3B8;
        font-size: 0.98rem;
        line-height: 1.55;
        margin: 0 0 1rem 0;
        font-weight: 400;
    }

    /* Footer Metadata Line */
    .cricinfo-footer {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.7rem;
        font-size: 0.83rem;
        color: #64748B;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        padding-top: 0.8rem;
    }

    .source-badge {
        color: #38BDF8;
        font-weight: 600;
    }

    .pub-time {
        color: #A1A1AA;
        font-weight: 500;
    }

    .bullet {
        color: #475569;
    }

    .redirect-hint {
        margin-left: auto;
        color: #F97316;
        font-weight: 600;
        font-size: 0.82rem;
    }

    @media (max-width: 768px) {
        .brand-title { font-size: 2.1rem; }
        .cricinfo-news-card { padding: 1rem; }
        .cricinfo-title { font-size: 1.15rem; }
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("# 🧡 @SRHXtra")
st.sidebar.markdown("**Global Command Center V5.1**")
st.sidebar.markdown(f"📡 **UI:** `ESPNcricinfo Direct On-Click Feed`")
st.sidebar.markdown(f"👥 **Targets:** `73 Players & 4 Squads`")
st.sidebar.markdown(f"⏱️ **Expiry:** `Strict Last 24 Hours`")

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
st.markdown("<div class='brand-title'>🦅 @SRHXtra GLOBAL TRACKER</div>", unsafe_allow_html=True)
st.markdown("<div class='brand-subtitle'>ESPNcricinfo Live News Portal | Click Any Article to Open Original Story | Strictly Last 24 Hours</div>", unsafe_allow_html=True)

# Main Navigation Tabs
tab_schedule, tab_news = st.tabs([
    "🗓️ SECTION 1: 30-DAY GLOBAL SCHEDULE (GROUPED BY DATE)",
    "📰 SECTION 2: LIVE CRICKET NEWS PORTAL (ON-CLICK REDIRECT)"
])

# ---------------------------------------------------------
# SECTION 1: 30-DAY GLOBAL SCHEDULE (GROUPED BY DATE IN 12-HR IST)
# ---------------------------------------------------------
with tab_schedule:
    st.subheader("🗓️ 30-Day Fixture Calendar (Grouped by Date | Timings in 12-Hour AM/PM IST)")
    
    raw_schedules = [
        # July 25, 2026
        {"date": "July 25, 2026", "time": "03:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson (C), Phoebe Litchfield, Deepti Sharma, Annabel Sutherland, Bryony Smith, Flo Miller, Lauren Winfield-Hill & Squad", "vs": "Southern Brave Women", "league": "The Hundred Women"},
        {"date": "July 25, 2026", "time": "04:30 PM IST", "squad": "Sunrisers Hyderabad (India)", "players": "Abhishek Sharma, Ishan Kishan, Harsh Dubey", "vs": "Zimbabwe", "league": "India Tour of Zimbabwe - 2nd T20I"},
        {"date": "July 25, 2026", "time": "07:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Zak Crawley (C), Harry Brook, Mitchell Marsh, Brydon Carse, Ryan Rickelton, Reece Topley & Squad", "vs": "Southern Brave Men", "league": "The Hundred Men"},
        {"date": "July 25, 2026", "time": "07:00 PM IST", "squad": "Sunrisers Eastern Cape", "players": "Quinton de Kock, James Coles (Southern Brave)", "vs": "Sunrisers Leeds Men", "league": "The Hundred Men"},
        {"date": "July 25, 2026", "time": "10:30 PM IST", "squad": "Sunrisers Eastern Cape", "players": "Tristan Stubbs (C), Marco Jansen (MI London)", "vs": "Welsh Fire", "league": "The Hundred Men"},
        
        # July 26, 2026
        {"date": "July 26, 2026", "time": "04:30 PM IST", "squad": "Sunrisers Hyderabad (India)", "players": "Abhishek Sharma, Ishan Kishan, Harsh Dubey", "vs": "Zimbabwe", "league": "India Tour of Zimbabwe - 3rd T20I"},
        {"date": "July 26, 2026", "time": "10:30 PM IST", "squad": "SRH & SEC Stars", "players": "Heinrich Klaasen (SRH), Jonny Bairstow (SEC), Liam Livingstone (SRH)", "vs": "Trent Rockets", "league": "The Hundred Men"},
        
        # July 27, 2026
        {"date": "July 27, 2026", "time": "11:00 PM IST", "squad": "Sunrisers Eastern Cape Showcase", "players": "Quinton de Kock, James Coles vs Tristan Stubbs, Marco Jansen", "vs": "MI London vs Southern Brave", "league": "The Hundred Men"},
        
        # July 28, 2026
        {"date": "July 28, 2026", "time": "07:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson, Phoebe Litchfield, Deepti Sharma & Squad", "vs": "Manchester Super Giants Women", "league": "The Hundred Women"},
        {"date": "July 28, 2026", "time": "11:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Harry Brook, Mitchell Marsh, Brydon Carse & Squad", "vs": "Manchester Super Giants Men", "league": "The Hundred Men"},
        
        # July 29, 2026
        {"date": "July 29, 2026", "time": "11:00 PM IST", "squad": "SRH & SEC Stars", "players": "Heinrich Klaasen, Jonny Bairstow vs Tristan Stubbs, Marco Jansen", "vs": "London Spirit vs MI London", "league": "The Hundred Men"},
        
        # August 01, 2026
        {"date": "August 01, 2026", "time": "07:00 PM IST", "squad": "SRH & SEC Stars", "players": "Heinrich Klaasen, Jonny Bairstow vs Quinton de Kock, James Coles", "vs": "London Spirit vs Southern Brave", "league": "The Hundred Men"},
        
        # August 02, 2026
        {"date": "August 02, 2026", "time": "03:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Phoebe Litchfield, Deepti Sharma & Squad", "vs": "Trent Rockets Women", "league": "The Hundred Women"},
        {"date": "August 02, 2026", "time": "07:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Mitchell Marsh, Brydon Carse & Squad", "vs": "Trent Rockets Men", "league": "The Hundred Men"},
        {"date": "August 02, 2026", "time": "11:00 PM IST", "squad": "Sunrisers Eastern Cape", "players": "Tristan Stubbs, Marco Jansen (MI London)", "vs": "Manchester Super Giants", "league": "The Hundred Men"},
        
        # August 04, 2026
        {"date": "August 04, 2026", "time": "07:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson, Phoebe Litchfield, Deepti Sharma & Squad", "vs": "London Spirit Women", "league": "The Hundred Women"},
        {"date": "August 04, 2026", "time": "11:00 PM IST", "squad": "Sunrisers Leeds Men vs London Spirit", "players": "Brydon Carse, Mitchell Marsh vs Heinrich Klaasen, Jonny Bairstow", "vs": "London Spirit", "league": "The Hundred Men"},
        
        # August 07, 2026
        {"date": "August 07, 2026", "time": "07:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Phoebe Litchfield, Deepti Sharma & Squad", "vs": "Welsh Fire Women", "league": "The Hundred Women"},
        {"date": "August 07, 2026", "time": "11:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Harry Brook, Mitchell Marsh, Brydon Carse & Squad", "vs": "Welsh Fire Men", "league": "The Hundred Men"},
        
        # August 09, 2026
        {"date": "August 09, 2026", "time": "03:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson, Phoebe Litchfield, Deepti Sharma & Squad", "vs": "Birmingham Phoenix Women", "league": "The Hundred Women"},
        {"date": "August 09, 2026", "time": "07:00 PM IST", "squad": "Sunrisers Leeds Men", "players": "Harry Brook, Mitchell Marsh, Brydon Carse & Squad", "vs": "Birmingham Phoenix Men", "league": "The Hundred Men"},
        
        # August 12, 2026
        {"date": "August 12, 2026", "time": "07:30 PM IST", "squad": "Sunrisers Leeds Women", "players": "Dani Gibson, Phoebe Litchfield, Deepti Sharma & Squad", "vs": "MI London Women", "league": "The Hundred Women"},
        {"date": "August 12, 2026", "time": "11:00 PM IST", "squad": "Sunrisers Leeds Men vs MI London", "players": "Harry Brook, Mitchell Marsh vs Tristan Stubbs, Marco Jansen", "vs": "MI London Men", "league": "The Hundred Men"},
        
        # August 15, 2026
        {"date": "August 15, 2026", "time": "10:00 AM IST", "squad": "Sri Lanka & India Tests", "players": "Kamindu Mendis (SL) vs Ishan Kishan, Mohammed Shami, Nitish Kumar Reddy (IND)", "vs": "India vs Sri Lanka (1st Test - Day 1)", "league": "ICC World Test Championship"},
        
        # August 16, 2026
        {"date": "August 16, 2026", "time": "10:00 AM IST", "squad": "Sri Lanka & India Tests", "players": "Kamindu Mendis (SL) vs Ishan Kishan, Mohammed Shami, Nitish Kumar Reddy (IND)", "vs": "India vs Sri Lanka (1st Test - Day 2)", "league": "ICC World Test Championship"},
        {"date": "August 16, 2026", "time": "06:45 PM IST", "squad": "The Hundred Women Final", "players": "Sunrisers Leeds Women (TBD)", "vs": "Final Opponent", "league": "The Hundred Women Final"},
        {"date": "August 16, 2026", "time": "10:30 PM IST", "squad": "The Hundred Men Final", "players": "Sunrisers Leeds Men / Heinrich Klaasen / Tristan Stubbs (TBD)", "vs": "Final Opponent", "league": "The Hundred Men Final"}
    ]
    
    # Filter Domain
    if franchise_filter != "All":
        filtered_sched = [s for s in raw_schedules if franchise_filter in s["squad"] or franchise_filter in s["players"] or "SRH" in s["squad"]]
    else:
        filtered_sched = raw_schedules
        
    # Group By Date
    grouped_dates = {}
    for item in filtered_sched:
        d = item["date"]
        if d not in grouped_dates:
            grouped_dates[d] = []
        grouped_dates[d].append(item)
        
    for date_str, items in grouped_dates.items():
        st.markdown(f"<div class='date-header'>📅 {date_str}</div>", unsafe_allow_html=True)
        for item in items:
            st.markdown(f"""
            <div class='glass-card'>
                <div><span class='badge-time'>⏰ {item['time']}</span> <span class='badge-squad'>{item['squad']}</span></div>
                <h3 style='margin: 0.3rem 0; color: #FFFFFF;'>vs {item['vs']}</h3>
                <p style='color: #CBD5E1; margin-bottom: 0.2rem;'><strong>Squad Players:</strong> {item['players']}</p>
                <small style='color: #64748B;'>Tournament: {item['league']}</small>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# SECTION 2: ESPNcricinfo STYLE LIVE NEWS PORTAL (DIRECT ON-CLICK REDIRECTION)
# ---------------------------------------------------------
with tab_news:
    st.subheader("📰 Live Cricket News Feed (ESPNcricinfo Layout | Click Any Card to Read Original Story)")
    
    news_list = get_recent_news(limit=150)
    
    # Filter Domain for News
    if franchise_filter != "All":
        news_list = [n for n in news_list if n["franchise"] == franchise_filter]

    # Explicit Bulletproof Sorting by Datetime / Float Epoch (Latest First)
    news_list = sorted(news_list, key=get_bulletproof_sort_key, reverse=True)

    if news_list:
        for n in news_list:
            is_priority = n['importance_score'] >= 7.5
            priority_class = " priority-card" if is_priority else ""
            
            # Destination Link (Opens in new tab on click)
            article_link = n['link'] if n['link'] and n['link'] != "#" else f"https://news.google.com/search?q={urllib.parse.quote(n['player_name'] + ' cricket')}"

            # Detect League Context (The Hundred, SA20, IPL, International)
            league_context = detect_league_context(n['title'], n['summary'])

            st.markdown(f"""
            <a href='{article_link}' target='_blank' class='cricinfo-card-link'>
                <div class='cricinfo-news-card{priority_class}'>
                    <div class='card-meta-top'>
                        <span class='player-tag'>👤 {n['player_name']}</span>
                        <span class='franchise-tag'>🧡 {n['franchise']} Squad</span>
                        <span class='league-tag'>🏏 {league_context}</span>
                    </div>
                    <h2 class='cricinfo-title'>{n['title']}</h2>
                    <p class='cricinfo-summary'>{n['summary']}</p>
                    <div class='cricinfo-footer'>
                        <span class='pub-time'>📅 {n['published_at']}</span>
                        <span class='bullet'>•</span>
                        <span class='source-badge'>🔗 {n['source']}</span>
                        <span class='bullet'>•</span>
                        <span>Category: <strong style='color: #E2E8F0;'>{n['category']}</strong></span>
                        <span class='bullet'>•</span>
                        <span>Rating: <strong style='color: #FF8844;'>🔥 {n['importance_score']}/10</strong></span>
                        <span class='redirect-hint'>Read Original Article ↗</span>
                    </div>
                </div>
            </a>
            """, unsafe_allow_html=True)
    else:
        st.info("No player or franchise updates reported in the last 24 hours. Click 'Live Refresh 50 Feeds' in the sidebar to scan all 50 global outlets now!")
