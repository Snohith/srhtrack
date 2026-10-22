"""
SRHXtra Scheduler Package.
Provides background ingestion workers and periodic maintenance jobs.
"""
from .check_news import do_one_news_check

__all__ = ["do_one_news_check"]
