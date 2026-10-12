"""
Live Matchday Fixture Scraper for @SRHXtra.

Workflow (per user requirement):
  1. Open / scrape https://crex.com/schedule
  2. Extract all upcoming/live match links
  3. Visit each match page
  4. Extract the Squad / Playing XI section text
  5. Check whether any Sunrisers player names appear in that squad
     (strict full-name match against the Excel roster via match_squad_players)
  6. If yes -> return match details (teams, series, time, which SRH players,
     link); UI sorts LIVE first, then soonest upcoming. Finished matches are
     removed (never returned).

Only fixtures containing at least one real rostered player are returned.
Generic "Franchise Update" matches without a named player do not qualify.
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from config.roster import MASTER_ROSTER
from utils.logger import rss_logger, error_logger
from utils.time_utils import get_current_ist

CREX_BASE = "https://crex.com"
CREX_SCHEDULE_URL = f"{CREX_BASE}/schedule"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )
}

CACHE_TTL_SECS = 900  # 15 min — matches AUTO_INGEST_INTERVAL_SECS
MAX_MATCHES_PER_CYCLE = 25

_CACHE = {"ts": 0.0, "fixtures": []}

# e.g. "Tue, 13 Oct 2026" from the schedule date headers
_SCHEDULE_DATE_RE = re.compile(
    r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s*(\d{1,2})\s+"
    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{4})"
)
# e.g. "Tuesday, 13 October, 1:00 PM" from match pages (year absent)
_MATCH_DATE_RE = re.compile(
    r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*"
    r"(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December),\s*"
    r"(\d{1,2}):(\d{2})\s*(AM|PM)",
    re.IGNORECASE,
)
# Embedded Angular/CrickAPI state holds BOTH squads even when only one tab
# is server-rendered: &q;p&q;:[{&q;f_key&q;:...&q;n&q;:&q;Player Name&q;...}]
_PLAYER_BLOCK_RE = re.compile(r"&q;p&q;:\[(.*?)\]", re.DOTALL)
_PLAYER_NAME_RE = re.compile(r"&q;n&q;:&q;(.*?)&q;")

_MONTH_NUM = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _http_get(url, timeout=12):
    """GET with browser UA. Returns response text or None (never raises)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code == 200 and resp.text:
            return resp.text
        error_logger.warning(f"Matchday scrape: HTTP {resp.status_code} for {url}")
    except Exception as exc:
        error_logger.warning(f"Matchday scrape failed for {url}: {type(exc).__name__}: {exc}")
    return None


def fetch_schedule_cards(timeout=12):
    """Scrapes crex.com/schedule into lightweight match cards.

    Returns list of dicts: team1, team2, time_str, format_str, series,
    href (relative), date_header (e.g. 'Tue, 13 Oct 2026').
    Returns [] on failure (never raises).
    """
    html = _http_get(CREX_SCHEDULE_URL, timeout=timeout)
    if not html:
        return []
    try:
        soup = BeautifulSoup(html, "html.parser")
        cards = []
        # Each date section groups its match cards; walk sections in order so
        # every card inherits the right date header.
        sections = soup.find_all("div", class_="date-wise-matches-card")
        if not sections:
            sections = [soup]
        for section in sections:
            date_tag = section.find(["h2"], class_="date")
            date_header = date_tag.get_text(strip=True) if date_tag else ""
            for li in section.find_all("li", class_="match-card-container"):
                a = li.find("a", class_="match-card-wrapper", href=True)
                if not a:
                    continue
                href = a["href"]
                # Only same-site match links — never follow absolute
                # third-party URLs found in page markup.
                if not href.startswith("/cricket-live-score/"):
                    continue
                team_names = [
                    s.get_text(strip=True)
                    for s in a.find_all("span", class_="team-name")
                ]
                if len(team_names) < 2:
                    continue
                start = a.find("div", class_="start-text")
                time_str = start.get_text(strip=True) if start else ""
                meta = a.find("p", class_="time")
                meta_text = meta.get_text(" ", strip=True) if meta else ""
                # meta looks like: "8th One Day , AUS One Day Cup 2026-27"
                fmt, _, series = meta_text.partition(",")
                cards.append({
                    "team1": team_names[0],
                    "team2": team_names[1],
                    "time_str": time_str,
                    "format_str": fmt.strip(),
                    "series": series.strip(),
                    "href": href,
                    "date_header": date_header,
                })
        return cards
    except Exception as exc:
        error_logger.warning(f"Matchday schedule parse failed: {exc}")
        return []


