"""
Friendly nightly news-check tests (no filing box, no network — helpers faked).
"""
from handy_tools import nightly_news_job as ingest_job


class _Result:
    def __init__(self, inserted, new_articles):
        self.inserted = inserted
        self.failed_feeds = []
        self.total_polled = 268
        self.new_articles = new_articles


def test_main_inits_db_before_cycle(monkeypatch):
    order = []
    monkeypatch.setattr(ingest_job, "set_up_story_box", lambda: order.append("init"))
    monkeypatch.setattr(
        ingest_job, "do_one_news_check",
        lambda: (order.append("cycle"), _Result(2, [{"title": "T"}]))[1],
    )
    assert ingest_job.main() == 0
    assert order == ["init", "cycle"]


def test_main_returns_1_on_cycle_crash(monkeypatch):
    monkeypatch.setattr(ingest_job, "set_up_story_box", lambda: None)

    def _boom():
        raise RuntimeError("feeds unreachable")

    monkeypatch.setattr(ingest_job, "do_one_news_check", _boom)
    assert ingest_job.main() == 1


def test_main_tolerates_plain_int_result(monkeypatch, capsys):
    monkeypatch.setattr(ingest_job, "set_up_story_box", lambda: None)
    monkeypatch.setattr(ingest_job, "do_one_news_check", lambda: 3)
    assert ingest_job.main() == 0
    assert "3 fresh stories saved" in capsys.readouterr().out
