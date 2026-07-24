"""
@SRHXtra Global Command Center Dashboard (V6.0 - High-Contrast ESPNcricinfo Portal UI).
Section 1: 30-Day Global Schedule Grouped by Date (12-hr AM/PM IST).
Section 2: High-Contrast Live News Feed (Exact Raw Source Headlines & Summaries | Direct On-Click Redirection).
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

# Premium High-Contrast Color Palette CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@600;700;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #0B0E14;
        color: #F3F4F6;
    }
    
    .stApp {
        background: radial-gradient(circle at 15% 15%, rgba(242, 101, 34, 0.09) 0%, rgba(11, 14, 20, 1) 85%);
    }

    section[data-testid="stSidebar"] {
        background-color: #111520 !important;
        border-right: 1px solid rgba(242, 101, 34, 0.3);
    }
    
    .brand-title {
        background: linear-gradient(135deg, #FF6B35 0%, #FFB703 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif;
        font-size: 2.8rem;
        font-weight: 900;
        margin-bottom: 0.2rem;
        line-height: 1.1;
    }
    
    .brand-subtitle {
        color: #9CA3AF;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
        font-weight: 400;
    }

    .date-header {
        background: linear-gradient(90deg, rgba(242, 101, 34, 0.25) 0%, rgba(26, 31, 46, 0.9) 100%);
        border-left: 4px solid #FF6B35;
        padding: 0.7rem 1.2rem;
        border-radius: 8px;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
        font-weight: 800;
        font-size: 1.3rem;
        color: #FFB703;
    }

    /* ESPNcricinfo Style News Card Link Wrapper */
    a.cricinfo-card-link {
        text-decoration: none !important;
        color: inherit !important;
        display: block;
        margin-bottom: 1.2rem;
    }

    /* ESPNcricinfo Style High-Contrast Card Container */
    .cricinfo-news-card {
        background: #161A26;
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 12px;
        padding: 1.5rem 1.7rem;
        transition: all 0.22s ease-in-out;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    }

    .cricinfo-news-card:hover {
        transform: translateY(-3px);
        border-color: #FF6B35;
        background: #1C2132;
        box-shadow: 0 12px 35px rgba(255, 107, 53, 0.25);
    }

    .cricinfo-news-card:hover .cricinfo-title {
        color: #FF6B35 !important;
    }

    /* Header Badges with High Contrast Colors */
    .card-meta-top {
        display: flex;
        gap: 0.6rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.75rem;
    }

    .player-tag {
        background: #FF6B35;
        color: #FFFFFF;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.2px;
        box-shadow: 0 2px 8px rgba(255, 107, 53, 0.3);
    }

    .franchise-tag {
        background: #FFB703;
        color: #0F172A;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 800;
        letter-spacing: 0.2px;
    }

    .league-tag {
        background: #0284C7;
        color: #FFFFFF;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
    }

    /* Main Headline - Maximum Readability */
    .cricinfo-title {
        font-family: 'Outfit', sans-serif;
        font-size: 1.35rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0 0 0.6rem 0;
        line-height: 1.35;
        transition: color 0.2s ease;
    }

    /* Summary Sub-headline - Crisp High-Contrast Gray */
    .cricinfo-summary {
        color: #D1D5DB;
        font-size: 1.02rem;
        line-height: 1.6;
        margin: 0 0 1.1rem 0;
        font-weight: 400;
    }

    /* Footer Metadata Line */
    .cricinfo-footer {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 0.8rem;
        font-size: 0.86rem;
        color: #9CA3AF;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        padding-top: 0.9rem;
    }

    .source-badge {
        color: #38BDF8;
        font-weight: 700;
        background: rgba(56, 189, 248, 0.1);
        padding: 3px 10px;
        border-radius: 6px;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }

    .pub-time {
        color: #E5E7EB;
        font-weight: 600;
    }

    .bullet {
        color: #4B5563;
    }

    .redirect-hint {
        margin-left: auto;
        color: #FF6B35;
        font-weight: 700;
        font-size: 0.88rem;
    }

    @media (max-width: 768px) {
        .brand-title { font-size: 2.1rem; }
        .cricinfo-news-card { padding: 1.1rem; }
        .cricinfo-title { font-size: 1.18rem; }
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("# 🧡 @SRHXtra")
st.sidebar.markdown("**Global Command Center V6.0**")
st.sidebar.markdown(f"📡 **UI:** `High-Contrast Live Portal`")
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
st.markdown("<div class='brand-subtitle'>High-Contrast Live News Feed | Exact Raw Source Headlines & Summaries | Click Any Article to Read Story</div>", unsafe_allow_html=True)

# Main Navigation Tabs
tab_schedule, tab_news = st.tabs([
    "🗓️ SECTION 1: 30-DAY GLOBAL SCHEDULE (GROUPED BY DATE)",
    "📰 SECTION 2: LIVE CRICKET NEWS FEED (EXACT SOURCE HEADLINES)"
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
            <div class='glass-card' style='background: #161A26; border: 1px solid rgba(255, 255, 255, 0.12); padding: 1.2rem; border-radius: 10px; margin-bottom: 1rem;'>
                <div><span class='player-tag'>⏰ {item['time']}</span> <span class='franchise-tag'>{item['squad']}</span></div>
                <h3 style='margin: 0.4rem 0; color: #FFFFFF; font-size: 1.3rem;'>vs {item['vs']}</h3>
                <p style='color: #D1D5DB; margin-bottom: 0.2rem; font-size: 1rem;'><strong>Squad Players:</strong> {item['players']}</p>
                <small style='color: #9CA3AF;'>Tournament: {item['league']}</small>
            </div>
            """, unsafe_allow_html=True)

# ---------------------------------------------------------
# SECTION 2: HIGH-CONTRAST ESPNcricinfo STYLE LIVE NEWS FEED
# ---------------------------------------------------------
with tab_news:
    st.subheader("📰 Live Cricket News Feed (Exact Source Headlines & Descriptions | Click Any Card to Read Story)")
    
    news_list = get_recent_news(limit=150)
    
    # Filter Domain for News
    if franchise_filter != "All":
        news_list = [n for n in news_list if n["franchise"] == franchise_filter]

    # Explicit Bulletproof Sorting by Datetime / Float Epoch (Latest First)
    news_list = sorted(news_list, key=get_bulletproof_sort_key, reverse=True)

    if news_list:
        for n in news_list:
            # Destination Link (Opens in new tab on click)
            article_link = n['link'] if n['link'] and n['link'] != "#" else f"https://news.google.com/search?q={urllib.parse.quote(n['player_name'] + ' cricket')}"

            # Detect League Badge (The Hundred, SA20, IPL, International)
            league_context = detect_league_badge(n['title'], n['summary'])

            st.markdown(f"""
            <a href='{article_link}' target='_blank' class='cricinfo-card-link'>
                <div class='cricinfo-news-card'>
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
                        <span class='redirect-hint'>Read Original Article ↗</span>
                    </div>
                </div>
            </a>
            """, unsafe_allow_html=True)
    else:
        st.info("No player or franchise updates reported in the last 24 hours. Click 'Live Refresh 50 Feeds' in the sidebar to scan all 50 global outlets now!")