def extract_squad_text(html):
    """Extracts Squad / Playing XI section text (both teams) from a match page.

    Combines the server-rendered playingxi-card (visible tab) with player
    names embedded in the page state (both squads), so roster matching sees
    every squad member regardless of which tab was pre-rendered.
    """
    return " ".join(extract_squad_names(html))


def extract_squad_names(html):
    """Extracts Squad / Playing XI player full names (both teams) as a list.

    Sources: playingxi-card link titles (full names) + player names embedded
    in the page state. Order-preserving, de-duplicated.
    """
    names = []
    try:
        soup = BeautifulSoup(html, "html.parser")
        xi = soup.find("app-playingxi-card")
        if xi is not None:
            names.extend(
                a.get("title", "").strip()
                for a in xi.find_all("a", title=True)
                if a.get("title", "").strip()
            )
        for block in _PLAYER_BLOCK_RE.findall(html):
            names.extend(n.strip() for n in _PLAYER_NAME_RE.findall(block) if n.strip())
    except Exception as exc:
        error_logger.warning(f"Matchday squad extract failed: {exc}")
    seen, ordered = set(), []
    for n in names:
        key = _norm_name(n)
        if key and key not in seen:
            seen.add(key)
            ordered.append(n)
    return ordered


def _norm_name(name):
    return re.sub(r"[^a-z0-9\- ]", "", name.lower()).strip()


def _split_name(name):
    bits = _norm_name(name).split()
    if not bits:
        return "", ""
    if len(bits) == 1:
        return bits[0], ""
    return bits[0], bits[-1]


def match_squad_players(squad_names):
    """Strict squad-to-roster matching on full names.

    News headlines use loose single-name aliases for recall, but squads list
    full names — so bare first names ("Abhishek", "Ishan") or shared surnames
    ("Kruger") must NOT match across different players (e.g. Abhishek
    Paradkar is not Abhishek Sharma; Malan Kruger is not Patrick Kruger).
    A roster player matches iff a squad name equals their full name, or
    shares their surname with an equal first name / initial (covers "Mitch"
    vs "Mitchell", "P Cummins").
    Returns match dicts shaped like match_player_or_franchise_in_text().
    """
    roster = []
    for team_key, data in MASTER_ROSTER.items():
        for p in data["players"]:
            first, last = _split_name(p["name"])
            roster.append({
                "name": p["name"],
                "first": first,
                "last": last,
                "team_key": team_key,
                "franchise": data["franchise_name"],
                "country": p.get("country", ""),
                "role": p.get("role", ""),
                "captain": p.get("captain", False),
            })
    hits, seen = [], set()
    for squad_name in squad_names:
        s_first, s_last = _split_name(squad_name)
        if not s_first:
            continue
        for r in roster:
            if r["name"] in seen:
                continue
            if _norm_name(squad_name) == _norm_name(r["name"]):
                matched = True
            elif r["last"] and s_last == r["last"] and s_first and r["first"]:
                # Surname + (equal first OR equal initial with one side a
                # prefix of the other, e.g. Mitch/Mitchell, Matty/Matthew,
                # single-initial "P Cummins"). Different first names with a
                # shared surname (Malan vs Patrick Kruger) do NOT match.
                matched = (
                    s_first[:1] == r["first"][:1]
                    and (
                        s_first == r["first"]
                        or r["first"].startswith(s_first)
                        or s_first.startswith(r["first"])
                        or len(s_first) == 1
                        or len(r["first"]) == 1
                    )
                )
            else:
                matched = False
            if matched:
                seen.add(r["name"])
                hits.append({
                    "player_name": r["name"],
                    "team_key": r["team_key"],
                    "franchise": r["franchise"],
                    "country": r["country"],
                    "role": r["role"],
                    "captain": r["captain"],
                })
    return hits


def _year_from_date_header(date_header):
    m = _SCHEDULE_DATE_RE.search(date_header or "")
    if m:
        return int(m.group(4))
    return datetime.now().year


