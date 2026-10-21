"""
Plain date and time helpers for Sunrisers fans.

Everything here works in Indian time (IST, UTC+5:30):
- what time is it in India right now?
- show a date the friendly Indian way ("Oct 13, 2026 @ 10:00 AM IST")
- read a news website's date and turn it into Indian time
"""
import time
import calendar
from datetime import datetime, timedelta, timezone
INDIAN_TIME = timezone(timedelta(hours=5, minutes=30))
# Old name, kept so older guides still work.
IST = INDIAN_TIME
def what_time_is_it_in_india_now():
    """What time is it in India right now?"""
    return datetime.now(INDIAN_TIME)
def show_indian_time(dt_obj=None):
    """Show a date the friendly Indian way, like "Oct 13, 2026 @ 10:00 AM IST"."""
    if dt_obj is None:
        dt_obj = what_time_is_it_in_india_now()
    return dt_obj.strftime("%b %d, %Y @ %I:%M %p IST")
def read_story_date_as_indian_time(entry):
    """Read a news website's date and turn it into Indian time.

    Returns three simple things:
    - friendly date text ("Oct 13, 2026 @ 10:00 AM IST")
    - how old the story is, in hours
    - the exact moment as a number (so newest stories sort first)
    Stories from the future count as "just now".
    Stories with no date count as half an hour old.
    """
    now_utc = datetime.now(timezone.utc)
    pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if pub_parsed:
        try:
            pub_ts = float(calendar.timegm(pub_parsed))
            dt_utc = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
            dt_ist = dt_utc.astimezone(INDIAN_TIME)
            age_hours = (now_utc - dt_utc).total_seconds() / 3600.0
            age_hours = max(0.0, age_hours)
            return dt_ist.strftime("%b %d, %Y @ %I:%M %p IST"), age_hours, pub_ts
        except Exception:
            pass
    dt_ist = what_time_is_it_in_india_now()
    current_ts = float(time.time())
    return dt_ist.strftime("%b %d, %Y @ %I:%M %p IST"), 0.5, current_ts

# Old names, kept so older guides and tests still work.
parse_to_ist = read_story_date_as_indian_time
format_ist_12hr = show_indian_time
format_ist_string = show_indian_time
get_current_ist = what_time_is_it_in_india_now
