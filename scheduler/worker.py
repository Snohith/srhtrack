"""
Background Task Scheduler & Collector Worker for @SRHXtra.
Runs periodic RSS feeds, database refreshes, and alert generation.
"""

import time
from scrapers.rss_collector import fetch_and_filter_rss
from database.db_manager import init_db, insert_notification

def run_collector_cycle():
    """Runs one full ingestion cycle."""
    init_db()
    items_added = fetch_and_filter_rss()
    insert_notification(f"✅ Ingestion cycle complete. {items_added} new Sunrisers updates captured.", "SYSTEM")
    return items_added

if __name__ == "__main__":
    print("🚀 Starting @SRHXtra Background Collector Worker...")
    items = run_collector_cycle()
    print(f"Cycle finished. Captured {items} items.")
