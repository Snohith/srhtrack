"""
Web Scraper module for fetching match scorecards and official press releases.
"""

import requests
from bs4 import BeautifulSoup
from config.roster import match_player_in_text

def scrape_match_highlights(url):
    """Scrapes clean text snippet from match webpage."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = [p.get_text() for p in soup.find_all("p")]
            full_text = " ".join(paragraphs[:5])
            matches = match_player_in_text(full_text)
            return {"snippet": full_text[:400], "matched_players": matches}
    except Exception as e:
        return {"error": str(e), "snippet": "", "matched_players": []}
    return {"snippet": "", "matched_players": []}
