"""
Centralized Structured Logging Module for @SRHXtra.
Creates isolated log files in logs/ directory for rss, scheduler, database, graphics, and errors.
Uses RotatingFileHandler (5 MB max, 3 backups) to prevent unbounded log growth.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
WHERE_WE_WRITE_DIARIES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
def make_sure_diary_folder_exists():
    if not os.path.exists(WHERE_WE_WRITE_DIARIES):
        os.makedirs(WHERE_WE_WRITE_DIARIES)
def make_a_diary(name, filename):
    """Creates a custom logger writing to a rotating log file (5 MB max, 3 backups)."""
    make_sure_diary_folder_exists()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        file_path = os.path.join(WHERE_WE_WRITE_DIARIES, filename)
        handler = RotatingFileHandler(
            file_path,
            maxBytes=5 * 1024 * 1024,  
            backupCount=3,              
            encoding="utf-8",
        )
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
news_diary       = make_a_diary("RSS",       "rss.log")
storage_diary        = make_a_diary("DB",        "database.log")
app_diary       = make_a_diary("App",       "app.log")
pictures_diary  = make_a_diary("Graphics",  "graphics.log")
checker_diary = make_a_diary("Scheduler", "scheduler.log")
problems_diary     = make_a_diary("Error",     "errors.log")

# Old names, kept so older guides and tests still work.
get_logger = make_a_diary
ensure_logs_dir = make_sure_diary_folder_exists
LOGS_DIR = WHERE_WE_WRITE_DIARIES
rss_logger = news_diary
db_logger = storage_diary
app_logger = app_diary
graphics_logger = pictures_diary
scheduler_logger = checker_diary
error_logger = problems_diary
