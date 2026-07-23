"""
@SRHXtra Global Command Center Dashboard (V2.2 Refined UI).
Section 1: 30-Day Global Schedule Grouped by Date (12-hr AM/PM IST).
Section 2: Player Reconnaissance & Updates sorted by Latest Posted IST Time (12-hr AM/PM IST).
"""

import os
import streamlit as st
import pandas as pd
from config.roster import MASTER_ROSTER
from database.db_manager import init_db, get_recent_news, search_news
from scrapers.rss_collector import fetch_and_filter_rss
from utils.time_utils import format_ist_12hr

# Page Configuration
st.set_page_config(
    page_title="@SRHXtra Global Command Center",
    page_icon="🧡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Database & Pre-seed Data
init_db()

# Premium Dark Glassmorphism CSS & Responsive Spacing
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@600;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #0B0C10;
        color: #E2E8F0;
    }
    
    .stApp {
        background: radial-gradient(circle at 10% 20%, rgba(242, 101, 34, 0.08) 0%, rgba(11, 12, 16, 1) 90%);
    }

    section[data-testid="stSidebar"] {
        background-color: #12131C !important;
        border-right: 1px solid rgba(242, 101, 34, 0.25);
    }
    
    h1, h2, h3, h4, .brand-title {
        font-family: 'Outfit', sans-serif;
        letter-spacing: -0.5px;
    }
    
    .brand-title {
        background: linear-gradient(135deg, #FF6B00 0%, #FFA800 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
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

    .glass-card {
        background: rgba(22, 24, 34, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(242, 101, 34, 0.18);
        border-radius: 12px;
        padding: 1.3rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        transition: transform 0.2s ease;
    }
    
    .glass-card:hover {
        transform: translateY(-2px);
        border-color: rgba(242, 101, 34, 0.45);
    }

    .priority-card {
        background: linear-gradient(135deg, rgba(42, 22, 18, 0.85) 0%, rgba(20, 12, 10, 0.95) 100%);
        border-left: 5px solid #FF3D00;
        border-radius: 12px;
        padding: 1.3rem;
        margin-bottom: 1.2rem;
    }
    
    .badge-time {
        background: rgba(242, 101, 34, 0.18);
        color: #FF8844;
        border: 1px solid rgba(242, 101, 34, 0.35);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 0.4rem;
    }
    
    .badge-squad {
        background: rgba(255, 215, 0, 0.12);
        color: #FFD700;
        border: 1px solid rgba(255, 215, 0, 0.25);
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }

    @media (max-width: 768px) {
        .brand-title { font-size: 2.1rem; }
        .glass-card, .priority-card { padding: 1rem; }
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("# 🧡 @SRHXtra")
st.sidebar.markdown("**Global Command Center V2.2**")
st.sidebar.markdown(f"🕒 **Current IST:** `{format_ist_12hr()}`")

st.sidebar.markdown("---")
franchise_filter = st.sidebar.selectbox(
    "Filter Squad Domain",
    ["All", "Sunrisers Hyderabad", "Sunrisers Eastern Cape", "Sunrisers Leeds Men", "Sunrisers Leeds Women"]
)

if st.sidebar.button("⚡ Live Refresh Feeds"):
    with st.spinner("Polling 16 global cricket sources..."):
        count = fetch_and_filter_rss()
        st.sidebar.success(f"Captured {count} new Sunrisers items!")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🌐 Remote Access")
st.sidebar.info("""
**View from any phone or device:**
1. **Local Wi-Fi:** `http://192.168.1.130:8501`
2. **Live Cloud URL:** [https://srhtrack.streamlit.app/](https://srhtrack.streamlit.app/)
""")

# Dashboard Brand Header
st.markdown("<div class='brand-title'>🦅 @SRHXtra GLOBAL TRACKER</div>", unsafe_allow_html=True)
st.markdown("<div class='brand-subtitle'>Unified 2-Section Operations Desk | 73 Players Tracked Across 4 Global Sunrisers Squads</div>", unsafe_allow_html=True)

# Main Navigation Tabs
tab_schedule, tab_news = st.tabs([
    "🗓️ SECTION 1: 30-DAY GLOBAL SCHEDULE (GROUPED BY DATE)",
    "📰 SECTION 2: PLAYER RECONNAISSANCE & UPDATES (SORTED BY LATEST IST TIME)"
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
# SECTION 2: PLAYER RECONNAISSANCE & UPDATES (12-HR AM/PM IST SORTED LATEST FIRST)
# ---------------------------------------------------------
with tab_news:
    st.subheader("📰 Player Reconnaissance & Updates (Sorted Latest First by 12-Hour AM/PM IST Time)")
    
    news_list = get_recent_news(limit=50)
    
    if news_list:
        for n in news_list:
            is_priority = n['importance_score'] >= 7.5
            card_style = "priority-card" if is_priority else "glass-card"
            badge_label = "🔥 PRIORITY ALERT" if is_priority else "MATCH UPDATE"
            
            st.markdown(f"""
            <div class='{card_style}'>
                <div><span class='badge-time'>🕒 {n['published_at']}</span> <span class='badge-squad'>{n['franchise']}</span></div>
                <h3 style='margin: 0.4rem 0; color: #FFFFFF;'>👤 {n['player_name']} — {n['title']}</h3>
                <p style='color: #CBD5E1; font-size: 1.02rem; line-height: 1.5; margin-bottom: 0.6rem;'>{n['summary']}</p>
                <div style='display: flex; gap: 1.2rem; font-size: 0.85rem; color: #94A3B8;'>
                    <span>Category: <strong style='color: #E2E8F0;'>{n['category']}</strong></span>
                    <span>Impact Rating: <strong style='color: #FF8844;'>🔥 {n['importance_score']}/10</strong></span>
                    <span>Source: <strong style='color: #E2E8F0;'>{n['source']}</strong></span>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No player updates captured yet. Click 'Live Refresh Feeds' in the sidebar!")
