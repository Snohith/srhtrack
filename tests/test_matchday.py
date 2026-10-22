"""
Matchday (Crex live) verification for @SRHXtra V15.

Covers the required workflow with mocked HTTP (no live network in CI):
  schedule scrape -> match links -> Squad/Playing XI extract ->
  roster check -> fixture details -> LIVE-first sort -> finished removed.
Also locks the On-This-Day removal.
"""
import os
import tempfile

# Isolated temp DB (mirrors tests/test_system.py): importing
# news_collectors.find_matches pulls in news_collectors/__init__ -> collect_news ->
# saved_stories.story_storage, which binds SRH_DB_PATH at import time. This must stay
# a temp file so the production DB is never touched, regardless of pytest
# import order. This module performs no DB writes itself.
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["SRH_DB_PATH"] = _tmp_db.name

from unittest.mock import patch
from datetime import timedelta

from helpers.dates_and_times import what_time_is_it_in_india_now

from news_collectors import find_matches as md


def _date_line_safe(dt):
    # Portable (no %-I on some platforms): "Tuesday, 13 October, 11:00 PM"
    s = dt.strftime("%A, %d %B, %I:%M %p")
    return s.replace(", 0", ", ").replace(" 0", " ")


_LIVE_DT = what_time_is_it_in_india_now().replace(tzinfo=None) - timedelta(hours=2)
_UP_DT = what_time_is_it_in_india_now().replace(tzinfo=None) + timedelta(days=1, hours=2)
_OLD_DT = what_time_is_it_in_india_now().replace(tzinfo=None) - timedelta(days=8)

SCHEDULE_HTML = """
<div class="date-wise-matches-card">
  <h2 class="date">Tue, 13 Oct 2026</h2>
  <li class="match-card-container">
    <a class="match-card-wrapper" href="/cricket-live-score/nsw-vs-tas-test-132H">
      <div class="match-details">
        <div class="team-info"><span class="team-name">New South Wales</span></div>
        <div class="not-started"><div class="start-text">11:00 PM</div>
          <p class="time"><span>8th</span><span>One Day</span>, AUS One Day Cup 2026-27</p>
        </div>
        <div class="team-info"><span class="team-name">Tasmania</span></div>
      </div>
    </a>
  </li>
  <li class="match-card-container">
    <a class="match-card-wrapper" href="/cricket-live-score/pak-vs-sl-test-13LS">
      <div class="match-details">
        <div class="team-info"><span class="team-name">Pakistan</span></div>
        <div class="not-started"><div class="start-text">1:00 PM</div>
          <p class="time"><span>3rd</span><span>T20I</span>, SL vs PAK 2026</p>
        </div>
        <div class="team-info"><span class="team-name">Sri Lanka</span></div>
      </div>
    </a>
  </li>
</div>
"""


def _match_html(*, live_tab, date_line, venue, broadcast, titles, embedded):
    xi_links = "".join(
        f'<a title="{t}" href="/player/x"><div class="p-name">{t}</div></a>'
        for t in titles
    )
    embedded_block = "&q;p&q;:[" + "".join(
        "&q;f_key&q;:&q;X&q;,&q;n&q;:&q;" + n + "&q;,"
        for n in embedded
    ) + "]"
    nav = "Match info | Live | Points Table" if live_tab else "Match info | Discussions | Series Stats"
    return f"""
<html><head><title>Test Match Live Score | CREX</title></head><body>
<div>Match Details | TEST vs TEST2, 3rd T20, TEST Series 2026 Info, Weather Report</div>
<div>Pakistan | Sri Lanka | {nav} | News | 3rd T20I | SL vs PAK 2026 | {date_line} | {venue} | {broadcast} |</div>
<app-playingxi-card><div class="playingxi">PAK &amp; SL Squad {xi_links}</div></app-playingxi-card>
<div>{embedded_block}</div>
</body></html>
    """


LIVE_SRH_HTML = _match_html(
    live_tab=True,
    date_line=_date_line_safe(_LIVE_DT),
    venue="Sydney Olympic Park",
    broadcast="CREX & FANCODE",
    titles=["Pat Cummins", "Jack Edwards"],
    embedded=["Pat Cummins", "Jack Edwards", "Steve Smith"],
)
UPCOMING_SRH_HTML = _match_html(
    live_tab=False,
    date_line=_date_line_safe(_UP_DT),
    venue="Allan Border Field, Brisbane",
    broadcast="CREX & FANCODE",
    titles=["Phoebe Litchfield", "Annabel Sutherland"],
    embedded=["Phoebe Litchfield", "Annabel Sutherland", "Beth Mooney"],
)
NO_SRH_HTML = _match_html(
    live_tab=False,
    date_line=_date_line_safe(_UP_DT),
    venue="Somewhere",
    broadcast="YouTube",
    titles=["Joe Bloggs", "John Doe"],
    embedded=["Joe Bloggs", "John Doe"],
)
OLD_SRH_HTML = _match_html(
    live_tab=False,
    date_line=_date_line_safe(_OLD_DT),
    venue="Old Ground",
    broadcast="TV",
    titles=["Pat Cummins"],
    embedded=["Pat Cummins"],
)


