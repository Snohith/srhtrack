"""
Headless ingest job tests (no DB, no network — collaborators mocked).
"""
from scripts import ingest_job


class _Result:
    def __init__(self, inserted, new_articles):
        self.inserted = inserted
        self.failed_feeds = []
        self.total_polled = 193
        self.new_articles = new_articles


def test_main_inits_db_before_cycle(monkeypatch):
    order = []
    monkeypatch.setattr(ingest_job, "init_db", lambda: order.append("init"))
    monkeypatch.setattr(
        ingest_job, "run_collector_cycle",
        lambda: (order.append("cycle"), _Result(2, [{"title": "T"}]))[1],
    )
    assert ingest_job.main() == 0
    assert order == ["init", "cycle"]


def test_main_returns_1_on_cycle_crash(monkeypatch):
    monkeypatch.setattr(ingest_job, "init_db", lambda: None)

    def _boom():
        raise RuntimeError("feeds unreachable")

    monkeypatch.setattr(ingest_job, "run_collector_cycle", _boom)
    assert ingest_job.main() == 1


def test_main_tolerates_plain_int_result(monkeypatch, capsys):
    monkeypatch.setattr(ingest_job, "init_db", lambda: None)
    monkeypatch.setattr(ingest_job, "run_collector_cycle", lambda: 3)
    assert ingest_job.main() == 0
    assert "3 fresh rows" in capsys.readouterr().out
