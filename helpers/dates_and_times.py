"""Timezone-aware date helpers.

Feed timestamps are read as UTC (feedparser gives a struct_time in UTC) and
displayed in IST.  A missing date is reported honestly as unknown instead of
pretending the story is fresh.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone

INDIAN_TIME = timezone(timedelta(hours=5, minutes=30))
IST = INDIAN_TIME


def what_time_is_it_in_india_now():
    return datetime.now(INDIAN_TIME)


def show_indian_time(dt_obj=None):
    if dt_obj is None:
        dt_obj = what_time_is_it_in_india_now()
    return dt_obj.strftime("%b %d, %Y @ %I:%M %p IST")


def read_story_date_as_indian_time(entry):
    """Return (friendly IST text, age_hours or None, utc_timestamp).

    No timestamp -> ("", None, 0.0).  Future timestamps count as age 0.
    """
    parsed = (entry or {}).get("published_parsed") or (entry or {}).get("updated_parsed")
    if not parsed:
        return "", None, 0.0
    try:
        published_ts = float(calendar.timegm(parsed))
        published_utc = datetime.fromtimestamp(published_ts, tz=timezone.utc)
        age_hours = max(0.0, (datetime.now(timezone.utc) - published_utc).total_seconds() / 3600.0)
        return show_indian_time(published_utc.astimezone(INDIAN_TIME)), age_hours, published_ts
    except (TypeError, ValueError, OverflowError, OSError):
        return "", None, 0.0


def parse_to_ist(entry):
    return read_story_date_as_indian_time(entry)
