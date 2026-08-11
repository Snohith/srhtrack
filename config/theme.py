"""
SRHXtra — Ultra-Readable Daylight Theme & Dynamic Matchday Status Engine.
Delivers maximum legibility, crystal-clear reading comfort, and live match status tracking:
  - Dynamic Live Status: Automatically detects matches currently in progress (within 4 hours of start time).
  - Palette: Daylight Slate (#F8FAFC), Bright White (#FFFFFF), Sunrisers Copper (#F26522), Deep Slate Text (#0F172A).
  - Typography: Inter (Universal High-Legibility Sans-Serif font for headers, body, timestamps & telemetry).
"""
import html as html_lib
import urllib.parse
import time
from datetime import datetime
from utils.time_utils import get_current_ist
def parse_fixture_datetime(item):
    """Parses fixture date_str and time into an IST naive datetime object."""
    d_str = str(item.get("date_str", "")).replace(" 0", " ").strip()
    t_str = str(item.get("time", "12:00 PM IST")).replace(" IST", "").strip()
    full_str = f"{d_str} {t_str}"
    try:
        return datetime.strptime(full_str, "%B %d, %Y %I:%M %p")
    except Exception:
        try:
            return datetime.strptime(d_str, "%B %d, %Y")
        except Exception:
            return None
def get_fixture_status(item):
    """
    Determines match status dynamically:
      - 'LIVE': Start time has passed but match is within 4-hour window (0 <= elapsed < 4h)
      - 'UPCOMING': Match start time is in the future
      - 'COMPLETED': Match start time was more than 4 hours ago
    """
    dt = parse_fixture_datetime(item)
    if not dt:
        return "UPCOMING"
    now = get_current_ist().replace(tzinfo=None)
    diff_secs = (now - dt).total_seconds()
    if 0 <= diff_secs < 14400:  
        return "LIVE"
    elif diff_secs < 0:
        return "UPCOMING"
    else:
        return "COMPLETED"
