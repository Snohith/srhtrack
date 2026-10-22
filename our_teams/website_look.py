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
from helpers.dates_and_times import what_time_is_it_in_india_now
def read_match_date_and_time(item):
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
def is_match_live_now_or_later(item):
    """
    Determines match status dynamically:
      - 'LIVE': Start time has passed but match is within 4-hour window (0 <= elapsed < 4h)
      - 'UPCOMING': Match start time is in the future
      - 'COMPLETED': Match start time was more than 4 hours ago
    """
    dt = read_match_date_and_time(item)
    if not dt:
        return "UPCOMING"
    now = what_time_is_it_in_india_now().replace(tzinfo=None)
    diff_secs = (now - dt).total_seconds()
    if 0 <= diff_secs < 14400:  
        return "LIVE"
    elif diff_secs < 0:
        return "UPCOMING"
    else:
        return "COMPLETED"
def get_website_style():
    return """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    :root {
        --srh-bg: #F7F7F5;
        --srh-surface: #FFFFFF;
        --srh-surface-soft: #FCFBFA;
        --srh-ink: #191C22;
        --srh-body: #3F4753;
        --srh-muted: #5F6B7A;
        --srh-faint: #8A94A3;
        --srh-line: #E7E4E0;
        --srh-line-soft: #F0EEEB;
        --srh-accent: #EA580C;
        --srh-accent-ink: #C2410C;
        --srh-accent-soft: #FDF0E7;
        --srh-green: #15803D;
        --srh-green-soft: #EAF5EE;
        --srh-red: #D92D20;
        --srh-red-soft: #FDECEC;
        --srh-amber-bg: #F7EFDC;
        --srh-amber-ink: #7C5A10;
        --srh-night: #141519;
        --srh-night-raise: #1E2027;
        --srh-night-line: #2B2E37;
        --srh-night-ink: #F2F3F5;
        --srh-night-muted: #A7ADBA;
        --srh-night-faint: #71767F;
        --srh-r: 10px;
        --srh-r-sm: 7px;
        --srh-shadow: 0 1px 2px rgba(22, 24, 29, 0.05);
        --srh-shadow-hover: 0 6px 16px rgba(22, 24, 29, 0.08);
    }
    /* Base */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        background-color: var(--srh-bg) !important;
        color: var(--srh-ink) !important;
    }
    .stApp {
        background: var(--srh-bg) !important;
    }
    ::selection {
        background: #FBD9BE;
    }
    :focus-visible {
        outline: 2px solid var(--srh-accent);
        outline-offset: 2px;
    }
    .block-container {
        max-width: 72rem;
        padding-top: 2rem;
    }
    /* Sidebar — dark desk rail */
    section[data-testid="stSidebar"] {
        background-color: var(--srh-night) !important;
        border-right: 1px solid #000000 !important;
    }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown span,
    section[data-testid="stSidebar"] .stMarkdown div,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] .stExpander details summary p {
        color: var(--srh-night-muted) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown strong {
        color: var(--srh-night-ink) !important;
    }
    section[data-testid="stSidebar"] .stMarkdown h1,
    section[data-testid="stSidebar"] .stMarkdown h2,
    section[data-testid="stSidebar"] .stMarkdown h3 {
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.01em;
        color: var(--srh-night-ink) !important;
    }
    section[data-testid="stSidebar"] code {
        background: var(--srh-night-raise) !important;
        border: 1px solid var(--srh-night-line) !important;
        color: var(--srh-night-ink) !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: var(--srh-night-line) !important;
    }
    .srh-side-label {
        font-size: 0.7rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--srh-night-faint) !important;
    }
    .srh-side-brand {
        font-family: 'Inter', sans-serif !important;
        font-weight: 800 !important;
        letter-spacing: -0.015em;
        color: var(--srh-night-ink) !important;
        margin-bottom: 0.15rem;
    }
    .srh-side-brand .dot {
        color: var(--srh-accent);
    }
    /* Sidebar widgets on dark */
    section[data-testid="stSidebar"] .stSelectbox label {
        color: var(--srh-night-faint) !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: var(--srh-night-raise) !important;
        border-color: var(--srh-night-line) !important;
        border-radius: 8px !important;
        color: var(--srh-night-ink) !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] span {
        color: var(--srh-night-ink) !important;
    }
    section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
        fill: var(--srh-night-muted) !important;
    }
    section[data-testid="stSidebar"] .stButton button {
        background: var(--srh-night-ink) !important;
        border: 1px solid var(--srh-night-ink) !important;
        color: #141519 !important;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        background: #FFFFFF !important;
        border-color: #FFFFFF !important;
        color: #141519 !important;
    }
    section[data-testid="stSidebar"] details {
        border: 1px solid var(--srh-night-line) !important;
        border-radius: 8px;
        background: transparent !important;
    }
    section[data-testid="stSidebar"] details summary {
        color: var(--srh-night-ink) !important;
    }
    section[data-testid="stSidebar"] .stSpinner > div {
        border-top-color: var(--srh-accent) !important;
    }
    /* Tabs — editorial underline; one accent line, nothing else */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.4rem;
        background-color: transparent;
        padding: 0;
        border-radius: 0;
        border: none;
        border-bottom: 1px solid var(--srh-line);
        margin-bottom: 1.6rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: auto;
        padding: 0.6rem 0.15rem;
        border-radius: 0;
        color: var(--srh-faint);
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9rem;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -1px;
        background-color: transparent !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--srh-ink);
    }
    .stTabs [aria-selected="true"] {
        background-color: transparent !important;
        color: var(--srh-ink) !important;
        font-weight: 750 !important;
        border-bottom: 2px solid var(--srh-accent) !important;
        box-shadow: none;
    }
    .stTabs [data-baseweb="tab-border"] {
        display: none !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }
    /* Inputs */
    .stTextInput input {
        background-color: #FFFFFF !important;
        border: 1px solid var(--srh-line) !important;
        color: var(--srh-ink) !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.92rem !important;
        padding: 0.6rem 0.9rem !important;
        box-shadow: none !important;
    }
    .stTextInput input:focus {
        border-color: var(--srh-accent) !important;
        box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.14) !important;
    }
    .stTextInput label, .stSelectbox label, .stCheckbox label {
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        color: var(--srh-muted) !important;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        border-radius: 8px !important;
        border-color: var(--srh-line) !important;
    }
    .stCheckbox input {
        accent-color: var(--srh-accent);
    }
    /* Buttons — neutral by default */
    .stButton button {
        border-radius: 8px !important;
        border: 1px solid var(--srh-line) !important;
        background: #FFFFFF !important;
        color: var(--srh-ink) !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        box-shadow: none !important;
    }
    .stButton button:hover {
        border-color: var(--srh-ink) !important;
        color: var(--srh-ink) !important;
    }
    /* Metrics */
    [data-testid="stMetricLabel"] {
        font-size: 0.72rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--srh-faint) !important;
    }
    [data-testid="stMetricValue"] {
        font-variant-numeric: tabular-nums;
    }
    /* Section scaffolding */
    .srh-section-title {
        font-family: 'Inter', sans-serif;
        font-weight: 750;
        font-size: 1.2rem;
        letter-spacing: -0.01em;
        color: var(--srh-ink);
        margin: 0 0 0.25rem 0;
    }
    .srh-section-sub {
        color: var(--srh-muted);
        font-size: 0.86rem;
        margin-bottom: 1.1rem;
        line-height: 1.55;
    }
    .srh-section-sub a {
        color: var(--srh-accent-ink);
        font-weight: 600;
        text-decoration: none;
    }
    .srh-section-sub a:hover {
        text-decoration: underline;
    }
    .srh-date-group {
        font-family: 'Inter', sans-serif;
        font-size: 0.76rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: var(--srh-muted);
        margin: 1.4rem 0 0.65rem 0;
        padding-bottom: 0.45rem;
        border-bottom: 1px solid var(--srh-line);
    }
    .srh-note {
        font-size: 0.8rem;
        color: var(--srh-faint);
    }
    .srh-empty {
        background: var(--srh-surface);
        border: 1px solid var(--srh-line);
        border-radius: var(--srh-r);
        padding: 1.6rem 1.4rem;
        text-align: center;
        color: var(--srh-muted);
        font-size: 0.9rem;
    }
    .srh-stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 0.7rem;
        margin: 0.8rem 0 1.4rem 0;
    }
    .srh-stat {
        background: var(--srh-surface);
        border: 1px solid var(--srh-line);
        border-radius: var(--srh-r);
        padding: 0.7rem 0.9rem;
        box-shadow: var(--srh-shadow);
    }
    .srh-stat-num {
        font-size: 1.25rem;
        font-weight: 750;
        color: var(--srh-ink);
        font-variant-numeric: tabular-nums;
        line-height: 1.2;
    }
    .srh-stat-lbl {
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--srh-faint);
        margin-top: 0.15rem;
    }
    /* Masthead */
    .srh-masthead-kicker {
        font-size: 0.7rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--srh-accent-ink);
        margin-bottom: 0.3rem;
    }
    .srh-brand-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-end;
        padding-bottom: 1.2rem;
        margin-bottom: 0;
        flex-wrap: wrap;
        gap: 0.8rem;
    }
    .srh-brand-title {
        font-family: 'Inter', sans-serif;
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: var(--srh-ink);
        line-height: 1.05;
    }
    .srh-brand-title span.highlight {
        color: var(--srh-accent);
    }
    .srh-brand-subtitle {
        color: var(--srh-muted);
        font-size: 0.88rem;
        font-weight: 500;
        margin-top: 0.35rem;
    }
    .srh-live-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: var(--srh-night);
        border: 1px solid var(--srh-night);
        color: var(--srh-night-muted);
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        padding: 0.5rem 0.85rem;
        border-radius: 999px;
    }
    .srh-live-badge strong {
        color: var(--srh-night-ink);
        font-weight: 750;
    }
    .srh-live-pulse-dot {
        width: 7px;
        height: 7px;
        background-color: #34D399;
        border-radius: 50%;
        animation: live-pulse 2.4s ease-in-out infinite;
        flex-shrink: 0;
    }
    @keyframes live-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
    }
    /* Hero — dark feature panel, the single entry point */
    .hero-fixture-card {
        background: var(--srh-night);
        border: 1px solid #000000;
        border-radius: 14px;
        padding: 1.6rem 1.7rem;
        margin: 1.2rem 0 1.5rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1.2rem;
        position: relative;
        overflow: hidden;
    }
    .hero-fixture-card::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: var(--srh-accent);
    }
    .hero-fixture-card-live::before {
        background: var(--srh-red);
    }
    .hero-fixture-left { flex: 1; min-width: 260px; }
    .hero-fixture-tag {
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        font-weight: 750;
        text-transform: uppercase;
        color: var(--srh-accent);
        letter-spacing: 0.1em;
        margin-bottom: 0.45rem;
        filter: brightness(1.35);
    }
    .hero-fixture-tag-live {
        color: #FF6B61;
        filter: none;
    }
    .hero-fixture-vs {
        font-family: 'Inter', sans-serif;
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: -0.025em;
        color: var(--srh-night-ink);
        margin-bottom: 0.55rem;
        line-height: 1.15;
    }
    .hero-fixture-details {
        display: flex;
        gap: 0.5rem 1.1rem;
        font-size: 0.85rem;
        color: var(--srh-night-muted);
        font-weight: 500;
        flex-wrap: wrap;
    }
    .hero-fixture-details strong {
        color: var(--srh-night-ink);
        font-weight: 650;
    }
    .hero-fixture-card .srh-crex-link {
        color: #FF8A4C;
        margin-top: 0.7rem;
    }
    .hero-fixture-right {
        text-align: right;
        padding-left: 1.3rem;
        border-left: 1px solid var(--srh-night-line);
    }
    .hero-countdown-val {
        font-family: 'Inter', sans-serif;
        font-size: 2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--srh-night-ink);
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.55rem;
        font-variant-numeric: tabular-nums;
        line-height: 1.1;
    }
    .hero-countdown-val::before {
        content: '';
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--srh-accent);
    }
    .hero-countdown-val-live {
        color: #FFFFFF;
    }
    .hero-countdown-val-live::before {
        background: var(--srh-red);
        animation: live-pulse 2.4s ease-in-out infinite;
    }
    .hero-countdown-lbl {
        font-size: 0.7rem;
        color: var(--srh-night-faint);
        text-transform: uppercase;
        font-weight: 650;
        letter-spacing: 0.08em;
        margin-top: 0.3rem;
    }
    /* Metric strip */
    .telemetry-strip {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 0.7rem;
        margin-bottom: 1.4rem;
    }
    .telemetry-metric-pill {
        background: var(--srh-surface);
        border: 1px solid var(--srh-line);
        border-radius: var(--srh-r);
        padding: 0.8rem 1rem;
        box-shadow: var(--srh-shadow);
    }
    .telemetry-metric-num {
        font-family: 'Inter', sans-serif;
        font-size: 1.2rem;
        font-weight: 750;
        color: var(--srh-ink);
        line-height: 1.15;
        font-variant-numeric: tabular-nums;
    }
    .telemetry-metric-lbl {
        font-size: 0.72rem;
        color: var(--srh-faint);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    /* Featured story */
    a.featured-story-link { text-decoration: none !important; color: inherit !important; display: block; margin-bottom: 1.1rem; }
    .featured-story-card {
        background: var(--srh-surface);
        border: 1px solid var(--srh-line);
        border-radius: var(--srh-r);
        padding: 1.4rem 1.5rem;
        box-shadow: var(--srh-shadow);
    }
    .featured-story-card:hover {
        border-color: #D8D4CE;
        box-shadow: var(--srh-shadow-hover);
    }
    .featured-badge-bar {
        display: flex;
        gap: 0.45rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.7rem;
    }
    .badge-hero-top {
        color: var(--srh-accent-ink);
        font-family: 'Inter', sans-serif;
        font-size: 0.7rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    }
    .featured-story-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.3rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: var(--srh-ink);
        line-height: 1.4;
        margin-bottom: 0.55rem;
    }
    .featured-story-card:hover .featured-story-title {
        color: var(--srh-accent-ink);
    }
    .featured-story-desc {
        color: var(--srh-body);
        font-size: 0.92rem;
        line-height: 1.65;
        margin-bottom: 1rem;
        font-weight: 400;
    }
    .featured-story-footer {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        border-top: 1px solid var(--srh-line-soft);
        padding-top: 0.8rem;
        font-size: 0.78rem;
        color: var(--srh-faint);
        flex-wrap: wrap;
        font-weight: 500;
    }
    /* News cards */
    a.telemetry-card-link { text-decoration: none !important; color: inherit !important; display: block; margin-bottom: 0.7rem; }
    .telemetry-news-card {
        background: var(--srh-surface);
        border: 1px solid var(--srh-line);
        border-radius: var(--srh-r);
        padding: 1.05rem 1.2rem;
        box-shadow: var(--srh-shadow);
    }
    .telemetry-news-card:hover {
        border-color: #D8D4CE;
        box-shadow: var(--srh-shadow-hover);
    }
    .telemetry-news-card:hover .telemetry-card-title {
        color: var(--srh-accent-ink);
    }
    .telemetry-card-tags {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.5rem;
    }
    .chip-player {
        background: var(--srh-accent-soft);
        color: var(--srh-accent-ink);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 700;
    }
    .chip-squad {
        background: var(--srh-line-soft);
        color: var(--srh-muted);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .chip-league {
        background: var(--srh-line-soft);
        color: var(--srh-muted);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .chip-new-live {
        background: var(--srh-red-soft);
        color: var(--srh-red);
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        display: inline-flex;
        align-items: center;
        gap: 5px;
    }
    .chip-new-live::before {
        content: '';
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: currentColor;
    }
    .telemetry-card-title {
        font-family: 'Inter', sans-serif;
        font-size: 1.02rem;
        font-weight: 650;
        letter-spacing: -0.005em;
        color: var(--srh-ink);
        margin: 0 0 0.35rem 0;
        line-height: 1.45;
    }
    .telemetry-card-desc {
        color: var(--srh-body);
        font-size: 0.87rem;
        line-height: 1.6;
        margin: 0 0 0.8rem 0;
        font-weight: 400;
    }
    .telemetry-card-footer {
        display: flex;
        align-items: center;
        gap: 0.7rem;
        font-size: 0.76rem;
        color: var(--srh-faint);
        border-top: 1px solid var(--srh-line-soft);
        padding-top: 0.65rem;
        flex-wrap: wrap;
        font-weight: 500;
    }
    .source-tag {
        color: var(--srh-muted);
        font-weight: 600;
        display: inline-flex;
        align-items: center;
    }
    .time-tag {
        color: var(--srh-faint);
        font-weight: 500;
        font-variant-numeric: tabular-nums;
    }
    .link-action {
        margin-left: auto;
        color: var(--srh-accent-ink);
        font-weight: 650;
        font-size: 0.78rem;
    }
    /* Pulse timeline */
    .pulse-panel {
        background: var(--srh-surface);
        border: 1px solid var(--srh-line);
        border-radius: var(--srh-r);
        padding: 1.1rem 1.15rem;
        box-shadow: var(--srh-shadow);
    }
    .pulse-panel-title {
        font-family: 'Inter', sans-serif;
        font-size: 0.72rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: var(--srh-muted);
        margin-bottom: 0.9rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .pulse-item-dark {
        border-left: 2px solid var(--srh-line);
        padding-left: 0.7rem;
        margin-bottom: 0.85rem;
    }
    .pulse-time-dark {
        font-size: 0.7rem;
        color: var(--srh-faint);
        font-weight: 600;
        margin-bottom: 0.15rem;
        font-variant-numeric: tabular-nums;
    }
    .pulse-headline-dark {
        font-size: 0.83rem;
        color: var(--srh-body);
        font-weight: 550;
        line-height: 1.5;
        text-decoration: none;
        display: block;
    }
    .pulse-headline-dark:hover {
        color: var(--srh-accent-ink);
    }
    /* Matchday cards */
    .broadcast-match-card {
        background: var(--srh-surface);
        border: 1px solid var(--srh-line);
        border-radius: var(--srh-r);
        padding: 1.15rem 1.3rem;
        margin-bottom: 0.7rem;
        box-shadow: var(--srh-shadow);
    }
    .broadcast-match-card-live {
        box-shadow: inset 3px 0 0 var(--srh-red), var(--srh-shadow);
    }
    .broadcast-match-card:hover {
        border-color: #D8D4CE;
        box-shadow: var(--srh-shadow-hover);
    }
    .broadcast-match-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.6rem;
        flex-wrap: wrap;
    }
    .match-versus {
        font-family: 'Inter', sans-serif;
        font-size: 1.2rem;
        font-weight: 750;
        letter-spacing: -0.01em;
        color: var(--srh-ink);
        margin-bottom: 0.45rem;
        line-height: 1.35;
    }
    .match-meta {
        color: var(--srh-muted);
        font-size: 0.83rem;
        font-weight: 500;
    }
    .match-meta strong {
        color: var(--srh-body);
        font-weight: 600;
    }
    .match-players {
        color: var(--srh-body);
        font-size: 0.84rem;
        margin-top: 0.45rem;
    }
    .match-players strong {
        font-weight: 650;
        color: var(--srh-ink);
    }
    .status-pill {
        font-family: 'Inter', sans-serif;
        font-size: 0.68rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 3px 9px 3px 8px;
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .status-pill::before {
        content: '';
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: currentColor;
    }
    .status-pill-live { background: var(--srh-red-soft); color: var(--srh-red); }
    .status-pill-live::before { animation: live-pulse 2.4s ease-in-out infinite; }
    .status-pill-upcoming { background: var(--srh-line-soft); color: var(--srh-muted); }
    .status-pill-completed { background: var(--srh-line-soft); color: var(--srh-faint); }
    .match-league {
        font-size: 0.76rem;
        font-weight: 600;
        color: var(--srh-muted);
    }
    .match-venue {
        font-size: 0.76rem;
        color: var(--srh-faint);
    }
    .srh-crex-link {
        display: inline-block;
        margin-top: 0.6rem;
        color: var(--srh-accent-ink);
        font-weight: 650;
        font-size: 0.82rem;
        text-decoration: none;
    }
    .srh-crex-link:hover {
        text-decoration: underline;
    }
    /* Source favicon */
    .source-fav-icon {
        width: 14px;
        height: 14px;
        vertical-align: -2px;
        border-radius: 3px;
        margin-right: 5px;
        display: inline-block;
    }
    /* Squad directory */
    .squad-player-card {
        background: var(--srh-surface);
        border: 1px solid var(--srh-line);
        border-radius: var(--srh-r);
        padding: 1rem 1.1rem;
        box-shadow: var(--srh-shadow);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 138px;
    }
    .squad-player-card:hover {
        border-color: #D8D4CE;
        box-shadow: var(--srh-shadow-hover);
    }
    .squad-player-card-coach {
        box-shadow: inset 3px 0 0 var(--srh-accent), var(--srh-shadow);
    }
    .squad-player-card-captain {
        box-shadow: inset 3px 0 0 #D9A013, var(--srh-shadow);
    }
    .squad-coach-badge {
        color: var(--srh-accent-ink);
        background: var(--srh-accent-soft);
        padding: 2px 7px;
        border-radius: 5px;
        font-size: 0.66rem;
        font-weight: 750;
        letter-spacing: 0.06em;
    }
    .squad-captain-badge {
        color: var(--srh-amber-ink);
        background: var(--srh-amber-bg);
        padding: 2px 7px;
        border-radius: 5px;
        font-size: 0.66rem;
        font-weight: 750;
        letter-spacing: 0.06em;
    }
    .squad-tag {
        color: var(--srh-muted);
        background: var(--srh-line-soft);
        padding: 2px 7px;
        border-radius: 5px;
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.04em;
    }
    .squad-card-name {
        font-family: 'Inter', sans-serif;
        font-size: 0.97rem;
        font-weight: 700;
        letter-spacing: -0.005em;
        color: var(--srh-ink);
        margin-bottom: 0.2rem;
    }
    .squad-card-role {
        font-size: 0.8rem;
        color: var(--srh-muted);
        font-weight: 500;
        margin-bottom: 0.6rem;
    }
    .squad-card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid var(--srh-line-soft);
        padding-top: 0.55rem;
        font-size: 0.76rem;
        color: var(--srh-faint);
    }
    @media (max-width: 768px) {
        .block-container { padding-top: 1.2rem; }
        .srh-brand-title { font-size: 1.6rem; }
        .hero-fixture-card { padding: 1.2rem 1.2rem 1.2rem 1.4rem; }
        .hero-fixture-vs { font-size: 1.45rem; }
        .hero-fixture-right { border-left: none; padding-left: 0; text-align: left; width: 100%; }
        .hero-countdown-val { justify-content: flex-start; }
        .featured-story-title { font-size: 1.1rem; }
        .match-versus { font-size: 1.05rem; }
    }
    @media (prefers-reduced-motion: reduce) {
        .srh-live-pulse-dot,
        .hero-countdown-val-live::before,
        .status-pill-live::before {
            animation: none;
        }
    }
</style>
"""
def find_good_link_for_story(n):
    """Returns a valid article link, falling back to Google News search."""
    if n.get("link") and n["link"] != "#":
        return n["link"]
    return f"https://news.google.com/search?q={urllib.parse.quote(str(n.get('player_name', '')) + ' cricket')}"
