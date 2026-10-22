"""Nightly 15-minute news check (runs on a helper computer; no browser needed).

Flow: set_up_story_box() (make tables + copy player list + tidy old stories) ->
do_one_news_check() (visit websites + text phones about fresh stories) -> summary.

set_up_story_box() lives HERE and not in regular_checks/check_news.py: the checker is one-shot
by design and a test forbids set_up_story_box() inside it. Fresh helper computers are
start empty, so without setup the stories file would have no tables.

Secrets arrive as env vars (the workflow maps repo Secrets). Telegram is
best-effort: alert failures never fail the job. Exit code is 1 only on
unexpected crashes so scheduled runs surface real breakage.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from saved_stories.story_storage import set_up_story_box
from regular_checks.check_news import do_one_news_check


def main():
    set_up_story_box()
    try:
        result = do_one_news_check()
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
        f"nightly_news_job: {inserted} fresh stories saved; "
        f"{len(new_articles) if new_articles is not None else '?'} alert candidates."
    )
    try:
        from helpers.phone_alerts import are_phone_alerts_ready
        print(f"nightly_news_job: phone texts {'configured' if are_phone_alerts_ready() else 'UNCONFIGURED (no DMs)'}")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