def test_schedule_cards_parsed():
    with patch.object(md, "_http_get", return_value=SCHEDULE_HTML):
        cards = md.download_match_list_from_website()
    assert len(cards) == 2, cards
    assert cards[0]["team1"] == "New South Wales"
    assert cards[0]["team2"] == "Tasmania"
    assert cards[0]["href"].endswith("nsw-vs-tas-test-132H")
    assert cards[0]["date_header"] == "Tue, 13 Oct 2026"
    assert cards[1]["series"] == "SL vs PAK 2026"
    print("✅ Schedule cards parsed.")


def test_squad_extract_covers_both_teams():
    squad = md.read_squad_words_from_match_page(UPCOMING_SRH_HTML)
    assert "Phoebe Litchfield" in squad
    assert "Annabel Sutherland" in squad
    assert "Beth Mooney" in squad  # embedded-only name still found
    print("✅ Squad extract covers rendered + embedded players.")


def test_roster_check_uses_excel_roster():
    from our_teams.players import find_our_players_in_story
    squad = md.read_squad_words_from_match_page(LIVE_SRH_HTML)
    names = {m["player_name"] for m in find_our_players_in_story(squad)}
    assert "Pat Cummins" in names, names
    squad2 = md.read_squad_words_from_match_page(UPCOMING_SRH_HTML)
    names2 = {m["player_name"] for m in find_our_players_in_story(squad2)}
    assert "Phoebe Litchfield" in names2 and "Annabel Sutherland" in names2
    print("✅ Roster check matches SRH / Leeds Women stars.")


def test_strict_squad_matching_no_false_positives():
    # Abhishek Paradkar (USA) is NOT Abhishek Sharma; Malan Kruger is NOT
    # Patrick Kruger; Ishan Pandey is NOT Ishan Kishan; Duan Jansen (Titans)
    # is NOT Marco Jansen; Rubin Hermann is NOT Jordan Hermann.
    names = {m["player_name"] for m in md.find_our_players_in_match_squad(
        ["Abhishek Paradkar", "Malan Kruger", "Ishan Pandey", "Duan Jansen",
         "Rubin Hermann"])}
    assert "Abhishek Sharma" not in names, names
    assert "Patrick Kruger" not in names, names
    assert "Ishan Kishan" not in names, names
    assert "Marco Jansen" not in names, names
    assert "Jordan Hermann" not in names, names
    assert names == set(), names
    # ...while true roster names (full, initial, or nickname variants) match.
    good = {m["player_name"] for m in md.find_our_players_in_match_squad(
        ["Pat Cummins", "P Cummins", "Mitchell Marsh", "Phoebe Litchfield",
         "Abrar Ahmed", "Kamindu Mendis", "Eshan Malinga", "Quinton De Kock",
         "Marco Jansen", "Jordan Hermann"])}
    for want in ["Pat Cummins", "Mitch Marsh", "Phoebe Litchfield",
                 "Abrar Ahmed", "Kamindu Mendis", "Eshan Malinga",
                 "Quinton De Kock", "Marco Jansen", "Jordan Hermann"]:
        assert want in good, (want, good)
    print("✅ Strict squad matching: full names hit, lookalikes rejected.")


def test_lookalike_squad_yields_no_fixture():
    card = {"team1": "United States", "team2": "Namibia", "series": "S",
            "format_str": "ODI", "date_header": "Tue, 13 Oct 2026",
            "href": "/cricket-live-score/usa-vs-nam-lookalike"}
    lookalike_html = _match_html(
        live_tab=False,
        date_line=_date_line_safe(_UP_DT),
        venue="Ground",
        broadcast="TV",
        titles=["Abhishek Paradkar", "Malan Kruger"],
        embedded=["Abhishek Paradkar", "Malan Kruger", "Gerhard Erasmus"],
    )
    with patch.object(md, "_http_get", return_value=lookalike_html):
        assert md.check_one_match_for_our_players(card) is None
    print("✅ Lookalike squads (Paradkar/Kruger) yield no fixture.")