def guess_which_league(title, summary):
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
def how_long_ago(pub_ts):
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
def is_this_story_fresh(pub_ts, hours=2):
    """Returns True if article published within last N hours."""
    if not pub_ts or pub_ts <= 0:
        return False
    return (time.time() - float(pub_ts)) < (hours * 3600)
def find_tiny_website_icon(link):
    """Generates Google favicon URL for source domain."""
    try:
        domain = urllib.parse.urlparse(link).netloc
        if domain:
            return f"https://www.google.com/s2/favicons?domain={domain}&sz=16"
    except Exception:
        pass
    return ""
def show_top_part(player_count, franchise_count=4):
    """Renders masthead: kicker, display title, dark status pill."""
    return f"""
    <div class='srh-masthead-kicker'>Sunrisers intelligence desk</div>
    <div class='srh-brand-header'>
        <div>
            <div class='srh-brand-title'><span class='highlight'>SRHXtra</span> Telemetry Engine</div>
            <div class='srh-brand-subtitle'>{player_count} players · {franchise_count} franchises · matchday, news &amp; squads</div>
        </div>
        <div class='srh-live-badge'>
            <span class='srh-live-pulse-dot'></span>
            <span><strong>Live</strong>&nbsp;· auto-ingest 15 min</span>
        </div>
    </div>
    """
