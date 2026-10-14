"""Elite Telegram matchday cards for @SRHXtra (/matches command).

Pure formatting over Crex fixtures from scrapers.matchday_scraper —
LIVE first, IST + relative day labels, roster-matched players grouped by
franchise. No network here, no buttons anywhere. All interpolated values
are HTML-escaped (team names and venues are untrusted scraper output).
"""
import html
from datetime import datetime

from config.roster import MASTER_ROSTER
from utils.telegram import _accent
from utils.time_utils import get_current_ist

MAX_PLAYERS_SHOWN = 6
MAX_UPCOMING_SHOWN = 4


def build_roster_franchise_map():
    """Player full name -> franchise display name (for per-card grouping)."""
    mapping = {}
    try:
        for data in MASTER_ROSTER.values():
            franchise = data.get("franchise_name", "")
            for p in data.get("players", []):
                mapping.setdefault(p.get("name", ""), franchise)
    except Exception:
        pass
    return mapping


def parse_fixture_dt(fixture):
    """IST-naive datetime from a fixture dict (same format as the sorter)."""
    try:
        return datetime.strptime(
            f"{fixture.get('date_str', '')} {fixture.get('time', '').replace(' IST', '').strip()}",
            "%B %d, %Y %I:%M %p",
        )
    except Exception:
        return None


def fixture_day_label(dt, now=None):
    """Today / Tomorrow / 'Wed, Oct 15' relative label (IST calendar days)."""
    if dt is None:
        return ""
    try:
        today = (now or get_current_ist()).date()
        delta = (dt.date() - today).days
        if delta == 0:
            return "Today"
        if delta == 1:
            return "Tomorrow"
        return dt.strftime("%a, %b %d")
    except Exception:
        return ""


def _player_line(players, roster_map):
    """'A, B, C +2 more' + franchise counts, all escaped."""
    players = [p for p in (players or []) if p]
    if not players:
        return ""
    shown = players[:MAX_PLAYERS_SHOWN]
    names = html.escape(", ".join(shown))
    if len(players) > MAX_PLAYERS_SHOWN:
        names += f" +{len(players) - MAX_PLAYERS_SHOWN} more"
    counts = {}
    for p in players:
        franchise = roster_map.get(p, "")
        if franchise:
            counts[franchise] = counts.get(franchise, 0) + 1
    suffix = ""
    if counts:
        suffix = " " + html.escape(
            "(" + ", ".join(f"{f} ×{c}" for f, c in sorted(counts.items())) + ")"
        )
    return f"⚡ {names}{suffix}"


def format_match_card(fixture, now=None, roster_map=None):
    """One fixture → HTML card. LIVE and upcoming share the layout."""
    roster_map = roster_map or build_roster_franchise_map()
    live = fixture.get("status") == "LIVE"
    dt = parse_fixture_dt(fixture)
    head = "🔴 <b>LIVE NOW</b>" if live else "🕒 <b>Upcoming</b>"
    team1 = html.escape(str(fixture.get("team1", "")))
    team2 = html.escape(str(fixture.get("team2", "")))
    league = html.escape(str(fixture.get("league", "") or "Cricket"))
    date_str = html.escape(str(fixture.get("date_str", "")))
    time_str = html.escape(str(fixture.get("time", "") or "").replace(" IST", "").strip())
    day = fixture_day_label(dt, now)
    when = html.escape(f"{day}, {date_str} · {time_str} IST".strip(" ,·")) if date_str else ""
    lines = [head, "", f"<b>{team1} vs {team2}</b>", f"🏆 {league}"]
    if when:
        lines.append(f"📅 {when}")
    players = _player_line(fixture.get("srh_players") or [], roster_map)
    if players:
        lines.append(players)
    venue = html.escape(str(fixture.get("venue", "") or ""))
    if venue:
        lines.append(f"🏟 {venue}")
    link = str(fixture.get("link", "") or "")
    if link.startswith("https://"):
        action = "Live score on Crex →" if live else "Fixture on Crex →"
        lines.append(f'<a href="{html.escape(link, quote=True)}">{action}</a>')
    return "\n".join(lines)


def format_matches_message(fixtures, now=None):
    """Full /matches reply: LIVE block, upcoming block, or honest empty state."""
    fixtures = list(fixtures or [])
    now = now or get_current_ist()
    roster_map = build_roster_franchise_map()
    if not fixtures:
        return (
            "📭 <b>No Sunrisers fixtures live right now</b>\n"
            "Nothing in the 4-day Crex window involves our squads — "
            "fresh matches appear here the moment squads drop.\n"
            '<a href="https://crex.com/schedule">Full schedule on Crex →</a>'
        )
    live = [f for f in fixtures if f.get("status") == "LIVE"]
    upcoming = [f for f in fixtures if f.get("status") != "LIVE"][:MAX_UPCOMING_SHOWN]
    blocks = []
    if live:
        n = len(live)
        blocks.append(
            f"🔴 <b>LIVE — {n} Sunrisers match{'es' if n != 1 else ''} on now</b>"
        )
        blocks += [format_match_card(f, now, roster_map) for f in live]
    if upcoming:
        if live:
            blocks.append("─ ─ ─")
        blocks.append("<b>Coming up</b>")
        blocks += [format_match_card(f, now, roster_map) for f in upcoming]
        hidden = len(fixtures) - len(live) - len(upcoming)
        if hidden > 0:
            blocks.append(f"<i>+{hidden} more in the 4-day window.</i>")
    text = "\n\n".join(blocks)
    return text[:4000]
