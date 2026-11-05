"""Markup and safety checks for the custom UI components."""
from our_teams.website_look import (
    show_story_card,
    show_big_story,
    show_player_grid,
    show_stat_cards,
    show_empty_state,
    show_pulse_panel,
)


def test_story_cards_escape_content_and_open_links_safely():
    story = {
        "title": "<script>alert(1)</script>",
        "summary": "<img src=x>",
        "player_name": "<b>Player</b>",
        "franchise": "SRH",
        "source": "Wire",
        "published_at": "now",
        "pub_timestamp": 0,
        "link": "https://example.com/story",
    }
    for html in (show_story_card(story), show_big_story(story)):
        assert "<script>" not in html
        assert "<img src=x>" not in html
        assert "&lt;script&gt;" in html
        assert "rel='noopener noreferrer'" in html
        assert "target='_blank'" in html


def test_pulse_panel_is_one_complete_list():
    news = [
        {"title": f"Headline {i}", "player_name": "Player", "pub_timestamp": 0, "link": "https://example.com"}
        for i in range(3)
    ]
    html = show_pulse_panel(news)
    assert html.startswith("<div class='pulse-panel'>")
    assert html.endswith("</div>")
    assert html.count("<li") == 3
    assert "<ol class='pulse-list'>" in html and "</ol>" in html


def test_player_and_stat_helpers_escape_text():
    grid = show_player_grid([{"name": "<b>Name</b>", "role": "Batter", "country": "India"}], "Sunrisers Hyderabad")
    assert "&lt;b&gt;Name&lt;/b&gt;" in grid
    assert "<b>Name</b>" not in grid
    assert show_stat_cards([("<x>", "Label")]).count("&lt;x&gt;") == 1
    empty = show_empty_state("<Title>", "<Message>")
    assert "&lt;Title&gt;" in empty and "role='status'" in empty