def show_next_match_big_box(next_fixture, status="UPCOMING"):
    """Renders next fixture countdown telemetry bar with dynamic LIVE / UPCOMING status."""
    if not next_fixture:
        return ""
    status = next_fixture.get("status", status) or status
    vs = html_lib.escape(next_fixture.get("vs", ""))
    squad = html_lib.escape(next_fixture.get("squad", ""))
    league = html_lib.escape(next_fixture.get("league", ""))
    date_str = html_lib.escape(next_fixture.get("date_str", ""))
    match_time = html_lib.escape(next_fixture.get("time", ""))
    venue = html_lib.escape(next_fixture.get("venue", "TBD"))
    broadcast = html_lib.escape(next_fixture.get("broadcast", "Check local listings"))
    if status == "LIVE":
        card_class = "hero-fixture-card hero-fixture-card-live"
        tag_html = f"<div class='hero-fixture-tag hero-fixture-tag-live'>Matchday live · {league}</div>"
        val_html = "<div class='hero-countdown-val hero-countdown-val-live'>Live now</div>"
        lbl_html = "<div class='hero-countdown-lbl'>In progress</div>"
    elif status == "COMPLETED":
        card_class = "hero-fixture-card"
        tag_html = f"<div class='hero-fixture-tag'>Result · {league}</div>"
        val_html = "<div class='hero-countdown-val'>Full time</div>"
        lbl_html = "<div class='hero-countdown-lbl'>Completed</div>"
    else:
        card_class = "hero-fixture-card"
        tag_html = f"<div class='hero-fixture-tag'>Up next · {league}</div>"
        val_html = f"<div class='hero-countdown-val'>{html_lib.escape(match_time)}</div>"
        lbl_html = f"<div class='hero-countdown-lbl'>{html_lib.escape(date_str)}</div>"
    link_html = ""
    _hero_link = str(next_fixture.get("link", ""))
    if _hero_link.startswith("https://crex.com/cricket-live-score/"):
        link_attr = html_lib.escape(_hero_link, quote=True)
        link_html = (
            f"<a href='{link_attr}' target='_blank' rel='noopener' "
            f"class='srh-crex-link'>"
            f"Squad &amp; live score on Crex ↗</a>"
        )
    return f"""
    <div class='{card_class}'>
        <div class='hero-fixture-left'>
            {tag_html}
            <div class='hero-fixture-vs'>{squad} vs {vs}</div>
            <div class='hero-fixture-details'>
                <span><strong>{date_str}</strong> · {match_time}</span>
                <span>{venue}</span>
                <span>{broadcast}</span>
            </div>
            {link_html}
        </div>
        <div class='hero-fixture-right'>
            {val_html}
            {lbl_html}
        </div>
    </div>
    """
