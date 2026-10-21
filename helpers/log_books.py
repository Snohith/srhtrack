"""Rotating log files for the collector.

Logs never contain the Telegram token or chat id.  Set SUNRISERS_LOG_DIR to
put the files somewhere other than the repository's logs/ directory.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.environ.get("SUNRISERS_LOG_DIR", os.path.join(PROJECT_ROOT, "logs"))
_LOG_FILES = (("RSS", "rss.log"), ("DB", "database.log"), ("Error", "errors.log"))


def make_sure_diary_folder_exists():
    os.makedirs(LOG_DIR, exist_ok=True)


def _make_handler(filename):
    make_sure_diary_folder_exists()
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, filename),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
    )
    return handler


def make_a_diary(name, filename):
    make_sure_diary_folder_exists()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(_make_handler(filename))
        logger.propagate = False
    return logger


news_diary = make_a_diary("RSS", "rss.log")
storage_diary = make_a_diary("DB", "database.log")
problems_diary = make_a_diary("Error", "errors.log")


def configure_logs():
    """Re-point the diaries after the entry point has loaded .env."""
    global LOG_DIR
    LOG_DIR = os.environ.get("SUNRISERS_LOG_DIR", os.path.join(PROJECT_ROOT, "logs"))
    for name, filename in _LOG_FILES:
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)
        logger.addHandler(_make_handler(filename))
        logger.propagate = False

LOGS_DIR = LOG_DIR
get_logger = make_a_diary
ensure_logs_dir = make_sure_diary_folder_exists
rss_logger = news_diary
db_logger = storage_diary
error_logger = problems_diary