def extract_match_meta(html, card):
    """Extracts teams/series/datetime/venue/broadcast/status-hint.

    `card` is the schedule card (provides fallback teams/series/year).
    Returns dict with date_str/time (IST-naive, theme-compatible), venue,
    broadcast, is_live_tab, title.
    """
    team1 = card.get("team1", "")
    team2 = card.get("team2", "")
    series = card.get("series", "")
    match_no = card.get("format_str", "")
    venue = ""
    broadcast = ""
    title = ""
    dt = None
    is_live_tab = False
    try:
        soup = BeautifulSoup(html, "html.parser")
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        text = soup.get_text(" | ", strip=True)
        # Live matches expose a "Live" nav tab; upcoming ones show
        # "Discussions | Series Stats" instead.
        is_live_tab = "| Live |" in text or ">Live<" in html
        m = _MATCH_DATE_RE.search(text)
        if m:
            year = _year_from_date_header(card.get("date_header", ""))
            try:
                dt = datetime(
                    year,
                    _MONTH_NUM[m.group(3)[:3].lower()],
                    int(m.group(2)),
                    (int(m.group(4)) % 12) + (12 if m.group(6).upper() == "PM" else 0),
                    int(m.group(5)),
                )
                # Segments after the date are "| Venue | Broadcast |"
                tail = text[m.end():].split(" | ")
                if len(tail) > 1 and tail[1].strip():
                    venue = tail[1].strip()
                if len(tail) > 2 and tail[2].strip():
                    broadcast = tail[2].strip()
            except ValueError:
                dt = None
        # match_no/series come from the schedule card (reliable structured
        # markup); the match-page header ("PAK vs SL, 3rd T20, ...") carries
        # the same data, so no override is attempted.
    except Exception as exc:
        error_logger.warning(f"Matchday meta extract failed: {exc}")
    if dt is None:
        # Fall back to the schedule card's date header + time
        dt = _schedule_card_datetime(card)
    if dt is not None:
        date_str = dt.strftime("%B %d, %Y")
        time_str = dt.strftime("%I:%M %p IST")
        day_name = dt.strftime("%a")
    else:
        date_str = card.get("date_header", "").split(",")[-1].strip() or "TBD"
        time_str = f"{card.get('time_str', '').strip()} IST".strip()
        day_name = ""
    return {
        "team1": team1,
        "team2": team2,
        "series": series,
        "match_no": match_no,
        "venue": venue,
        "broadcast": broadcast or "Check Crex for stream",
        "title": title,
        "datetime": dt,
        "is_live_tab": is_live_tab,
        "date_str": date_str,
        "time_str": time_str,
        "day_name": day_name,
    }


def _schedule_card_datetime(card):
    """Best-effort datetime from schedule card alone (date header + time)."""
    try:
        m = _SCHEDULE_DATE_RE.search(card.get("date_header", ""))
        if not m:
            return None
        year = int(m.group(4))
        month = _MONTH_NUM[m.group(3).lower()]
        day = int(m.group(2))
        tm = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", card.get("time_str", "") or "", re.I)
        if not tm:
            return datetime(year, month, day, 12, 0)
        hour = (int(tm.group(1)) % 12) + (12 if tm.group(3).upper() == "PM" else 0)
        return datetime(year, month, day, hour, int(tm.group(2)))
    except (ValueError, AttributeError, TypeError):
        return None


def _resolve_status(meta):
    """LIVE when Crex shows its Live tab on a non-future match, else by clock.

    Crex datetimes are IST-naive, so "now" is IST too (matching
    theme.get_fixture_status). Live-tab matches started within the last 12h
    count as LIVE (covers ODI/long formats whose SSR snapshot may lag);
    older ones are finished and dropped by the caller.
    Returns 'LIVE', 'UPCOMING', or 'COMPLETED'. Finished matches are dropped
    by the caller.
    """
    dt = meta.get("datetime")
    now = get_current_ist().replace(tzinfo=None)
    if dt is not None and dt > now:
        return "UPCOMING"
    if meta.get("is_live_tab"):
        if dt is None or (now - dt).total_seconds() < 43200:
            return "LIVE"
        return "COMPLETED"
    if dt is None:
        return "UPCOMING"
    return "COMPLETED"


def fetch_match_fixture(card, timeout=10):
    """Fetches one match page and builds a UI fixture dict, or None.

    None means: fetch failed, no Sunrisers player in the squad, or the match
    is finished (removed per requirement). Never raises — one bad card must
    not abort the whole batch.
    """
    try:
        return _fetch_match_fixture_inner(card, timeout=timeout)
    except Exception as exc:
        error_logger.warning(f"Matchday card failed ({card.get('href')}): {exc}")
        return None