def show_numbers_at_top(source_count, player_count, live_count):
    """Renders top metric strip (number over label, no decoration)."""
    return f"""
    <div class='telemetry-strip'>
        <div class='telemetry-metric-pill'>
            <div>
                <div class='telemetry-metric-num'>{source_count}</div>
                <div class='telemetry-metric-lbl'>Sources</div>
            </div>
        </div>
        <div class='telemetry-metric-pill'>
            <div>
                <div class='telemetry-metric-num'>{player_count}</div>
                <div class='telemetry-metric-lbl'>Players</div>
            </div>
        </div>
        <div class='telemetry-metric-pill'>
            <div>
                <div class='telemetry-metric-num'>4</div>
                <div class='telemetry-metric-lbl'>Franchises</div>
            </div>
        </div>
        <div class='telemetry-metric-pill'>
            <div>
                <div class='telemetry-metric-num'>{live_count}</div>
                <div class='telemetry-metric-lbl'>Reports</div>
            </div>
        </div>
    </div>
    """
def show_big_story(n):
    """Renders top latest article in a prominent featured hero layout."""
    link = find_good_link_for_story(n)
    link_attr = html_lib.escape(link, quote=True)
    league = guess_which_league(n.get("title", ""), n.get("summary", ""))
    pub_ts = n.get("pub_timestamp", 0)
    ago = how_long_ago(pub_ts)
    favicon = find_tiny_website_icon(link)
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
        f"<span class='badge-hero-top'>Top story</span>"
        f"<span class='chip-player'>{player_name}</span>"
        f"<span class='chip-squad'>{franchise}</span>"
        f"<span class='chip-league'>{league}</span>"
        f"</div>"
        f"<div class='featured-story-title'>{clean_title}</div>"
        f"<div class='featured-story-desc'>{clean_summary}</div>"
        f"<div class='featured-story-footer'>"
        f"<span class='time-tag'>{ago}</span>"
        f"<span>{pub_at}</span>"
        f"<span class='source-tag'>{fav_html} {source}</span>"
        f"<span class='link-action'>Open ↗</span>"
        f"</div>"
        f"</div>"
        f"</a>"
    )