def get_custom_css():
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    /* Global High-Legibility Inter Font Reset */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        background-color: #F8FAFC !important;
        color: #0F172A !important;
    }
    .stApp {
        background: #F8FAFC !important;
    }
    /* Streamlit Sidebar Overrides */
    section[data-testid="stSidebar"] {
        background-color: #F1F5F9 !important;
        border-right: 1px solid #E2E8F0 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.5px;
        color: #0F172A !important;
    }
    /* Streamlit Tabs Styling — Clean Daylight Controls */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background-color: #E2E8F0;
        padding: 0.4rem;
        border-radius: 12px;
        border: 1px solid #CBD5E1;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 0.65rem 1.3rem;
        border-radius: 8px;
        color: #475569;
        font-family: 'Inter', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.95rem;
        border: none !important;
        background-color: transparent !important;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #F26522 !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(242, 101, 34, 0.35);
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }
    /* Search & Inputs */
    .stTextInput input {
        background-color: #FFFFFF !important;
        border: 1px solid #CBD5E1 !important;
        color: #0F172A !important;
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.95rem !important;
        padding: 0.7rem 1rem !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02) !important;
    }
    .stTextInput input:focus {
        border-color: #F26522 !important;
        box-shadow: 0 0 0 2px rgba(242, 101, 34, 0.25) !important;
    }
    /* Brand Header Banner */
    .srh-brand-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 1.2rem;
        margin-bottom: 1.5rem;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .srh-brand-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.4rem;
        font-weight: 900;
        letter-spacing: -0.8px;
        color: #0F172A;
        line-height: 1.15;
    }
    .srh-brand-title span.highlight {
        color: #F26522;
    }
    .srh-brand-subtitle {
        color: #475569;
        font-size: 1rem;
        font-weight: 500;
        margin-top: 0.4rem;
    }
    .srh-live-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        color: #047857;
        font-family: 'Inter', sans-serif;
        font-size: 0.8rem;
        font-weight: 700;
        padding: 0.45rem 0.9rem;
        border-radius: 20px;
        box-shadow: 0 2px 6px rgba(4, 120, 87, 0.08);
    }
    .srh-live-pulse-dot {
        width: 8px;
        height: 8px;
        background-color: #10B981;
        border-radius: 50%;
        box-shadow: 0 0 8px #10B981;
        animation: live-pulse 1.8s infinite;
    }
    @keyframes live-pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.4; transform: scale(0.85); }
    }
    /* Next Match Hero Telemetry Bar */
    .hero-fixture-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #F26522;
        border-radius: 14px;
        padding: 1.4rem 1.7rem;
        margin-bottom: 1.8rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1.2rem;
    }
    .hero-fixture-card-live {
        border-left: 5px solid #DC2626 !important;
        background: linear-gradient(135deg, #FFFFFF 0%, #FEF2F2 100%) !important;
        box-shadow: 0 6px 20px rgba(220, 38, 38, 0.12) !important;
    }
    .hero-fixture-left { flex: 1; min-width: 280px; }
    .hero-fixture-tag {
        font-family: 'Inter', sans-serif;
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        color: #E05600;
        letter-spacing: 0.5px;
        margin-bottom: 0.3rem;
    }
    .hero-fixture-tag-live {
        color: #DC2626 !important;
    }
    .hero-fixture-vs {
        font-family: 'Inter', sans-serif;
        font-size: 1.65rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.4rem;
        line-height: 1.25;
    }
    .hero-fixture-details {
        display: flex;
        gap: 1.2rem;
        font-size: 0.92rem;
        color: #475569;
        font-weight: 600;
        flex-wrap: wrap;
    }
    .hero-fixture-right {
        text-align: right;
        background: #FFF7ED;
        border: 1px solid #FFEDD5;
        padding: 0.85rem 1.35rem;
        border-radius: 10px;
    }
    .hero-fixture-right-live {
        background: #FEE2E2 !important;
        border-color: #FCA5A5 !important;
    }
    .hero-countdown-val {
        font-family: 'Inter', sans-serif;
        font-size: 1.3rem;
        font-weight: 900;
        color: #F26522;
    }
    .hero-countdown-val-live {
        color: #DC2626 !important;
        animation: live-pulse 1.8s infinite;
    }
    .hero-countdown-lbl {
        font-size: 0.75rem;
        color: #9A3412;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .hero-countdown-lbl-live {
        color: #991B1B !important;
    }
    /* Telemetry Metric Strip */
    .telemetry-strip {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
        gap: 0.9rem;
        margin-bottom: 1.8rem;
    }
    .telemetry-metric-pill {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 0.95rem 1.15rem;
        display: flex;
        align-items: center;
        gap: 0.85rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
        transition: all 0.2s ease;
    }
    .telemetry-metric-pill:hover {
        border-color: #F26522;
        box-shadow: 0 6px 18px rgba(242, 101, 34, 0.12);
    }
    .telemetry-metric-icon {
        width: 40px;
        height: 40px;
        border-radius: 10px;
        background: rgba(242, 101, 34, 0.1);
        color: #F26522;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        font-weight: 800;
    }
    .telemetry-metric-num {
        font-family: 'Inter', sans-serif;
        font-size: 1.4rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
    }
    .telemetry-metric-lbl {
        font-size: 0.8rem;
        color: #64748B;
        font-weight: 600;
    }
    /* News Feed — Featured Hero Story Layout */
    a.featured-story-link { text-decoration: none !important; color: inherit !important; display: block; margin-bottom: 1.5rem; }
    .featured-story-card {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 16px;
        padding: 1.8rem;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.05);
        position: relative;
        overflow: hidden;
    }
    .featured-story-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; width: 100%; height: 4px;
        background: linear-gradient(90deg, #F26522, #FF7A38);
    }
    .featured-story-card:hover {
        transform: translateY(-2px);
        border-color: #F26522;
        box-shadow: 0 12px 32px rgba(242, 101, 34, 0.15);
    }
    .featured-badge-bar {
        display: flex;
        gap: 0.6rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 1rem;
    }
    .badge-hero-top {
        background: #F26522;
        color: #FFFFFF;
        font-family: 'Inter', sans-serif;
        font-size: 0.76rem;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        letter-spacing: 0.5px;
    }
    .featured-story-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.65rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.35;
        margin-bottom: 0.8rem;
        transition: color 0.2s ease;
    }
    .featured-story-card:hover .featured-story-title {
        color: #E05600;
    }
    .featured-story-desc {
        color: #334155;
        font-size: 1.05rem;
        line-height: 1.65;
        margin-bottom: 1.2rem;
        font-weight: 400;
    }
    .featured-story-footer {
        display: flex;
        align-items: center;
        gap: 1rem;
        border-top: 1px solid #F1F5F9;
        padding-top: 1rem;
        font-size: 0.88rem;
        color: #64748B;
        flex-wrap: wrap;
        font-weight: 600;
    }
    /* Standard Telemetry News Matrix Card */
    a.telemetry-card-link { text-decoration: none !important; color: inherit !important; display: block; margin-bottom: 1rem; }
    .telemetry-news-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.35rem 1.55rem;
        transition: all 0.2s ease;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
    }
    .telemetry-news-card:hover {
        border-color: #F26522;
        background: #FFFFFF;
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(242, 101, 34, 0.12);
    }
    .telemetry-news-card:hover .telemetry-card-title {
        color: #E05600;
    }
    .telemetry-card-tags {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.6rem;
    }
    .chip-player {
        background: rgba(242, 101, 34, 0.1);
        color: #E05600;
        border: 1px solid rgba(242, 101, 34, 0.25);
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .chip-squad {
        background: #F1F5F9;
        color: #334155;
        border: 1px solid #E2E8F0;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .chip-league {
        background: rgba(2, 132, 199, 0.08);
        color: #0284C7;
        border: 1px solid rgba(2, 132, 199, 0.25);
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .chip-new-live {
        background: #FEE2E2;
        color: #DC2626;
        border: 1px solid #FCA5A5;
        padding: 3px 9px;
        border-radius: 6px;
        font-size: 0.78rem;
        font-weight: 800;
    }
    .telemetry-card-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        margin: 0 0 0.5rem 0;
        line-height: 1.35;
        transition: color 0.2s ease;
    }
    .telemetry-card-desc {
        color: #334155;
        font-size: 0.98rem;
        line-height: 1.6;
        margin: 0 0 0.9rem 0;
        font-weight: 400;
    }
    .telemetry-card-footer {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        font-size: 0.84rem;
        color: #64748B;
        border-top: 1px solid #F1F5F9;
        padding-top: 0.75rem;
        flex-wrap: wrap;
        font-weight: 600;
    }
    .source-tag {
        color: #0284C7;
        font-weight: 700;
        background: rgba(2, 132, 199, 0.08);
        padding: 3px 9px;
        border-radius: 4px;
    }
    .time-tag {
        color: #E05600;
        font-weight: 700;
    }
    .link-action {
        margin-left: auto;
        color: #F26522;
        font-weight: 800;
    }
    /* Live Pulse Side Panel */
    .pulse-panel {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.3rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
    }
    .pulse-panel-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.18rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 1.1rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .pulse-item-dark {
        border-left: 3px solid rgba(242, 101, 34, 0.4);
        padding-left: 0.85rem;
        margin-bottom: 1.1rem;
        transition: border-color 0.2s ease;
    }
    .pulse-item-dark:hover {
        border-left-color: #F26522;
    }
    .pulse-time-dark {
        font-size: 0.78rem;
        color: #E05600;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .pulse-headline-dark {
        font-size: 0.92rem;
        color: #1E293B;
        font-weight: 600;
        line-height: 1.4;
        text-decoration: none;
        display: block;
    }
    .pulse-headline-dark:hover {
        color: #E05600;
    }
    /* Broadcast Matchday Cards (Tab 1) */
    .broadcast-match-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 14px rgba(0,0,0,0.03);
        transition: all 0.2s ease;
    }
    .broadcast-match-card-live {
        border-left: 5px solid #DC2626 !important;
        background: linear-gradient(135deg, #FFFFFF 0%, #FEF2F2 100%) !important;
    }
    .broadcast-match-card:hover {
        border-color: #F26522;
        box-shadow: 0 8px 24px rgba(242, 101, 34, 0.12);
    }
    .broadcast-match-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.8rem;
        flex-wrap: wrap;
        gap: 0.6rem;
    }
    .match-versus {
        font-family: 'Inter', sans-serif;
        font-size: 1.55rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.5rem;
    }
    .status-pill {
        font-family: 'Inter', sans-serif;
        font-size: 0.78rem;
        font-weight: 800;
        padding: 4px 11px;
        border-radius: 20px;
        text-transform: uppercase;
    }
    .status-pill-live { background: #FEE2E2; color: #DC2626; border: 1px solid #FCA5A5; animation: live-pulse 1.8s infinite; }
    .status-pill-upcoming { background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
    .status-pill-completed { background: #F1F5F9; color: #475569; border: 1px solid #CBD5E1; }
    .broadcast-badge {
        background: #EFF6FF;
        color: #1D4ED8;
        border: 1px solid #BFDBFE;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .venue-badge {
        background: #F8FAFC;
        color: #334155;
        border: 1px solid #E2E8F0;
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    /* On This Day Cards (Tab 3) */
    .otd-card-dark {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 5px solid #F26522;
        border-radius: 14px;
        padding: 1.5rem 1.8rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.03);
        transition: all 0.2s ease;
    }
    .otd-card-hero {
        border-left-color: #D97706 !important;
        background: linear-gradient(135deg, #FFFFFF 0%, #FFFBEB 100%) !important;
        box-shadow: 0 8px 24px rgba(217, 119, 6, 0.15) !important;
    }
    .otd-card-dark:hover {
        border-left-color: #D97706;
        box-shadow: 0 8px 24px rgba(242, 101, 34, 0.12);
    }
    .otd-year-dark {
        font-family: 'Inter', sans-serif;
        font-size: 1.45rem;
        font-weight: 800;
        color: #F26522;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
    }
    .otd-title-dark {
        font-family: 'Inter', sans-serif;
        font-size: 1.35rem;
        font-weight: 800;
        color: #0F172A;
        margin-bottom: 0.6rem;
    }
    .otd-desc-dark {
        color: #334155;
        font-size: 1.02rem;
        line-height: 1.65;
        margin-bottom: 0.8rem;
    }
    .otd-score-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 0.6rem 1rem;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        color: #0F172A;
        font-size: 0.95rem;
        margin-bottom: 0.8rem;
    }
    .otd-stat-chip {
        background: rgba(242, 101, 34, 0.1);
        color: #E05600;
        border: 1px solid rgba(242, 101, 34, 0.25);
        padding: 3px 10px;
        border-radius: 6px;
        font-size: 0.82rem;
        font-weight: 700;
        display: inline-block;
        margin-right: 0.5rem;
        margin-bottom: 0.4rem;
    }
    /* Source Favicon */
    .source-fav-icon {
        width: 14px;
        height: 14px;
        vertical-align: middle;
        border-radius: 3px;
        margin-right: 5px;
        display: inline-block;
    }
    @media (max-width: 768px) {
        .srh-brand-title { font-size: 1.9rem; }
        .hero-fixture-card { padding: 1rem; }
        .featured-story-title { font-size: 1.3rem; }
    }
</style>
"""
def safe_article_link(n):
    """Returns a valid article link, falling back to Google News search."""
    if n.get("link") and n["link"] != "#":
        return n["link"]
    return f"https://news.google.com/search?q={urllib.parse.quote(str(n.get('player_name', '')) + ' cricket')}"
def detect_league_badge(title, summary):
    """Detects competition for badge display."""
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
def time_ago(pub_ts):
    """Formats timestamp into relative human readable time string."""
    if not pub_ts or pub_ts <= 0:
        return "Recently"
    diff = time.time() - float(pub_ts)
    if diff < 60:
        return "Just now"
    if diff < 3600:
        return f"{int(diff / 60)}m ago"
    if diff < 86400:
        hrs = int(diff / 3600)
        mins = int((diff % 3600) / 60)
        return f"{hrs}h {mins}m ago" if mins else f"{hrs}h ago"
    return "1d+ ago"
def is_new_article(pub_ts, hours=2):
    """Returns True if article published within last N hours."""
    if not pub_ts or pub_ts <= 0:
        return False
    return (time.time() - float(pub_ts)) < (hours * 3600)
def get_favicon_url(link):
    """Generates Google favicon URL for source domain."""
    try:
        domain = urllib.parse.urlparse(link).netloc
        if domain:
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=16"
    except Exception:
        pass
    return ""
def render_header_banner(player_count, franchise_count=4):
    """Renders top brand header."""
    return f"""
    <div class='srh-brand-header'>
        <div>
            <div class='srh-brand-title'><span class='highlight'>SRHXtra</span> Telemetry Engine</div>
            <div class='srh-brand-subtitle'>Matchday Reconnaissance & Squad Intelligence Hub | {player_count} Squad Members Across {franchise_count} Sunrisers Franchises</div>
        </div>
        <div class='srh-live-badge'>
            <span class='srh-live-pulse-dot'></span>
            15-MIN AUTOMATED RSS INGESTION ACTIVE
        </div>
    </div>
    """
def render_next_match_hero(next_fixture, status="UPCOMING"):
    """Renders next fixture countdown telemetry bar with dynamic LIVE / UPCOMING status."""
    if not next_fixture:
        return ""
    vs = html_lib.escape(next_fixture.get("vs", ""))
    squad = html_lib.escape(next_fixture.get("squad", ""))
    league = html_lib.escape(next_fixture.get("league", ""))
    date_str = html_lib.escape(next_fixture.get("date_str", ""))
    match_time = html_lib.escape(next_fixture.get("time", ""))
    venue = html_lib.escape(next_fixture.get("venue", "TBD"))
    broadcast = html_lib.escape(next_fixture.get("broadcast", "Check Local Listings"))
    if status == "LIVE":
        card_class = "hero-fixture-card hero-fixture-card-live"
        tag_html = f"<div class='hero-fixture-tag hero-fixture-tag-live'>🔴 MATCHDAY LIVE NOW • {league}</div>"
        right_class = "hero-fixture-right hero-fixture-right-live"
        val_html = "<div class='hero-countdown-val hero-countdown-val-live'>🔴 LIVE NOW</div>"
        lbl_html = "<div class='hero-countdown-lbl hero-countdown-lbl-live'>Match in Progress</div>"
    elif status == "COMPLETED":
        card_class = "hero-fixture-card"
        tag_html = f"<div class='hero-fixture-tag'>COMPLETED FIXTURE • {league}</div>"
        right_class = "hero-fixture-right"
        val_html = "<div class='hero-countdown-val' style='color:#64748B;'>✅ FINAL</div>"
        lbl_html = "<div class='hero-countdown-lbl'>Match Completed</div>"
    else:
        card_class = "hero-fixture-card"
        tag_html = f"<div class='hero-fixture-tag'>NEXT UPCOMING FIXTURE • {league}</div>"
        right_class = "hero-fixture-right"
        val_html = "<div class='hero-countdown-val'>⏳ UPCOMING</div>"
        lbl_html = "<div class='hero-countdown-lbl'>Matchday Status</div>"
    return f"""
    <div class='{card_class}'>
        <div class='hero-fixture-left'>
            {tag_html}
            <div class='hero-fixture-vs'>{squad} vs {vs}</div>
            <div class='hero-fixture-details'>
                <span>📅 {date_str} @ {match_time}</span>
                <span>📍 {venue}</span>
                <span>📺 {broadcast}</span>
            </div>
        </div>
        <div class='{right_class}'>
            {val_html}
            {lbl_html}
        </div>
    </div>
    """
def render_telemetry_metrics(source_count, player_count, live_count):
    """Renders top metric pills strip."""
    return f"""
    <div class='telemetry-strip'>
        <div class='telemetry-metric-pill'>
            <div class='telemetry-metric-icon'>📡</div>
            <div>
                <div class='telemetry-metric-num'>{source_count}</div>
                <div class='telemetry-metric-lbl'>Global Feeds</div>
            </div>
        </div>
        <div class='telemetry-metric-pill'>
            <div class='telemetry-metric-icon'>👥</div>
            <div>
                <div class='telemetry-metric-num'>{player_count}</div>
                <div class='telemetry-metric-lbl'>Roster Members</div>
            </div>
        </div>
        <div class='telemetry-metric-pill'>
            <div class='telemetry-metric-icon'>🧡</div>
            <div>
                <div class='telemetry-metric-num'>4</div>
                <div class='telemetry-metric-lbl'>Franchises</div>
            </div>
        </div>
        <div class='telemetry-metric-pill'>
            <div class='telemetry-metric-icon'>📰</div>
            <div>
                <div class='telemetry-metric-num'>{live_count}</div>
                <div class='telemetry-metric-lbl'>Live Reports</div>
            </div>
        </div>
    </div>
    """
def render_featured_hero_news(n):
    """Renders top latest article in a prominent featured hero layout."""
    link = safe_article_link(n)
    link_attr = html_lib.escape(link, quote=True)
    league = detect_league_badge(n.get("title", ""), n.get("summary", ""))
    pub_ts = n.get("pub_timestamp", 0)
    ago = time_ago(pub_ts)
    favicon = get_favicon_url(link)
    fav_html = f"<img src='{favicon}' class='source-fav-icon' onerror='this.style.display=\"none\"'>" if favicon else ""
    clean_title = html_lib.escape(str(n.get("title", "")).replace("\n", " ").strip())
    clean_summary = html_lib.escape(str(n.get("summary", "")).replace("\n", " ").strip())
    player_name = html_lib.escape(str(n.get("player_name", "")).strip())
    franchise = html_lib.escape(str(n.get("franchise", "")).strip())
    source = html_lib.escape(str(n.get("source", "")).strip())
    pub_at = html_lib.escape(str(n.get("published_at", "")).strip())
    return (
        f"<a href='{link_attr}' target='_blank' class='featured-story-link'>"
        f"<div class='featured-story-card'>"
        f"<div class='featured-badge-bar'>"
        f"<span class='badge-hero-top'>TOP FEATURED STORY</span>"
        f"<span class='chip-player'>👤 {player_name}</span>"
        f"<span class='chip-squad'>🧡 {franchise}</span>"
        f"<span class='chip-league'>🏏 {league}</span>"
        f"</div>"
        f"<div class='featured-story-title'>{clean_title}</div>"
        f"<div class='featured-story-desc'>{clean_summary}</div>"
        f"<div class='featured-story-footer'>"
        f"<span class='time-tag'>🕒 {ago}</span>"
        f"<span>{pub_at}</span>"
        f"<span class='source-tag'>{fav_html} {source}</span>"
        f"<span class='link-action'>Open Article ↗</span>"
        f"</div>"
        f"</div>"
        f"</a>"
    )
def render_telemetry_news_card(n):
    """Renders a standard single-line clean news item card."""
    link = safe_article_link(n)
    link_attr = html_lib.escape(link, quote=True)
    league = detect_league_badge(n.get("title", ""), n.get("summary", ""))
    pub_ts = n.get("pub_timestamp", 0)
    ago = time_ago(pub_ts)
    new_badge = "<span class='chip-new-live'>● NEW</span>" if is_new_article(pub_ts) else ""
    favicon = get_favicon_url(link)
    fav_html = f"<img src='{favicon}' class='source-fav-icon' onerror='this.style.display=\"none\"'>" if favicon else ""
    clean_title = html_lib.escape(str(n.get("title", "")).replace("\n", " ").strip())
    clean_summary = html_lib.escape(str(n.get("summary", "")).replace("\n", " ").strip())
    player_name = html_lib.escape(str(n.get("player_name", "")).strip())
    franchise = html_lib.escape(str(n.get("franchise", "")).strip())
    source = html_lib.escape(str(n.get("source", "")).strip())
    pub_at = html_lib.escape(str(n.get("published_at", "")).strip())
    return (
        f"<a href='{link_attr}' target='_blank' class='telemetry-card-link'>"
        f"<div class='telemetry-news-card'>"
        f"<div class='telemetry-card-tags'>{new_badge}<span class='chip-player'>👤 {player_name}</span><span class='chip-squad'>{franchise}</span><span class='chip-league'>{league}</span></div>"
        f"<div class='telemetry-card-title'>{clean_title}</div>"
        f"<div class='telemetry-card-desc'>{clean_summary}</div>"
        f"<div class='telemetry-card-footer'>"
        f"<span class='time-tag'>🕒 {ago}</span>"
        f"<span>{pub_at}</span>"
        f"<span class='source-tag'>{fav_html} {source}</span>"
        f"<span class='link-action'>Read ↗</span>"
        f"</div>"
        f"</div>"
        f"</a>"
    )
def render_telemetry_pulse_item(n):
    """Renders compact sidebar live pulse timeline entry."""
    link = safe_article_link(n)
    link_attr = html_lib.escape(link, quote=True)
    pub_ts = n.get("pub_timestamp", 0)
    ago = time_ago(pub_ts)
    raw_title = str(n.get("title", "")).replace("\n", " ").strip()
    headline = html_lib.escape(raw_title[:65] + ("..." if len(raw_title) > 65 else ""))
    player_name = html_lib.escape(str(n.get("player_name", "")).strip())
    return (
        f"<div class='pulse-item-dark'>"
        f"<div class='pulse-time-dark'>🕒 {ago} • {player_name}</div>"
        f"<a href='{link_attr}' target='_blank' class='pulse-headline-dark'>{headline}</a>"
        f"</div>"
    )
def render_broadcast_match_card(item, status="UPCOMING"):
    """Renders fixture item in broadcast infographic format."""
    if status == "LIVE":
        status_html = "<span class='status-pill status-pill-live'>🔴 LIVE NOW</span>"
        card_extra_class = " broadcast-match-card-live"
    elif status == "COMPLETED":
        status_html = "<span class='status-pill status-pill-completed'>✅ COMPLETED</span>"
        card_extra_class = ""
    else:
        status_html = "<span class='status-pill status-pill-upcoming'>⏳ UPCOMING</span>"
        card_extra_class = ""
    venue_html = f"<span class='venue-badge'>📍 {item.get('venue', '')}</span>" if item.get("venue") else ""
    broadcast_html = f"<span class='broadcast-badge'>📺 {item.get('broadcast', '')}</span>" if item.get("broadcast") else ""
    return (
        f"<div class='broadcast-match-card{card_extra_class}'>"
        f"<div class='broadcast-match-header'>"
        f"{status_html}"
        f"<span class='chip-squad'>{item.get('squad', '')}</span>"
        f"<span class='chip-league'>🏏 {item.get('league', '')}</span>"
        f"{venue_html}"
        f"{broadcast_html}"
        f"</div>"
        f"<div class='match-versus'>{item.get('squad', '')} vs {item.get('vs', '')}</div>"
        f"<div style='color:#475569;font-size:0.92rem;font-weight:600;'>⏰ <strong>Match Time:</strong> {item.get('time', '')} | <strong>Date:</strong> {item.get('date_str', '')}</div>"
        f"<div style='color:#334155;font-size:0.92rem;margin-top:0.5rem;'><strong>Key Squad Members:</strong> {item.get('players', '')}</div>"
        f"</div>"
    )
def render_otd_telemetry_card(m, is_hero=False):
    """Renders On This Day historical moment card with scorecards and performance chips."""
    emoji = m.get("emoji", "🏆")
    year = m.get("year", "")
    category = m.get("category", "")
    title = html_lib.escape(m.get("title", ""))
    desc = html_lib.escape(m.get("desc", ""))
    entity = html_lib.escape(m.get("entity", ""))
    franchise = html_lib.escape(m.get("franchise", ""))
    scorecard = html_lib.escape(m.get("scorecard", "")) if m.get("scorecard") else ""
    stats = m.get("stats", [])
    card_class = "otd-card-dark otd-card-hero" if is_hero else "otd-card-dark"
    hero_badge = "<span class='chip-new-live' style='background:#FEF3C7;color:#92400E;border-color:#FDE68A;'>⭐ TODAY'S ANNIVERSARY HIGHLIGHT</span>" if is_hero else ""
    scorecard_html = f"<div class='otd-score-box'>🏏 <strong>Match Telemetry / Scorecard:</strong> {scorecard}</div>" if scorecard else ""
    stats_html = ""
    if stats:
        chips = "".join([f"<span class='otd-stat-chip'>📊 {html_lib.escape(s)}</span>" for s in stats])
        stats_html = f"<div style='margin-top:0.4rem;margin-bottom:0.6rem;'>{chips}</div>"
    return (
        f"<div class='{card_class}'>"
        f"<div style='display:flex;gap:0.5rem;align-items:center;margin-bottom:0.5rem;flex-wrap:wrap;'>"
        f"{hero_badge}"
        f"<span class='otd-year-dark'>{emoji} {year}</span>"
        f"<span class='chip-league'>{category}</span>"
        f"<span class='chip-player'>👤 {entity}</span>"
        f"<span class='chip-squad'>🧡 {franchise}</span>"
        f"</div>"
        f"<div class='otd-title-dark'>{title}</div>"
        f"{scorecard_html}"
        f"{stats_html}"
        f"<div class='otd-desc-dark'>{desc}</div>"
        f"</div>"
    )
