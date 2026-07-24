"""
Timezone and 12-Hour AM/PM IST conversion & RSS date parsing utilities for @SRHXtra.
Converts all RSS entry timestamps to accurate 12-Hour AM/PM IST and calculates numeric epoch timestamps for strict chronological sorting.
"""

import time
import calendar
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

def get_current_ist():
    """Returns current datetime in IST."""
    return datetime.now(IST)

def format_ist_12hr(dt_obj=None):
    """Formats a datetime object to clean 12-hour AM/PM IST string."""
    if dt_obj is None:
        dt_obj = get_current_ist()
    return dt_obj.strftime("%b %d, %Y @ %I:%M %p IST")

def format_ist_string(dt_obj=None):
    """Alias for 12-hour AM/PM IST formatting string."""
    return format_ist_12hr(dt_obj)

def parse_rss_date_to_ist(entry):
    """
    Parses original publication date from RSS entry, converts to IST, and returns:
    (formatted_ist_str, age_in_hours, pub_timestamp_float)
    """
    now_utc = datetime.now(timezone.utc)
    pub_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    
    if pub_parsed:
        try:
            pub_ts = float(calendar.timegm(pub_parsed))
            dt_utc = datetime.fromtimestamp(pub_ts, tz=timezone.utc)
            dt_ist = dt_utc.astimezone(IST)
            age_hours = (now_utc - dt_utc).total_seconds() / 3600.0
            return dt_ist.strftime("%b %d, %Y @ %I:%M %p IST"), age_hours, pub_ts
        except Exception:
            pass

    # Fallback to current time if feed lacks valid timestamp
    dt_ist = get_current_ist()
    current_ts = float(time.time())
    return dt_ist.strftime("%b %d, %Y @ %I:%M %p IST"), 0.0, current_ts