def show_story_card(n):
    """Renders a standard single-line clean news item card."""
    link = find_good_link_for_story(n)
    link_attr = html_lib.escape(link, quote=True)
    league = guess_which_league(n.get("title", ""), n.get("summary", ""))
    pub_ts = n.get("pub_timestamp", 0)
    ago = how_long_ago(pub_ts)
    new_badge = "<span class='chip-new-live'>New</span>" if is_this_story_fresh(pub_ts) else ""
    favicon = find_tiny_website_icon(link)
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
        f"<div class='telemetry-card-tags'>{new_badge}<span class='chip-player'>{player_name}</span><span class='chip-squad'>{franchise}</span><span class='chip-league'>{league}</span></div>"
        f"<div class='telemetry-card-title'>{clean_title}</div>"
        f"<div class='telemetry-card-desc'>{clean_summary}</div>"
        f"<div class='telemetry-card-footer'>"
        f"<span class='time-tag'>{ago}</span>"
        f"<span>{pub_at}</span>"
        f"<span class='source-tag'>{fav_html} {source}</span>"
        f"<span class='link-action'>Read ↗</span>"
        f"</div>"
        f"</div>"
        f"</a>"
    )
def show_small_timeline_story(n):
    """Renders compact sidebar live pulse timeline entry."""
    link = find_good_link_for_story(n)
    link_attr = html_lib.escape(link, quote=True)
    pub_ts = n.get("pub_timestamp", 0)
    ago = how_long_ago(pub_ts)
    raw_title = str(n.get("title", "")).replace("\n", " ").strip()
    headline = html_lib.escape(raw_title[:65] + ("..." if len(raw_title) > 65 else ""))
    player_name = html_lib.escape(str(n.get("player_name", "")).strip())
    return (
        f"<div class='pulse-item-dark'>"
        f"<div class='pulse-time-dark'>{ago} · {player_name}</div>"
        f"<a href='{link_attr}' target='_blank' class='pulse-headline-dark'>{headline}</a>"
        f"</div>"
    )
