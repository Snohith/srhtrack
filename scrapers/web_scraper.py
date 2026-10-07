"""
Web Scraper & Resilient Headline Collector for @SRHXtra.
Scrapes match webpages and provides fallback article scraping when primary RSS feeds fail.
"""
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urljoin
from config.roster import match_player_or_franchise_in_text
from utils.logger import error_logger, rss_logger

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

def scrape_match_highlights(url):
    """Scrapes clean text snippet from match webpage."""
    try:
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            paragraphs = [p.get_text() for p in soup.find_all("p")]
            full_text = " ".join(paragraphs[:5])
            matches = match_player_or_franchise_in_text(full_text)
            return {"snippet": full_text[:400], "matched_players": matches}
    except Exception as e:
        return {"error": str(e), "snippet": "", "matched_players": []}
    return {"snippet": "", "matched_players": []}

def scrape_google_news_topic(query, lang="en-IN", gl="IN"):
    """
    Scrapes Google News RSS for targeted topics, leagues, or site mirrors.
    Provides 100% resilient fallback for dead, blocked, or paywalled RSS endpoints.
    """
    encoded_q = quote_plus(query)
    feed_url = f"https://news.google.com/rss/search?q={encoded_q}&hl={lang}&gl={gl}&ceid={gl}:{lang.split('-')[0]}"
    try:
        res = requests.get(feed_url, headers=HEADERS, timeout=6)
        if res.status_code == 200:
            feed = feedparser.parse(res.content)
            return feed.entries
    except Exception as e:
        error_logger.error(f"Google News topic fallback failed for '{query}': {e}")
    return []

def scrape_web_headlines(page_url, max_items=20):
    """
    Direct HTML scraper fallback when RSS feeds are offline or return 0 items.
    Parses headline tags (h1-h4, article cards) and extracts text and hyperlinks.
    """
    try:
        res = requests.get(page_url, headers=HEADERS, timeout=6)
        if res.status_code != 200:
            return []
        soup = BeautifulSoup(res.text, "html.parser")
        entries = []
        seen_titles = set()
        # Look for article links and headline headings
        for a_tag in soup.find_all("a", href=True):
            text = a_tag.get_text().strip()
            # Valid cricket headlines typically have 25+ chars
            if len(text) >= 25 and text not in seen_titles:
                seen_titles.add(text)
                full_link = urljoin(page_url, a_tag["href"])
                entries.append({
                    "title": text,
                    "summary": text,
                    "link": full_link,
                    "published_parsed": None,
                })
                if len(entries) >= max_items:
                    break
        return entries
    except Exception as e:
        error_logger.error(f"Direct HTML scrape failed for '{page_url}': {e}")
        return []

