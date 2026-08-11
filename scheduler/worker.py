"""
Background Task Scheduler & Collector Worker for @SRHXtra.
Runs periodic RSS feeds, database refreshes, and alert generation.
Note: init_db() is intentionally NOT called here. It is already called on app startup
(app.py line 45). Calling it inside every collector cycle would trigger migrations,
roster re-seeding, and stale-row cleanups redundantly on every tick.
"""
import time
from scrapers.rss_collector import fetch_and_filter_rss
from database.db_manager import insert_notification
def run_collector_cycle():
    """Runs one full ingestion cycle (RSS poll + notification)."""
    items_added = fetch_and_filter_rss()
    insert_notification(f"✅ Ingestion cycle complete. {items_added} new Sunrisers updates captured.", "SYSTEM")
    return items_added
if __name__ == "__main__":
    print("🚀 Starting @SRHXtra Background Collector Worker...")
    items = run_collector_cycle()
    print(f"Cycle finished. Captured {items} items.")