def show_match_card(item, status="UPCOMING"):
    """Renders fixture item in broadcast infographic format.

    Live Crex fixtures carry `link`, `srh_players` and `franchises`; static
    legacy fixtures omit them and still render cleanly.
    """
    status = item.get("status", status) or status
    if status == "LIVE":
        status_html = "<span class='status-pill status-pill-live'>Live now</span>"
        card_extra_class = " broadcast-match-card-live"
    elif status == "COMPLETED":
        status_html = "<span class='status-pill status-pill-completed'>Completed</span>"
        card_extra_class = ""
    else:
        status_html = "<span class='status-pill status-pill-upcoming'>Upcoming</span>"
        card_extra_class = ""
    meta_bits = []
    if item.get("league"):
        meta_bits.append(f"<span class='match-league'>{html_lib.escape(str(item['league']))}</span>")
    if item.get("venue"):
        meta_bits.append(f"<span class='match-venue'>{html_lib.escape(str(item['venue']))}</span>")
    if item.get("broadcast"):
        meta_bits.append(f"<span class='match-venue'>{html_lib.escape(str(item['broadcast']))}</span>")
    meta_html = " · ".join(meta_bits)
    squad = html_lib.escape(str(item.get("squad", "")))
    vs = html_lib.escape(str(item.get("vs", "")))
    match_time = html_lib.escape(str(item.get("time", "")))
    date_str = html_lib.escape(str(item.get("date_str", "")))
    players = html_lib.escape(str(item.get("players", "")))
    link_html = ""
    _link = str(item.get("link", ""))
    if _link.startswith("https://crex.com/cricket-live-score/"):
        link_attr = html_lib.escape(_link, quote=True)
        link_html = (
            f"<a href='{link_attr}' target='_blank' rel='noopener' "
            f"class='srh-crex-link'>"
            f"Squad &amp; live score on Crex ↗</a>"
        )
    franchise_html = ""
    if item.get("franchises"):
        chips = "".join(
            f"<span class='chip-squad'>{html_lib.escape(str(f))}</span>"
            for f in item["franchises"]
        )
        franchise_html = f"<div style='margin-top:0.5rem;display:flex;gap:0.4rem;flex-wrap:wrap;'>{chips}</div>"
    return (
        f"<div class='broadcast-match-card{card_extra_class}'>"
        f"<div class='broadcast-match-header'>"
        f"{status_html}"
        f"<span class='match-league'>{squad}</span>"
        f"</div>"
        f"<div class='match-versus'>{squad} vs {vs}</div>"
        f"<div class='match-meta'><strong>{date_str}</strong> · {match_time}</div>"
        f"<div class='match-meta'>{meta_html}</div>"
        f"<div class='match-players'><strong>Sunrisers in squad:</strong> {players}</div>"
        f"{franchise_html}"
        f"{link_html}"
        f"</div>"
    )

