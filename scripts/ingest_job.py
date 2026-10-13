"""Headless 15-minute ingest job (GitHub Actions; no browser needed).

Flow: init_db() (schema + roster reseed + retention purges) ->
run_collector_cycle() (RSS sweep + per-article Telegram alerts) -> summary.

init_db() lives HERE and not in scheduler/worker.py: the worker is one-shot
by design and a test forbids init_db() inside it. Fresh CI runners are
stateless, so without init the SQLite file would have no tables.

Secrets arrive as env vars (the workflow maps repo Secrets). Telegram is
best-effort: alert failures never fail the job. Exit code is 1 only on
unexpected crashes so scheduled runs surface real breakage.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_manager import init_db
from scheduler.worker import run_collector_cycle


def main():
    init_db()
    try:
        result = run_collector_cycle()
    except Exception:
        traceback.print_exc()
        return 1
    inserted = getattr(result, "inserted", result)
    try:
        inserted = int(inserted)
    except (TypeError, ValueError):
        inserted = 0
    new_articles = getattr(result, "new_articles", None)
    print(
        f"ingest_job: {inserted} fresh rows stored; "
        f"{len(new_articles) if new_articles is not None else '?'} alert candidates."
    )
    try:
        from utils.telegram import is_telegram_configured
        print(f"ingest_job: telegram {'configured' if is_telegram_configured() else 'UNCONFIGURED (no DMs)'}")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
