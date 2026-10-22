"""Old front door, kept for friends with old links.

We moved to phone_bot.py (a friendlier name).
This tiny file just forwards everything there,
so `import bot` keeps working.
"""
from phone_bot import *  # noqa: F401,F403
from phone_bot import CommandBot, is_owner, parse_command, format_status, main  # noqa: F401