COUNTRY_FLAGS = {
    "India": "🇮🇳",
    "Australia": "🇦🇺",
    "South Africa": "🇿🇦",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "Sri Lanka": "🇱🇰",
    "New Zealand": "🇳🇿",
    "Pakistan": "🇵🇰",
    "Bangladesh": "🇧🇩",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
}

def show_player_card(member, franchise_name=None):
    """Renders a sleek athletic card for an official squad member."""
    name = html_lib.escape(member.get("name", ""))
    role = html_lib.escape(member.get("role", "Squad Member"))
    country = html_lib.escape(member.get("country", ""))
    notes = html_lib.escape(member.get("notes", "")) if member.get("notes") else ""
    is_captain = bool(member.get("captain", False)) or "(c)" in name.lower() or "captain" in role.lower()
    is_coach = "coach" in role.lower() or "vettori" in name.lower() or "birrell" in name.lower()
    is_wk = "(wk)" in name.lower() or "wicket-keeper" in role.lower() or "wicket-keeper" in str(member.get("role", "")).lower()

    flag = COUNTRY_FLAGS.get(member.get("country", ""), "🏏")

    card_classes = ["squad-player-card"]
    badges = []

    if is_coach:
        card_classes.append("squad-player-card-coach")
        badges.append("<span class='squad-coach-badge'>Head coach</span>")
    elif is_captain:
        card_classes.append("squad-player-card-captain")
        badges.append("<span class='squad-captain-badge'>Captain</span>")

    if is_wk:
        badges.append("<span class='squad-tag'>WK</span>")

    # Overseas detection based on franchise home country
    is_overseas = False
    f_str = str(franchise_name or "")
    if "Hyderabad" in f_str or not franchise_name:
        is_overseas = (country != "India" and not is_coach)
    elif "Eastern Cape" in f_str:
        is_overseas = (country != "South Africa" and not is_coach)
    elif "Leeds" in f_str:
        is_overseas = (country != "England" and not is_coach)

    if is_overseas:
        badges.append("<span class='squad-tag'>Overseas</span>")

    badges_html = f"<div style='display:flex;gap:0.35rem;flex-wrap:wrap;'>{''.join(badges)}</div>" if badges else "<div></div>"

    notes_html = f"<span style='color:var(--srh-accent-ink);font-size:0.75rem;font-weight:600;'>{notes}</span>" if notes else ""

    return (
        f"<div class='{' '.join(card_classes)}'>"
        f"  <div>"
        f"    <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.5rem;gap:0.4rem;'>"
        f"      {badges_html}"
        f"      <span style='font-size:1.15rem;line-height:1;' title='{country}'>{flag}</span>"
        f"    </div>"
        f"    <div class='squad-card-name'>{name}</div>"
        f"    <div class='squad-card-role'>{role}</div>"
        f"  </div>"
        f"  <div class='squad-card-footer'>"
        f"    <span>{country}</span>"
        f"    {notes_html}"
        f"  </div>"
        f"</div>"
    )

# Old names, kept so older guides still work.
get_custom_css = get_website_style
render_header_banner = show_top_part
render_next_match_hero = show_next_match_big_box
render_telemetry_metrics = show_numbers_at_top
render_featured_hero_news = show_big_story
render_telemetry_news_card = show_story_card
render_telemetry_pulse_item = show_small_timeline_story
render_broadcast_match_card = show_match_card
render_squad_member_card = show_player_card
safe_article_link = find_good_link_for_story
detect_league_badge = guess_which_league
time_ago = how_long_ago
is_new_article = is_this_story_fresh
get_favicon_url = find_tiny_website_icon
parse_fixture_datetime = read_match_date_and_time
get_fixture_status = is_match_live_now_or_later
