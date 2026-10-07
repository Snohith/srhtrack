"""
SRHXtra Scheduler Package.
Provides background ingestion workers and periodic maintenance jobs.
"""
from .worker import run_collector_cycle

__all__ = ["run_collector_cycle"]
