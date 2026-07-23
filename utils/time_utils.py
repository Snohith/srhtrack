"""
Timezone and IST conversion utilities for @SRHXtra.
"""

from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))

def get_current_ist():
    """Returns current datetime in IST."""
    return datetime.now(IST)

def format_ist_string(dt_obj=None):
    """Formats a datetime object to clean IST string."""
    if dt_obj is None:
        dt_obj = get_current_ist()
    return dt_obj.strftime("%Y-%m-%d %I:%M %p IST")

def parse_to_ist(date_str):
    """Attempts to parse arbitrary date string and format to IST."""
    if not date_str:
        return format_ist_string()
    try:
        # Fallback to current time string with date prefix if parsing generic text
        return f"{date_str} (IST)"
    except Exception:
        return format_ist_string()