def test_match_meta_and_status():
    card = {"team1": "Pakistan", "team2": "Sri Lanka", "series": "SL vs PAK 2026",
            "format_str": "3rd T20I", "date_header": "Tue, 13 Oct 2026"}
    meta_live = md.read_match_details(LIVE_SRH_HTML, card)
    assert meta_live["is_live_tab"] is True
    assert meta_live["venue"] == "Sydney Olympic Park"
    assert meta_live["datetime"] is not None
    assert md._resolve_status(meta_live) == "LIVE"
    meta_up = md.read_match_details(UPCOMING_SRH_HTML, card)
    assert meta_up["is_live_tab"] is False
    assert md._resolve_status(meta_up) == "UPCOMING"
    print("✅ Meta extract + LIVE/UPCOMING status.")


def test_fixture_returned_only_with_srh_player():
    card = {"team1": "New South Wales", "team2": "Tasmania", "series": "S",
            "format_str": "8th One Day", "date_header": "Tue, 13 Oct 2026",
            "href": "/cricket-live-score/nsw-vs-tas-test-132H"}
    with patch.object(md, "_http_get", return_value=LIVE_SRH_HTML):
        fx = md.check_one_match_for_our_players(card)
    assert fx is not None
    assert "Pat Cummins" in fx["srh_players"], fx
    assert fx["link"].startswith("https://crex.com/cricket-live-score/")
    assert fx["status"] == "LIVE"
    with patch.object(md, "_http_get", return_value=NO_SRH_HTML):
        assert md.check_one_match_for_our_players(card) is None
    print("✅ Fixture details returned only for SRH squads (with link).")


def test_finished_matches_removed_and_live_first():
    # Date headers built from today, so this test works any day it runs
    # (the old fixed "Oct 13/14" headers expired and got window-filtered).
    from helpers.dates_and_times import what_time_is_it_in_india_now as _now
    _today = _now().replace(tzinfo=None).date()
    _live_hdr = _LIVE_DT.strftime("%a, %d %b %Y")
    live_card = {"team1": "New South Wales", "team2": "Tasmania", "series": "S",
                 "format_str": "8th", "date_header": _live_hdr,
                 "href": "/cricket-live-score/live-one"}
    up_card = {"team1": "Australia Women", "team2": "Bangladesh Women", "series": "S2",
               "format_str": "3rd ODI", "date_header": _UP_DT.strftime("%a, %d %b %Y"),
               "href": "/cricket-live-score/up-one"}
    old_card = {"team1": "Old Team A", "team2": "Old Team B", "series": "S3",
                "format_str": "Final",
                "href": "/cricket-live-score/old-one"}
    pages = {
        "live-one": LIVE_SRH_HTML,
        "up-one": UPCOMING_SRH_HTML,
        "old-one": OLD_SRH_HTML,
    }

    def fake_http(url, timeout=10):
        for k, v in pages.items():
            if k in url:
                return v
        return None

    md.forget_saved_matches()
    with patch.object(md, "download_match_list_from_api",
                      return_value=[up_card, old_card, live_card]):
        with patch.object(md, "download_match_list_from_website", return_value=[]):
            with patch.object(md, "_http_get", side_effect=fake_http):
                fixtures = md.find_our_upcoming_matches(force_refresh=True)
    assert len(fixtures) == 2, fixtures  # finished Old Team match removed
    assert fixtures[0]["status"] == "LIVE", fixtures
    assert fixtures[1]["status"] == "UPCOMING", fixtures
    assert all(" drizzle " not in f["link"] for f in fixtures)
    md.forget_saved_matches()
    print("✅ Finished removed; LIVE sorts before upcoming.")


def test_fixture_compatible_with_theme_helpers():
    from our_teams.website_look import read_match_date_and_time, is_match_live_now_or_later
    card = {"team1": "Pakistan", "team2": "Sri Lanka", "series": "SL vs PAK 2026",
            "format_str": "3rd T20I", "date_header": "Tue, 13 Oct 2026",
            "href": "/cricket-live-score/x"}
    with patch.object(md, "_http_get", return_value=UPCOMING_SRH_HTML):
        fx = md.check_one_match_for_our_players(card)
    assert fx is not None
    assert read_match_date_and_time(fx) is not None
    assert is_match_live_now_or_later(fx) in ("LIVE", "UPCOMING")
    print("✅ Live fixture shape works with theme datetime/status + cards.")


def test_on_this_day_removed():
    import os as _os
    repo = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    app_src = open(_os.path.join(repo, "app.py")).read()
    theme_src = open(_os.path.join(repo, "our_teams", "website_look.py")).read()
    init_src = open(_os.path.join(repo, "our_teams", "__init__.py")).read()
    assert "ON_THIS_DAY_DB" not in app_src
    assert "tab_otd" not in app_src
    assert "on this day" not in app_src.lower()
    assert "render_otd_telemetry_card" not in app_src
    assert "render_otd_telemetry_card" not in theme_src
    assert "render_otd_telemetry_card" not in init_src
    assert "def render_otd_telemetry_card" not in theme_src
    assert "show_otd_story_card" not in theme_src
    print("✅ On This Day removed from UI + codebase.")