def _fetch_match_fixture_inner(card, timeout=10):
    url = card["href"]
    if url.startswith("/"):
        url = CREX_BASE + url
    elif not url.startswith(CREX_BASE + "/cricket-live-score/"):
        return None
    html = _http_get(url, timeout=timeout)
    if not html:
        return None
    meta = extract_match_meta(html, card)
    status = _resolve_status(meta)
    if status == "COMPLETED":
        return None
    squad_names = extract_squad_names(html)
    if not squad_names:
        return None
    # Strict full-name squad matching (NOT the loose news-headline aliases:
    # bare "Abhishek"/"Ishan" or shared surnames like "Kruger" must not match
    # unrelated players such as Abhishek Paradkar or Malan Kruger).
    player_hits = match_squad_players(squad_names)
    if not player_hits:
        return None
    srh_players = sorted({m["player_name"] for m in player_hits})
    franchises = sorted({m["franchise"] for m in player_hits})
    league = meta["series"]
    if meta.get("match_no"):
        league = f"{league} · {meta['match_no']}" if league else meta["match_no"]
    dt = meta.get("datetime")
    try:
        date_num = dt.day if dt else 0
        month = dt.strftime("%B %Y") if dt else ""
    except Exception:
        date_num, month = 0, ""
    fixture = {
        # Theme-compatible keys (parse_fixture_datetime / cards)
        "date_num": date_num,
        "month": month,
        "date_str": meta["date_str"],
        "day_name": meta.get("day_name", ""),
        "time": meta["time_str"],
        "squad": meta["team1"],
        "players": ", ".join(srh_players),
        "vs": meta["team2"],
        "league": league or "Cricket",
        "venue": meta.get("venue", ""),
        "broadcast": meta.get("broadcast", ""),
        # Live-scraper extras
        "link": url,
        "status": status,
        "srh_players": srh_players,
        "franchises": franchises,
        "team1": meta["team1"],
        "team2": meta["team2"],
        "series": meta["series"],
        "match_no": meta.get("match_no", ""),
        "source": "CREX Live Schedule",
    }
    rss_logger.info(
        f"Matchday hit: {meta['team1']} vs {meta['team2']} "
        f"({league} @ {meta['date_str']} {meta['time_str']}) — "
        f"SRH players: {', '.join(srh_players)} — {url}"
    )
    return fixture


def _sort_key(fixture):
    live_rank = 0 if fixture.get("status") == "LIVE" else 1
    dt = None
    try:
        dt = datetime.strptime(
            f"{fixture.get('date_str', '')} {fixture.get('time', '').replace(' IST', '').strip()}",
            "%B %d, %Y %I:%M %p",
        )
    except Exception:
        dt = None
    return (live_rank, dt or datetime.max)


def get_sunrisers_fixtures(force_refresh=False, max_matches=MAX_MATCHES_PER_CYCLE):
    """Full workflow: schedule -> match pages -> SRH-player fixtures.

    Sorted LIVE first, then soonest upcoming. Finished matches excluded.
    Results cached for CACHE_TTL_SECS. Never raises — returns [] on failure.
    """
    now = time.time()
    if not force_refresh and _CACHE["ts"] and (now - _CACHE["ts"]) < CACHE_TTL_SECS:
        # ts != 0 means a cycle ran (even an empty one) — serve it until TTL.
        return list(_CACHE["fixtures"])
    try:
        cards = fetch_schedule_cards()
    except Exception as exc:
        error_logger.warning(f"Matchday schedule fetch crashed: {exc}")
        cards = []
    fixtures = []
    if cards:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for fixture in pool.map(fetch_match_fixture, cards[:max_matches]):
                if fixture:
                    fixtures.append(fixture)
    fixtures.sort(key=_sort_key)
    _CACHE["ts"] = now
    _CACHE["fixtures"] = fixtures
    rss_logger.info(
        f"Matchday cycle complete: {len(fixtures)} Sunrisers fixtures "
        f"from {len(cards)} schedule matches."
    )
    return list(fixtures)


def clear_matchday_cache():
    """Forces the next get_sunrisers_fixtures() call to re-scrape."""
    _CACHE["ts"] = 0.0
    _CACHE["fixtures"] = []
