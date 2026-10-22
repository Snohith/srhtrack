"""
Background Task Scheduler & Collector Worker for @SRHXtra.
Runs periodic RSS feeds, database refreshes, and alert generation.
Note: set_up_story_box() is intentionally NOT called here. It already runs when the website starts
(app.py). Calling it on every check would rebuild tables,
copy the player list and tidy old stories again on every tick.
"""
import time
from news_collectors.collect_news import collect_fresh_stories
from saved_stories.story_storage import leave_a_note
def do_one_news_check():
    """Check all the news websites once, save anything fresh about our players."""
    items_added = collect_fresh_stories()
    leave_a_note(f"✅ News check finished. {items_added} new Sunrisers updates captured.", "SYSTEM")
    return items_added
if __name__ == "__main__":
    print("🚀 Checking the news for Sunrisers fans...")
    items = do_one_news_check()
    print(f"Done. Saved {items} fresh stories.")

# Old name, kept so older guides and tests still work.
run_collector_cycle = do_one_news_check