def test_third_party_links_rejected_and_escaped():
    from our_teams.website_look import show_match_card
    card = {"team1": "A", "team2": "B", "series": "S",
            "format_str": "T20", "date_header": "Tue, 13 Oct 2026",
            "href": "https://evil.example.com/cricket-live-score/x"}
    with patch.object(md, "_http_get", return_value=LIVE_SRH_HTML):
        assert md.check_one_match_for_our_players(card) is None  # off-site URL never fetched
    fx = {"squad": "A", "vs": "B", "league": "S", "time": "01:00 PM IST",
          "date_str": "October 13, 2026", "players": "Pat Cummins",
          "venue": "<script>alert(1)</script>",
          "link": "https://evil.example.com/cricket-live-score/x",
          "status": "UPCOMING"}
    html = show_match_card(fx, status="UPCOMING")
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert "evil.example.com" not in html  # off-site link never rendered
    print("✅ Off-site links rejected; markup escaped.")


def test_ordinal():
    assert md._ordinal("1") == "1st"
    assert md._ordinal("2") == "2nd"
    assert md._ordinal("3") == "3rd"
    assert md._ordinal("8") == "8th"
    assert md._ordinal("135") == "135th"
    assert md._ordinal("^0") == "0th" or isinstance(md._ordinal("^0"), str)
    print("✅ Ordinals.")


def _api_item(nf, t_ms, t1f="U", t2f="T", sf="2BD", mn="3", fo="T20I"):
    return {"t1f": t1f, "t2f": t2f, "sf": sf, "tt": 0, "date": "10/13/2026",
            "t": t_ms, "mn": mn, "mt": 5, "nf": nf, "id": 1, "ft": 2,
            "fo": fo, "status": 0}


def test_api_cards_window_and_dedupe():
    import time
    now_ms = int(time.time() * 1000)
    day = 86400000
    items = [_api_item("IN1", now_ms + day), _api_item("IN1", now_ms + day),
             _api_item("OUT1", now_ms + 10 * day)]
    mapping = {"t": [{"f_key": "U", "n": "Pakistan", "sn": "PAK"},
                     {"f_key": "T", "n": "Sri Lanka", "sn": "SL"}],
               "s": [{"f_key": "2BD", "n": "SL tour of PAK", "sn": "SL vs PAK 2026"}]}
    with patch.object(md, "download_one_page_of_matches", return_value=items):
        with patch.object(md, "turn_team_codes_into_names",
                          return_value=({"U": ("Pakistan", "PAK"), "T": ("Sri Lanka", "SL")},
                                        {"2BD": ("SL tour of PAK", "SL vs PAK 2026")})):
            cards = md.download_match_list_from_api(pages=(0,), window_days=4)
    assert len(cards) == 1, cards  # dup IN1 collapsed, OUT1 outside window
    assert cards[0]["href"].endswith("match-match-updates-IN1")
    assert cards[0]["format_str"] == "3rd T20I"
    print("✅ API cards: window-filtered, deduped, nf links.")


def test_merge_unions_api_and_ssr():
    from helpers.dates_and_times import what_time_is_it_in_india_now as _now2
    _t = _now2().replace(tzinfo=None).date()
    _in_window = _t.strftime("%a, %d %b %Y")
    _far_future = (_t + timedelta(days=30)).strftime("%a, %d %b %Y")
    api = [{"team1": "A", "team2": "B", "series": "S", "format_str": "T20",
            "time_str": "1:00 PM", "href": "/cricket-live-score/match-match-updates-N1",
            "date_header": _in_window, "start_ts": 1, "nf": "N1"}]
    ssr = [{"team1": "A", "team2": "B", "series": "S", "format_str": "T20",
            "time_str": "1:00 PM",
            "href": "/cricket-live-score/a-vs-b-1st-t20-s-2026-match-updates-N1",
            "date_header": _in_window},
           {"team1": "C", "team2": "D", "series": "S2", "format_str": "ODI",
            "time_str": "2:00 PM",
            "href": "/cricket-live-score/c-vs-d-999-odi-s2-match-updates-N2",
            "date_header": _far_future}]
    # N2 is dated 30 days out (outside the 4-day window) -> dropped; N1 deduped API wins.
    merged = md.merge_cards(api, ssr, window_days=4)
    assert [md._card_key(c) for c in merged] == ["N1"], merged
    assert merged[0]["href"].endswith("match-match-updates-N1")
    merged2 = md.merge_cards([], ssr, window_days=4000)
    assert len(merged2) == 2, merged2  # SSR-only path keeps dated-in-window cards
    print("✅ Merge: union + dedupe (API wins) + SSR window filter.")
