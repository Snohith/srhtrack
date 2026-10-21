"""Test bootstrap: isolated DB, isolated logs, and no real Telegram sends."""
from __future__ import annotations

import os
import tempfile

import pytest

_ROOT = tempfile.mkdtemp(prefix="srh_test_")
os.environ["SUNRISERS_DB_PATH"] = os.path.join(_ROOT, "bootstrap.db")
os.environ.pop("SRH_DB_PATH", None)
os.environ["SUNRISERS_LOG_DIR"] = os.path.join(_ROOT, "logs")
# `.env` must never supply real credentials during tests.
os.environ["TELEGRAM_ENABLED"] = "false"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["TELEGRAM_CHAT_ID"] = ""


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("SUNRISERS_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SUNRISERS_LOG_DIR", str(tmp_path / "logs"))
    from saved_stories.story_storage import set_up_story_box

    set_up_story_box()
    yield


@pytest.fixture()
def telegram_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_ENABLED", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    return monkeypatch
