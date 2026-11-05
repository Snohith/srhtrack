"""
SRHXtra — premium editorial theme and dynamic matchday status engine.

Design system: warm neutral surfaces, one Sunrisers orange accent, a
4px/8px spacing scale, 12–16px radii, and Inter with a clear type scale.
Live status is derived from the fixture start time (4-hour live window).
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
    /* ── Design tokens ───────────────────────────────────────────────────
       4px/8px spacing scale, one brand color, warm neutral surfaces.
       16px body copy; 12–14px metadata. Text colors pass WCAG AA on white. */
    @import url('https://fonts.googleapis.com/css2?family=Inter:opsz,wght@14..32,400..800&display=swap');
    :root {
        --sr-bg: #F5F5F2;
        --sr-surface: #FFFFFF;
        --sr-surface-soft: #FAFAF8;
        --sr-surface-sunken: #F1F1ED;
        --sr-ink: #17191E;
        --sr-body: #3A404B;
        --sr-muted: #5C6472;
        --sr-faint: #636B78;
        --sr-line: #E5E4DF;
        --sr-line-soft: #EFEEEA;
        --sr-accent: #EA580C;
        --sr-accent-ink: #C2410C;
        --sr-accent-soft: #FFF3EA;
        --sr-green: #15803D;
        --sr-green-soft: #E9F7EF;
        --sr-red: #B42318;
        --sr-red-soft: #FEECEB;
        --sr-amber: #8A5A00;
        --sr-amber-soft: #FFF6DD;
        --sr-night: #17191E;
        --sr-night-raise: #20232A;
        --sr-night-line: #2E323B;
        --sr-night-ink: #F6F7F9;
        --sr-night-muted: #B7BDC7;
        --sr-night-faint: #8B93A1;
        --sr-r-xs: 6px;
        --sr-r-sm: 8px;
        --sr-r: 12px;
        --sr-r-lg: 16px;
        --sr-pill: 999px;
        --sr-s1: 4px;
        --sr-s2: 8px;
        --sr-s3: 12px;
        --sr-s4: 16px;
        --sr-s5: 24px;
        --sr-s6: 32px;
        --sr-s7: 48px;
        --sr-s8: 64px;
        --sr-shadow-xs: 0 1px 2px rgba(23, 25, 30, 0.04);
        --sr-shadow-sm: 0 2px 4px rgba(23, 25, 30, 0.04), 0 1px 2px rgba(23, 25, 30, 0.03);
        --sr-shadow-md: 0 12px 28px -16px rgba(23, 25, 30, 0.25), 0 2px 6px rgba(23, 25, 30, 0.04);
        --sr-ease: cubic-bezier(0.2, 0.7, 0.3, 1);
    }

    /* ── Base ───────────────────────────────────────────────────────────── */
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    body, .stApp, [data-testid="stAppViewContainer"] {
        background: var(--sr-bg) !important;
        color: var(--sr-ink) !important;
    }
    ::selection { background: #FFD9BF; color: var(--sr-ink); }
    :focus-visible { outline: 2px solid var(--sr-accent-ink); outline-offset: 3px; border-radius: var(--sr-r-xs); }
    .block-container {
        max-width: 76rem;
        padding: 2rem 2rem 4rem 2rem;
    }
    * { scrollbar-width: thin; scrollbar-color: #D8D6D0 transparent; }
    #MainMenu, [data-testid="stAppDeployButton"], [data-testid="stStatusWidget"] { display: none !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stDecoration"] { display: none !important; }
    [data-testid="stSidebarCollapseButton"] button { color: var(--sr-muted) !important; }

    /* ── Sidebar ────────────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: var(--sr-surface) !important;
        border-right: 1px solid var(--sr-line) !important;
    }
    section[data-testid="stSidebar"] > div { background: var(--sr-surface) !important; }
    section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { padding: 0.75rem 1.25rem 0.25rem !important; }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding: 0.75rem 1.25rem 2rem !important; }
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown div,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] .stCaption p { color: var(--sr-body) !important; }
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] .stCaption p {
        font-size: 0.75rem !important;
        line-height: 1.5 !important;
        color: var(--sr-faint) !important;
    }
    section[data-testid="stSidebar"] hr {
        margin: 1.25rem 0 !important;
        border: none !important;
        border-top: 1px solid var(--sr-line) !important;
    }
    section[data-testid="stSidebar"] code {
        background: var(--sr-surface-sunken) !important;
        border: 0 !important;
        color: var(--sr-body) !important;
        border-radius: var(--sr-r-xs) !important;
        padding: 1px 5px !important;
        font-family: inherit !important;
        font-size: 0.8125rem !important;
    }
    section[data-testid="stSidebar"] details {
        border: 1px solid var(--sr-line) !important;
        border-radius: var(--sr-r-sm) !important;
        background: var(--sr-surface-soft) !important;
    }
    section[data-testid="stSidebar"] details summary {
        padding: 0.7rem 0.85rem !important;
        font-size: 0.875rem !important;
        font-weight: 600 !important;
        color: var(--sr-ink) !important;
    }
    section[data-testid="stSidebar"] details summary:hover { color: var(--sr-accent-ink) !important; }
    section[data-testid="stSidebar"] .stSpinner > div { border-top-color: var(--sr-accent) !important; }

    .srh-side-brand {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-size: 1.0625rem;
        font-weight: 750;
        letter-spacing: -0.02em;
        color: var(--sr-ink) !important;
        line-height: 1;
    }
    .srh-brand-mark {
        width: 28px;
        height: 28px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: var(--sr-r-sm);
        background: var(--sr-ink);
        color: #FFFFFF;
        font-size: 0.75rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        flex-shrink: 0;
    }
    .srh-side-tagline { color: var(--sr-faint) !important; font-size: 0.8125rem; margin-top: 0.35rem; }
    .srh-side-label {
        display: block;
        font-size: 0.6875rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        color: var(--sr-faint) !important;
    }
    .srh-side-meta { display: grid; gap: 0.9rem; }
    .srh-side-meta-row { display: flex; flex-direction: column; gap: 0.2rem; }
    .srh-side-value { color: var(--sr-ink); font-size: 0.875rem; font-weight: 600; line-height: 1.4; }

    /* ── Typography & section scaffolding ──────────────────────────────── */
    .srh-masthead-kicker {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        font-size: 0.6875rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--sr-accent-ink);
        margin-bottom: 0.55rem;
    }
    .srh-masthead-kicker::before {
        content: '';
        width: 18px;
        height: 1px;
        background: var(--sr-accent);
        flex-shrink: 0;
    }
    .srh-brand-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1.25rem;
        flex-wrap: wrap;
        padding-bottom: 1.25rem;
        border-bottom: 1px solid var(--sr-line);
    }
    h1.srh-brand-title {
        font-size: clamp(1.75rem, 1.35rem + 1.35vw, 2.55rem);
        font-weight: 780;
        letter-spacing: -0.04em;
        line-height: 1.06;
        color: var(--sr-ink);
        margin: 0;
        max-width: 20ch;
    }
    .srh-brand-title .highlight { color: var(--sr-accent); }
    .srh-brand-subtitle {
        color: var(--sr-muted);
        font-size: 0.9375rem;
        line-height: 1.6;
        margin: 0.55rem 0 0;
        max-width: 58ch;
    }
    .srh-live-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        min-height: 36px;
        padding: 0.45rem 0.8rem;
        border-radius: var(--sr-pill);
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        box-shadow: var(--sr-shadow-xs);
        color: var(--sr-muted);
        font-size: 0.6875rem;
        font-weight: 650;
        letter-spacing: 0.02em;
        white-space: nowrap;
    }
    .srh-live-badge strong { color: var(--sr-ink); font-weight: 700; }
    .srh-section-title {
        font-size: 1.125rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--sr-ink);
        margin: 0 0 0.25rem;
    }
    .srh-section-sub {
        color: var(--sr-muted);
        font-size: 0.9375rem;
        line-height: 1.6;
        margin: 0 0 1rem;
        max-width: 76ch;
    }
    .srh-section-sub a {
        color: var(--sr-accent-ink) !important;
        font-weight: 600;
        text-decoration: underline;
        text-underline-offset: 2px;
    }
    .srh-section-sub a:hover { color: var(--sr-accent) !important; }
    .srh-date-group {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        font-size: 0.6875rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        color: var(--sr-faint);
        margin: 1.5rem 0 0.75rem;
    }
    .srh-date-group::after { content: ''; flex: 1; height: 1px; background: var(--sr-line); }
    .srh-note { font-size: 0.8125rem; color: var(--sr-faint); }
    .sr-only {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0 0 0 0);
        white-space: nowrap;
        border: 0;
    }
    .srh-note-title {
        font-size: 0.875rem;
        font-weight: 650;
        color: var(--sr-body);
        margin: 0.5rem 0 0.75rem;
    }
    /* Our headings render through st.html; never inherit Streamlit heading padding. */
    .srh-brand-title, .hero-fixture-vs, .featured-story-title, .telemetry-card-title,
    .match-versus, .squad-card-name, .pulse-panel-title, .srh-date-group,
    .srh-empty h3, .srh-note-title, .srh-section-title { padding: 0 !important; }
    .srh-result-count {
        font-size: 0.8125rem;
        color: var(--sr-faint);
        margin: 0.4rem 0 0.9rem;
    }
    .srh-result-count strong { color: var(--sr-ink); font-weight: 650; }
    .srh-active-filter {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: var(--sr-accent-soft);
        color: var(--sr-accent-ink);
        border-radius: var(--sr-pill);
        padding: 0.25rem 0.65rem;
        font-size: 0.75rem;
        font-weight: 650;
        margin: 0 0 0.9rem;
    }
    .srh-active-filter span { color: var(--sr-muted); font-weight: 600; }
    .srh-empty {
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        border-radius: var(--sr-r);
        padding: 2.5rem 1.5rem;
        text-align: center;
        box-shadow: var(--sr-shadow-xs);
        margin: 1rem 0;
    }
    .srh-empty h3 { font-size: 1rem; font-weight: 700; color: var(--sr-ink); margin: 0 0 0.3rem; }
    .srh-empty p { font-size: 0.9375rem; color: var(--sr-muted); line-height: 1.6; margin: 0 auto; max-width: 52ch; }

    /* ── Tabs ───────────────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1.75rem;
        background: transparent;
        padding: 0;
        border: none;
        border-bottom: 1px solid var(--sr-line);
        border-radius: 0;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        min-height: 44px;
        padding: 0 0.15rem;
        border-radius: 0;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        margin-bottom: -1px;
        color: var(--sr-faint);
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9375rem;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab"]:hover { color: var(--sr-ink); }
    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: var(--sr-ink) !important;
        font-weight: 700 !important;
        border-bottom: 2px solid var(--sr-accent) !important;
        box-shadow: none;
    }
    .stTabs [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"] { display: none !important; }

    /* ── Inputs, selects, buttons ───────────────────────────────────────── */
    .stTextInput label, .stSelectbox label, .stMultiSelect label, .stCheckbox label {
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        color: var(--sr-muted) !important;
        letter-spacing: 0.01em;
        margin-bottom: 0.3rem !important;
    }
    .stTextInput div[data-baseweb="input"],
    .stTextInput div[data-baseweb="base-input"] {
        background: var(--sr-surface) !important;
        border: 1px solid var(--sr-line) !important;
        border-radius: 10px !important;
        box-shadow: var(--sr-shadow-xs) !important;
        transition: border-color 0.16s var(--sr-ease), box-shadow 0.16s var(--sr-ease);
    }
    .stTextInput div[data-baseweb="input"]:focus-within,
    .stTextInput div[data-baseweb="base-input"]:focus-within {
        border-color: var(--sr-accent) !important;
        box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.14) !important;
    }
    .stTextInput input {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        color: var(--sr-ink) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 1rem !important;
        min-height: 44px !important;
        padding: 0.6rem 0.8rem !important;
    }
    .stTextInput input::placeholder { color: var(--sr-faint) !important; opacity: 1; }
    .stSelectbox div[data-baseweb="select"] > div {
        min-height: 44px;
        background: var(--sr-surface) !important;
        border: 1px solid var(--sr-line) !important;
        border-radius: 10px !important;
        color: var(--sr-ink) !important;
        font-size: 0.9375rem !important;
        box-shadow: var(--sr-shadow-xs);
        transition: border-color 0.16s var(--sr-ease), box-shadow 0.16s var(--sr-ease);
    }
    .stSelectbox div[data-baseweb="select"] > div:hover { border-color: #D2D0C9 !important; }
    .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: var(--sr-accent) !important;
        box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.14) !important;
    }
    .stSelectbox svg { fill: var(--sr-muted) !important; }
    [data-baseweb="popover"] [role="listbox"] {
        border-radius: var(--sr-r-sm) !important;
        border: 1px solid var(--sr-line) !important;
        box-shadow: var(--sr-shadow-md) !important;
        background: var(--sr-surface) !important;
    }
    [data-baseweb="popover"] [role="option"] { min-height: 40px; font-size: 0.9rem; }
    .stCheckbox input { accent-color: var(--sr-accent); }
    .stButton button, .stDownloadButton button, .stFormSubmitButton button {
        min-height: 44px;
        border-radius: 10px !important;
        border: 1px solid var(--sr-line) !important;
        background: var(--sr-surface) !important;
        color: var(--sr-ink) !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        box-shadow: var(--sr-shadow-xs) !important;
        transition: background 0.16s var(--sr-ease), border-color 0.16s var(--sr-ease), color 0.16s var(--sr-ease), box-shadow 0.16s var(--sr-ease);
    }
    .stButton button:hover, .stDownloadButton button:hover, .stFormSubmitButton button:hover {
        background: var(--sr-surface-soft) !important;
        border-color: #D2D0C9 !important;
        color: var(--sr-ink) !important;
        box-shadow: var(--sr-shadow-sm) !important;
    }
    .stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {
        background: var(--sr-ink) !important;
        border-color: var(--sr-ink) !important;
        color: #FFFFFF !important;
    }
    .stButton button[kind="primary"]:hover, .stButton button[data-testid="stBaseButton-primary"]:hover {
        background: var(--sr-night-raise) !important;
        border-color: var(--sr-night-raise) !important;
        color: #FFFFFF !important;
    }
    .stButton button:disabled { opacity: 0.55; box-shadow: none !important; }
    .stButton button p { font-weight: 600 !important; }
    [data-testid="stSidebar"] .stButton button[kind="primary"] { background: var(--sr-ink) !important; color: #FFFFFF !important; }

    /* ── Global coverage strip ──────────────────────────────────────────── */
    .telemetry-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        border-radius: var(--sr-r);
        box-shadow: var(--sr-shadow-xs);
        margin: 0 0 1.5rem;
        overflow: hidden;
    }
    .telemetry-metric-pill {
        display: flex;
        align-items: baseline;
        gap: 0.4rem;
        padding: 0.85rem 1rem;
        border-left: 1px solid var(--sr-line-soft);
        min-width: 0;
    }
    .telemetry-metric-pill:first-child { border-left: 0; }
    .telemetry-metric-num {
        font-size: 1.25rem;
        font-weight: 750;
        line-height: 1.15;
        letter-spacing: -0.02em;
        color: var(--sr-ink);
        font-variant-numeric: tabular-nums;
    }
    .telemetry-metric-lbl {
        font-size: 0.6875rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: var(--sr-faint);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* ── Matchday hero ──────────────────────────────────────────────────── */
    .hero-fixture-card {
        position: relative;
        overflow: hidden;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1.5rem;
        background: linear-gradient(135deg, #17191E 0%, #1D2026 100%);
        border: 1px solid #101216;
        border-radius: var(--sr-r-lg);
        padding: 1.5rem 1.6rem;
        margin: 1.25rem 0 1rem;
        box-shadow: 0 18px 40px -28px rgba(23, 25, 30, 0.55);
    }
    .hero-fixture-card::after {
        content: '';
        position: absolute;
        right: -80px;
        top: -120px;
        width: 280px;
        height: 280px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(234, 88, 12, 0.18), transparent 70%);
        pointer-events: none;
    }
    .hero-fixture-left { flex: 1; min-width: 260px; position: relative; z-index: 1; }
    .hero-fixture-tag {
        font-size: 0.6875rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #FF9A62;
        margin-bottom: 0.45rem;
    }
    .hero-fixture-tag-live { color: #FF9A62; }
    h2.hero-fixture-vs {
        font-size: 1.75rem;
        font-weight: 780;
        letter-spacing: -0.03em;
        color: var(--sr-night-ink);
        margin: 0 0 0.55rem;
        line-height: 1.15;
    }
    .hero-fixture-details {
        display: flex;
        gap: 0.4rem 1.1rem;
        font-size: 0.8125rem;
        color: var(--sr-night-muted);
        font-weight: 500;
        flex-wrap: wrap;
    }
    .hero-fixture-details strong { color: var(--sr-night-ink); font-weight: 650; }
    .hero-fixture-card .srh-crex-link { color: #FF9A62 !important; margin-top: 0.7rem; }
    .hero-fixture-right {
        text-align: right;
        padding-left: 1.3rem;
        border-left: 1px solid var(--sr-night-line);
        position: relative;
        z-index: 1;
    }
    .hero-countdown-val {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 0.55rem;
        font-size: 1.75rem;
        font-weight: 780;
        letter-spacing: -0.025em;
        color: var(--sr-night-ink);
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
    }
    .hero-countdown-val::before {
        content: '';
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: var(--sr-accent);
        flex-shrink: 0;
    }
    .hero-countdown-val-live { color: #FFFFFF; }
    .hero-countdown-val-live::before { background: #FF6B61; animation: live-pulse 2.4s ease-in-out infinite; }
    .hero-countdown-lbl {
        font-size: 0.6875rem;
        color: var(--sr-night-faint);
        text-transform: uppercase;
        font-weight: 650;
        letter-spacing: 0.08em;
        margin-top: 0.3rem;
    }
    .srh-live-pulse-dot {
        width: 7px;
        height: 7px;
        background: var(--sr-green);
        border-radius: 50%;
        animation: live-pulse 2.4s ease-in-out infinite;
        flex-shrink: 0;
    }
    @keyframes live-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.35; }
    }

    /* ── Stats ──────────────────────────────────────────────────────────── */
    .srh-stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 0.75rem;
        margin: 1rem 0 1.5rem;
    }
    .srh-stat {
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        border-radius: var(--sr-r);
        padding: 0.875rem 1rem;
        box-shadow: var(--sr-shadow-xs);
    }
    .srh-stat-num {
        font-size: 1.375rem;
        font-weight: 750;
        line-height: 1.15;
        letter-spacing: -0.02em;
        color: var(--sr-ink);
        font-variant-numeric: tabular-nums;
    }
    .srh-stat.is-info .srh-stat-num { font-size: 1.0625rem; letter-spacing: -0.01em; line-height: 1.35; }
    .srh-stat-lbl {
        margin-top: 0.2rem;
        font-size: 0.6875rem;
        font-weight: 650;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: var(--sr-faint);
        line-height: 1.4;
    }

    /* ── Featured story ─────────────────────────────────────────────────── */
    a.featured-story-link {
        display: block;
        color: inherit !important;
        text-decoration: none !important;
        margin-bottom: 1rem;
        border-radius: var(--sr-r-lg);
    }
    a.featured-story-link:focus-visible { outline: 2px solid var(--sr-accent-ink); outline-offset: 3px; }
    .featured-story-card {
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        border-radius: var(--sr-r-lg);
        padding: 1.5rem 1.6rem;
        box-shadow: var(--sr-shadow-xs);
        transition: border-color 0.18s var(--sr-ease), box-shadow 0.18s var(--sr-ease), transform 0.18s var(--sr-ease);
    }
    a.featured-story-link:hover .featured-story-card {
        border-color: #D6D3CB;
        box-shadow: var(--sr-shadow-md);
        transform: translateY(-1px);
    }
    .featured-badge-bar {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.8rem;
    }
    .badge-hero-top {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        background: var(--sr-accent-soft);
        color: var(--sr-accent-ink);
        border-radius: var(--sr-pill);
        padding: 0.2rem 0.55rem;
        font-size: 0.6875rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .badge-hero-top::before {
        content: '';
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: currentColor;
    }
    h2.featured-story-title {
        font-size: clamp(1.2rem, 1.05rem + 0.5vw, 1.45rem);
        font-weight: 700;
        letter-spacing: -0.025em;
        color: var(--sr-ink);
        line-height: 1.35;
        margin: 0 0 0.55rem;
        display: -webkit-box;
        -webkit-line-clamp: 4;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    a.featured-story-link:hover h2.featured-story-title { color: var(--sr-accent-ink); }
    .featured-story-desc {
        color: var(--sr-body);
        font-size: 1rem;
        line-height: 1.65;
        margin: 0 0 1rem;
        font-weight: 400;
        display: -webkit-box !important;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden !important;
    }
    .featured-story-footer {
        display: flex;
        align-items: center;
        gap: 0.4rem 0.75rem;
        flex-wrap: wrap;
        border-top: 1px solid var(--sr-line-soft);
        padding-top: 0.8rem;
        font-size: 0.75rem;
        color: var(--sr-faint);
        font-weight: 500;
    }

    /* ── Story cards ────────────────────────────────────────────────────── */
    a.telemetry-card-link {
        display: block;
        color: inherit !important;
        text-decoration: none !important;
        margin-bottom: 0.75rem;
        border-radius: var(--sr-r);
    }
    a.telemetry-card-link:focus-visible { outline: 2px solid var(--sr-accent-ink); outline-offset: 3px; }
    .telemetry-news-card {
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        border-radius: var(--sr-r);
        padding: 1rem 1.2rem;
        box-shadow: var(--sr-shadow-xs);
        transition: border-color 0.18s var(--sr-ease), box-shadow 0.18s var(--sr-ease), transform 0.18s var(--sr-ease);
    }
    a.telemetry-card-link:hover .telemetry-news-card {
        border-color: #D6D3CB;
        box-shadow: var(--sr-shadow-sm);
        transform: translateY(-1px);
    }
    .telemetry-card-tags {
        display: flex;
        gap: 0.4rem;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 0.5rem;
    }
    .chip-player, .chip-squad, .chip-league, .chip-new {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        padding: 0.18rem 0.5rem;
        border-radius: var(--sr-pill);
        font-size: 0.6875rem;
        font-weight: 650;
        line-height: 1.4;
        white-space: nowrap;
    }
    .chip-player { background: var(--sr-accent-soft); color: var(--sr-accent-ink); }
    .chip-squad { background: var(--sr-surface-sunken); color: var(--sr-muted); }
    .chip-league { background: var(--sr-surface-sunken); color: var(--sr-muted); }
    .chip-new {
        background: var(--sr-green-soft);
        color: var(--sr-green);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .chip-new::before { content: ''; width: 5px; height: 5px; border-radius: 50%; background: currentColor; }
    h3.telemetry-card-title {
        font-size: 1.0625rem;
        font-weight: 650;
        letter-spacing: -0.01em;
        color: var(--sr-ink);
        margin: 0 0 0.35rem;
        line-height: 1.45;
    }
    a.telemetry-card-link:hover h3.telemetry-card-title { color: var(--sr-accent-ink); }
    .telemetry-card-desc {
        color: var(--sr-body);
        font-size: 1rem;
        line-height: 1.6;
        margin: 0 0 0.8rem;
        font-weight: 400;
        display: -webkit-box !important;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden !important;
    }
    .telemetry-card-footer {
        display: flex;
        align-items: center;
        gap: 0.4rem 0.75rem;
        flex-wrap: wrap;
        font-size: 0.75rem;
        color: var(--sr-faint);
        border-top: 1px solid var(--sr-line-soft);
        padding-top: 0.65rem;
        font-weight: 500;
    }
    .source-tag { color: var(--sr-muted); font-weight: 600; display: inline-flex; align-items: center; }
    .time-tag { color: var(--sr-faint); font-weight: 500; font-variant-numeric: tabular-nums; }
    .link-action {
        margin-left: auto;
        padding-left: 0.75rem;
        border-left: 1px solid var(--sr-line);
        color: var(--sr-accent-ink);
        font-weight: 650;
        font-size: 0.8125rem;
        white-space: nowrap;
    }
    .source-fav-icon {
        width: 16px;
        height: 16px;
        vertical-align: -3px;
        border-radius: 3px;
        margin-right: 5px;
        display: inline-block;
    }

    /* ── Latest headlines rail ──────────────────────────────────────────── */
    .pulse-panel {
        position: sticky;
        top: 1rem;
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        border-radius: var(--sr-r);
        padding: 1.1rem 1.15rem;
        box-shadow: var(--sr-shadow-xs);
    }
    h2.pulse-panel-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        margin: 0 0 0.9rem;
        font-size: 0.6875rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--sr-faint);
    }
    ol.pulse-list { list-style: none; margin: 0; padding: 0; }
    .pulse-item-dark {
        position: relative;
        padding: 0 0 0.85rem 0.8rem;
        margin: 0 0 0.85rem;
        border-left: 1px solid var(--sr-line);
    }
    .pulse-item-dark:last-child { margin-bottom: 0; padding-bottom: 0; }
    .pulse-item-dark::before {
        content: '';
        position: absolute;
        left: -3px;
        top: 0.3rem;
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: var(--sr-line);
    }
    .pulse-item-dark:first-child::before { background: var(--sr-accent); }
    .pulse-time-dark {
        font-size: 0.6875rem;
        color: var(--sr-faint);
        font-weight: 600;
        margin-bottom: 0.15rem;
        font-variant-numeric: tabular-nums;
    }
    .pulse-panel a.pulse-headline-dark {
        display: block;
        font-size: 0.875rem;
        color: var(--sr-body) !important;
        font-weight: 550;
        line-height: 1.5;
        text-decoration: none !important;
    }
    .pulse-panel a.pulse-headline-dark:hover { color: var(--sr-accent-ink) !important; }

    /* ── Matchday cards ─────────────────────────────────────────────────── */
    .broadcast-match-card {
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        border-radius: var(--sr-r);
        padding: 1.15rem 1.3rem;
        margin-bottom: 0.75rem;
        box-shadow: var(--sr-shadow-xs);
        transition: border-color 0.18s var(--sr-ease), box-shadow 0.18s var(--sr-ease);
    }
    .broadcast-match-card:hover { border-color: #D6D3CB; box-shadow: var(--sr-shadow-sm); }
    .broadcast-match-card-live {
        border-color: #F1C4C0;
        box-shadow: inset 3px 0 0 var(--sr-red), var(--sr-shadow-xs);
    }
    .broadcast-match-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.6rem;
        flex-wrap: wrap;
    }
    h3.match-versus {
        font-size: 1.125rem;
        font-weight: 700;
        letter-spacing: -0.015em;
        color: var(--sr-ink);
        margin: 0 0 0.45rem;
        line-height: 1.35;
    }
    .match-meta { color: var(--sr-muted); font-size: 0.875rem; font-weight: 500; line-height: 1.6; }
    .match-meta strong { color: var(--sr-body); font-weight: 600; }
    .match-players { color: var(--sr-body); font-size: 0.875rem; margin-top: 0.45rem; line-height: 1.6; }
    .match-players strong { font-weight: 650; color: var(--sr-ink); }
    .match-franchises { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.55rem; }
    .status-pill {
        font-size: 0.6875rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 3px 9px 3px 8px;
        border-radius: var(--sr-pill);
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .status-pill::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
    .status-pill-live { background: var(--sr-red-soft); color: var(--sr-red); }
    .status-pill-live::before { animation: live-pulse 2.4s ease-in-out infinite; }
    .status-pill-upcoming { background: var(--sr-surface-sunken); color: var(--sr-muted); }
    .status-pill-completed { background: var(--sr-surface-sunken); color: var(--sr-faint); }
    .match-league { font-size: 0.75rem; font-weight: 600; color: var(--sr-muted); }
    .match-venue { font-size: 0.75rem; color: var(--sr-faint); }
    .srh-crex-link {
        display: inline-block;
        margin-top: 0.6rem;
        color: var(--sr-accent-ink) !important;
        font-weight: 650;
        font-size: 0.8125rem;
        text-decoration: none !important;
    }
    .srh-crex-link:hover { color: var(--sr-accent) !important; text-decoration: underline !important; }

    /* ── Squad directory ────────────────────────────────────────────────── */
    .srh-card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .squad-player-card {
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 122px;
        background: var(--sr-surface);
        border: 1px solid var(--sr-line);
        border-radius: var(--sr-r);
        padding: 1rem 1.05rem;
        box-shadow: var(--sr-shadow-xs);
        transition: border-color 0.18s var(--sr-ease), box-shadow 0.18s var(--sr-ease), transform 0.18s var(--sr-ease);
    }
    .squad-player-card:hover {
        border-color: #D6D3CB;
        box-shadow: var(--sr-shadow-sm);
        transform: translateY(-1px);
    }
    .squad-player-card-coach { box-shadow: inset 3px 0 0 var(--sr-accent), var(--sr-shadow-xs); }
    .squad-player-card-captain { box-shadow: inset 3px 0 0 #D9A013, var(--sr-shadow-xs); }
    .srh-card-top {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.4rem;
        margin-bottom: 0.55rem;
    }
    .srh-badge-row { display: flex; gap: 0.35rem; flex-wrap: wrap; }
    .squad-flag { font-size: 1.05rem; line-height: 1; flex-shrink: 0; }
    .squad-coach-badge {
        color: var(--sr-accent-ink);
        background: var(--sr-accent-soft);
        padding: 2px 7px;
        border-radius: var(--sr-r-xs);
        font-size: 0.625rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .squad-captain-badge {
        color: var(--sr-amber);
        background: var(--sr-amber-soft);
        padding: 2px 7px;
        border-radius: var(--sr-r-xs);
        font-size: 0.625rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .squad-tag {
        color: var(--sr-muted);
        background: var(--sr-surface-sunken);
        padding: 2px 7px;
        border-radius: var(--sr-r-xs);
        font-size: 0.625rem;
        font-weight: 650;
        letter-spacing: 0.04em;
    }
    h3.squad-card-name {
        font-size: 1rem;
        font-weight: 700;
        letter-spacing: -0.01em;
        color: var(--sr-ink);
        margin: 0 0 0.15rem;
    }
    .squad-card-role { font-size: 0.8125rem; color: var(--sr-muted); font-weight: 500; line-height: 1.45; }
    .squad-card-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 0.5rem;
        border-top: 1px solid var(--sr-line-soft);
        padding-top: 0.55rem;
        margin-top: 0.85rem;
        font-size: 0.75rem;
        color: var(--sr-faint);
    }
    .squad-card-note { color: var(--sr-accent-ink); font-size: 0.75rem; font-weight: 600; }

    /* ── Alerts & loading ───────────────────────────────────────────────── */
    [data-testid="stAlert"] {
        border-radius: var(--sr-r) !important;
        border: 1px solid var(--sr-line) !important;
        color: var(--sr-body) !important;
    }
    [data-testid="stSkeleton"], [data-testid="stSkeletonElement"] {
        border-radius: var(--sr-r-sm) !important;
        background: linear-gradient(90deg, #EFEEEA 25%, #F8F8F5 37%, #EFEEEA 63%) !important;
        background-size: 400% 100% !important;
        animation: sr-shimmer 1.4s ease infinite !important;
    }
    @keyframes sr-shimmer {
        0% { background-position: 100% 0; }
        100% { background-position: 0 0; }
    }

    /* ── Responsive ─────────────────────────────────────────────────────── */
    @media (max-width: 1024px) {
        .block-container { padding-left: 1.5rem; padding-right: 1.5rem; }
    }
    @media (max-width: 900px) {
        .block-container { padding: 1.25rem 1rem 3rem; }
        h1.srh-brand-title { max-width: 100%; }
        .srh-brand-header { gap: 1rem; }
        .srh-live-badge { order: 3; }
        .hero-fixture-card { padding: 1.25rem; align-items: flex-start; }
        .hero-fixture-right {
            width: 100%;
            text-align: left;
            padding-left: 0;
            padding-top: 1rem;
            border-left: 0;
            border-top: 1px solid var(--sr-night-line);
        }
        .hero-countdown-val { justify-content: flex-start; }
        h2.hero-fixture-vs { font-size: 1.4rem; }
        .pulse-panel { position: static; }
        [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 0.75rem !important; }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: 100% !important;
        }
        /* The headline rail repeats the feed; don't stack it after 47 stories. */
        [data-testid="stColumn"]:has(.pulse-panel) { display: none !important; }
        .srh-stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .srh-card-grid { grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); }
        .featured-story-card { padding: 1.25rem; }
        .link-action { margin-left: 0; padding-left: 0; border-left: 0; }
    }
    @media (max-width: 560px) {
        .block-container { padding: 1rem 0.9rem 2.5rem; }
        h1.srh-brand-title { font-size: 1.8rem; }
        .srh-brand-subtitle { font-size: 0.9rem; }
        .telemetry-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .telemetry-metric-pill { padding: 0.75rem 0.85rem; }
        .telemetry-metric-pill:nth-child(3) { border-left: 0; }
        .telemetry-metric-pill:nth-child(n+3) { border-top: 1px solid var(--sr-line-soft); }
        .telemetry-metric-num { font-size: 1.15rem; }
        .srh-stat-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .srh-card-grid { grid-template-columns: 1fr; }
        .stTabs [data-baseweb="tab-list"] { gap: 1.1rem; }
        .stTabs [data-baseweb="tab"] { font-size: 0.875rem; }
        h2.featured-story-title { font-size: 1.15rem; }
        .featured-story-desc { -webkit-line-clamp: 4; }
        .featured-story-footer .published-tag,
        .featured-story-footer .meta-dot,
        .telemetry-card-footer .published-tag,
        .telemetry-card-footer .meta-dot { display: none; }
        .hero-fixture-card { margin-top: 1rem; }
        .hero-fixture-details { font-size: 0.78rem; }
        .broadcast-match-card { padding: 1rem; }
        .match-meta, .match-players { font-size: 0.84rem; }
    }
    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
            scroll-behavior: auto !important;
        }
        .srh-live-pulse-dot,
        .hero-countdown-val-live::before,
        .status-pill-live::before { animation: none; }
        a.featured-story-link:hover .featured-story-card,
        a.telemetry-card-link:hover .telemetry-news-card,
        .squad-player-card:hover { transform: none; }
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
        return f"{int(diff / 60)} min ago"
    if diff < 86400:
        hrs = int(diff / 3600)
        mins = int((diff % 3600) / 60)
        return f"{hrs} hr {mins} min ago" if mins else f"{hrs} hr ago"
    return "Over a day ago"
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
    """Renders the page masthead: kicker, display headline and live status."""
    return f"""
    <div class='srh-masthead-kicker'>SRHXtra · Sunrisers news hub</div>
    <div class='srh-brand-header'>
        <div>
            <h1 class='srh-brand-title'>Every Sunrisers story, <span class='highlight'>one place.</span></h1>
            <p class='srh-brand-subtitle'>All the latest news, fixtures and squads for {player_count} Sunrisers players across {franchise_count} teams.</p>
        </div>
        <div class='srh-live-badge'>
            <span class='srh-live-pulse-dot' aria-hidden='true'></span>
            <span>News checked every 15 minutes</span>
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
    venue = html_lib.escape(next_fixture.get("venue", "Venue to be confirmed"))
    broadcast = html_lib.escape(next_fixture.get("broadcast", "Check your local listings"))
    if status == "LIVE":
        card_class = "hero-fixture-card hero-fixture-card-live"
        tag_html = f"<div class='hero-fixture-tag hero-fixture-tag-live'>Live now · {league}</div>"
        val_html = "<div class='hero-countdown-val hero-countdown-val-live' aria-live='polite'>Live now</div>"
        lbl_html = "<div class='hero-countdown-lbl'>In progress</div>"
    elif status == "COMPLETED":
        card_class = "hero-fixture-card"
        tag_html = f"<div class='hero-fixture-tag'>Result · {league}</div>"
        val_html = "<div class='hero-countdown-val'>Match ended</div>"
        lbl_html = "<div class='hero-countdown-lbl'>Result</div>"
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
            f"<a href='{link_attr}' target='_blank' rel='noopener noreferrer' "
            f"class='srh-crex-link'>"
            f"Squad and live score on Crex <span aria-hidden='true'>↗</span></a>"
        )
    return f"""
    <div class='{card_class}'>
        <div class='hero-fixture-left'>
            {tag_html}
            <h2 class='hero-fixture-vs'>{squad} vs {vs}</h2>
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
    """Renders the global coverage strip above the tabs."""
    return f"""
    <div class='telemetry-strip' role='list' aria-label='At a glance'>
        <div class='telemetry-metric-pill' role='listitem'>
            <span class='telemetry-metric-num'>{source_count}</span>
            <span class='telemetry-metric-lbl'>News sites</span>
        </div>
        <div class='telemetry-metric-pill' role='listitem'>
            <span class='telemetry-metric-num'>{player_count}</span>
            <span class='telemetry-metric-lbl'>Players</span>
        </div>
        <div class='telemetry-metric-pill' role='listitem'>
            <span class='telemetry-metric-num'>4</span>
            <span class='telemetry-metric-lbl'>Teams</span>
        </div>
        <div class='telemetry-metric-pill' role='listitem'>
            <span class='telemetry-metric-num'>{live_count}</span>
            <span class='telemetry-metric-lbl'>Stories</span>
        </div>
    </div>
    """
def show_big_story(n):
    """Renders the top article as the featured story, with full article metadata."""
    link = find_good_link_for_story(n)
    link_attr = html_lib.escape(link, quote=True)
    league = guess_which_league(n.get("title", ""), n.get("summary", ""))
    pub_ts = n.get("pub_timestamp", 0)
    ago = how_long_ago(pub_ts)
    favicon = find_tiny_website_icon(link)
    fav_html = (
        f"<img src='{favicon}' class='source-fav-icon' alt='' width='16' height='16' "
        f"loading='lazy' referrerpolicy='no-referrer'>"
        if favicon else ""
    )
    clean_title = html_lib.escape(str(n.get("title", "")).replace("\n", " ").strip())
    clean_summary = html_lib.escape(str(n.get("summary", "")).replace("\n", " ").strip())
    player_name = html_lib.escape(str(n.get("player_name", "")).strip())
    franchise = html_lib.escape(str(n.get("franchise", "")).strip())
    source = html_lib.escape(str(n.get("source", "")).strip())
    pub_at = html_lib.escape(str(n.get("published_at", "")).strip())
    return (
        f"<a href='{link_attr}' target='_blank' rel='noopener noreferrer' class='featured-story-link'>"
        f"<div class='featured-story-card'>"
        f"<div class='featured-badge-bar'>"
        f"<span class='badge-hero-top'>Top story</span>"
        f"<span class='chip-player'>{player_name}</span>"
        f"<span class='chip-squad'>{franchise}</span>"
        f"<span class='chip-league'>{league}</span>"
        f"</div>"
        f"<h2 class='featured-story-title'>{clean_title}</h2>"
        f"<div class='featured-story-desc'>{clean_summary}</div>"
        f"<div class='featured-story-footer'>"
        f"<span class='time-tag'>{ago}</span>"
        f"<span class='meta-dot' aria-hidden='true'>·</span>"
        f"<span class='published-tag'>{pub_at}</span>"
        f"<span class='source-tag'>{fav_html}{source}</span>"
        f"<span class='link-action'>Read story <span aria-hidden='true'>↗</span></span>"
        f"</div>"
        f"</div>"
        f"</a>"
    )
def show_story_card(n):
    """Renders a standard news item card."""
    link = find_good_link_for_story(n)
    link_attr = html_lib.escape(link, quote=True)
    league = guess_which_league(n.get("title", ""), n.get("summary", ""))
    pub_ts = n.get("pub_timestamp", 0)
    ago = how_long_ago(pub_ts)
    new_badge = "<span class='chip-new'>New</span>" if is_this_story_fresh(pub_ts) else ""
    favicon = find_tiny_website_icon(link)
    fav_html = (
        f"<img src='{favicon}' class='source-fav-icon' alt='' width='16' height='16' "
        f"loading='lazy' referrerpolicy='no-referrer'>"
        if favicon else ""
    )
    clean_title = html_lib.escape(str(n.get("title", "")).replace("\n", " ").strip())
    clean_summary = html_lib.escape(str(n.get("summary", "")).replace("\n", " ").strip())
    player_name = html_lib.escape(str(n.get("player_name", "")).strip())
    franchise = html_lib.escape(str(n.get("franchise", "")).strip())
    source = html_lib.escape(str(n.get("source", "")).strip())
    pub_at = html_lib.escape(str(n.get("published_at", "")).strip())
    return (
        f"<a href='{link_attr}' target='_blank' rel='noopener noreferrer' class='telemetry-card-link'>"
        f"<div class='telemetry-news-card'>"
        f"<div class='telemetry-card-tags'>{new_badge}<span class='chip-player'>{player_name}</span><span class='chip-squad'>{franchise}</span><span class='chip-league'>{league}</span></div>"
        f"<h3 class='telemetry-card-title'>{clean_title}</h3>"
        f"<div class='telemetry-card-desc'>{clean_summary}</div>"
        f"<div class='telemetry-card-footer'>"
        f"<span class='time-tag'>{ago}</span>"
        f"<span class='meta-dot' aria-hidden='true'>·</span>"
        f"<span class='published-tag'>{pub_at}</span>"
        f"<span class='source-tag'>{fav_html}{source}</span>"
        f"<span class='link-action'>Read story <span aria-hidden='true'>↗</span></span>"
        f"</div>"
        f"</div>"
        f"</a>"
    )
def show_small_timeline_story(n):
    """Renders one compact entry in the latest-headlines rail."""
    link = find_good_link_for_story(n)
    link_attr = html_lib.escape(link, quote=True)
    pub_ts = n.get("pub_timestamp", 0)
    ago = how_long_ago(pub_ts)
    raw_title = str(n.get("title", "")).replace("\n", " ").strip()
    headline = html_lib.escape(raw_title[:65] + ("..." if len(raw_title) > 65 else ""))
    player_name = html_lib.escape(str(n.get("player_name", "")).strip())
    return (
        f"<li class='pulse-item-dark'>"
        f"<div class='pulse-time-dark'>{ago} · {player_name}</div>"
        f"<a href='{link_attr}' target='_blank' rel='noopener noreferrer' class='pulse-headline-dark'>{headline}</a>"
        f"</li>"
    )
def show_pulse_panel(news_list):
    """Renders the whole latest-headlines rail in one HTML block."""
    items = "".join(show_small_timeline_story(n) for n in news_list[:10])
    return (
        "<div class='pulse-panel'>"
        "<h2 class='pulse-panel-title'>"
        "<span>Latest headlines</span>"
        "<span class='srh-live-pulse-dot' aria-hidden='true'></span>"
        "</h2>"
        f"<ol class='pulse-list'>{items}</ol>"
        "</div>"
    )

def show_match_card(item, status="UPCOMING"):
    """Renders a fixture in the matchday card format.

    Live Crex fixtures carry `link`, `srh_players` and `franchises`; static
    legacy fixtures omit them and still render cleanly.
    """
    status = item.get("status", status) or status
    if status == "LIVE":
        status_html = "<span class='status-pill status-pill-live'>Live now</span>"
        card_extra_class = " broadcast-match-card-live"
    elif status == "COMPLETED":
        status_html = "<span class='status-pill status-pill-completed'>Final</span>"
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
            f"<a href='{link_attr}' target='_blank' rel='noopener noreferrer' "
            f"class='srh-crex-link'>"
            f"Squad and live score on Crex <span aria-hidden='true'>↗</span></a>"
        )
    franchise_html = ""
    if item.get("franchises"):
        chips = "".join(
            f"<span class='chip-squad'>{html_lib.escape(str(f))}</span>"
            for f in item["franchises"]
        )
        franchise_html = f"<div class='match-franchises'>{chips}</div>"
    players_html = (
        f"<div class='match-players'><strong>Sunrisers players:</strong> {players}</div>"
        if players else ""
    )
    meta_html = (
        f"<div class='match-meta'>{meta_html}</div>"
        if meta_html else ""
    )
    return (
        f"<div class='broadcast-match-card{card_extra_class}'>"
        f"<div class='broadcast-match-header'>"
        f"{status_html}"
        f"<span class='match-league'>{squad}</span>"
        f"</div>"
        f"<h3 class='match-versus'>{squad} vs {vs}</h3>"
        f"<div class='match-meta'><strong>{date_str}</strong> · {match_time}</div>"
        f"{meta_html}"
        f"{players_html}"
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
    """Renders an official squad member card."""
    name = html_lib.escape(member.get("name", ""))
    role = html_lib.escape(member.get("role", "Player"))
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

    badges_html = f"<div class='srh-badge-row'>{''.join(badges)}</div>"
    notes_html = f"<span class='squad-card-note'>{notes}</span>" if notes else ""

    return (
        f"<div class='{' '.join(card_classes)}'>"
        f"  <div>"
        f"    <div class='srh-card-top'>"
        f"      {badges_html}"
        f"      <span class='squad-flag' title='{country}' aria-hidden='true'>{flag}</span>"
        f"    </div>"
        f"    <h3 class='squad-card-name'>{name}</h3>"
        f"    <div class='squad-card-role'>{role}</div>"
        f"  </div>"
        f"  <div class='squad-card-footer'>"
        f"    <span>{country}</span>"
        f"    {notes_html}"
        f"  </div>"
        f"</div>"
    )

def show_player_grid(members, franchise_name=None):
    """Renders a responsive grid of squad cards in one HTML block."""
    cards = "".join(show_player_card(m, franchise_name=franchise_name) for m in members)
    return f"<div class='srh-card-grid'>{cards}</div>"

def show_stat_cards(stats):
    """Renders a consistent stat-card grid from (value, label) pairs."""
    cells = "".join(
        f"<div class='srh-stat'><div class='srh-stat-num'>{html_lib.escape(str(value))}</div>"
        f"<div class='srh-stat-lbl'>{html_lib.escape(str(label))}</div></div>"
        for value, label in stats
    )
    return f"<div class='srh-stat-grid'>{cells}</div>"

def show_empty_state(title, message):
    """Renders a friendly, consistent empty state."""
    return (
        f"<div class='srh-empty' role='status'>"
        f"<h3>{html_lib.escape(str(title))}</h3>"
        f"<p>{html_lib.escape(str(message))}</p>"
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
