"""
Timezone and 12-Hour AM/PM IST conversion utilities for @SRHXtra.
"""

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

def parse_to_12hr_ist(date_str):
    """Attempts to parse string and format into 12-hour AM/PM IST format."""
    if not date_str:
        return format_ist_12hr()
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M IST")
        return dt.strftime("%b %d, %Y @ %I:%M %p IST")
    except Exception:
        return f"{date_str}"
