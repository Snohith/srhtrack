"""
Centralized Structured Logging Module for @SRHXtra.
Creates isolated log files in logs/ directory for rss, scheduler, database, graphics, and errors.
Uses RotatingFileHandler (5 MB max, 3 backups) to prevent unbounded log growth.
"""
import os
import logging
from logging.handlers import RotatingFileHandler
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
def ensure_logs_dir():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
def get_logger(name, filename):
    """Creates a custom logger writing to a rotating log file (5 MB max, 3 backups)."""
    ensure_logs_dir()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        file_path = os.path.join(LOGS_DIR, filename)
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
rss_logger       = get_logger("RSS",       "rss.log")
db_logger        = get_logger("DB",        "database.log")
graphics_logger  = get_logger("Graphics",  "graphics.log")
scheduler_logger = get_logger("Scheduler", "scheduler.log")
error_logger     = get_logger("Error",     "errors.log")
