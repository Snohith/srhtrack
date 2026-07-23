"""
Centralized Structured Logging Module for @SRHXtra.
Creates isolated log files in logs/ directory for rss, scheduler, database, graphics, and errors.
"""

import os
import logging

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")

def ensure_logs_dir():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

def get_logger(name, filename):
    """Creates a custom logger writing to specified log file."""
    ensure_logs_dir()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        file_path = os.path.join(LOGS_DIR, filename)
        handler = logging.FileHandler(file_path)
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s', '%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    return logger

# Pre-defined loggers
rss_logger = get_logger("RSS", "rss.log")
db_logger = get_logger("DB", "database.log")
graphics_logger = get_logger("Graphics", "graphics.log")
scheduler_logger = get_logger("Scheduler", "scheduler.log")
error_logger = get_logger("Error", "errors.log")
