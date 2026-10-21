"""Environment loading tests."""
from __future__ import annotations

import os

from helpers.config import env_bool, load_env


def test_load_env_fills_missing_values_without_overriding_real_env(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "KEEP_ME=from-file\n"
        "ADD_ME='quoted value'\n"
        "# comment\n"
        "BROKEN_LINE\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KEEP_ME", "from-process")
    monkeypatch.delenv("ADD_ME", raising=False)
    try:
        load_env(str(env_file))
        assert os.environ["KEEP_ME"] == "from-process"
        assert os.environ["ADD_ME"] == "quoted value"
    finally:
        os.environ.pop("ADD_ME", None)


def test_load_env_missing_file_is_not_an_error(tmp_path):
    load_env(str(tmp_path / "does-not-exist.env"))


def test_env_bool_defaults_and_values(monkeypatch):
    monkeypatch.delenv("SOME_SWITCH", raising=False)
    assert env_bool("SOME_SWITCH", True) is True
    for value in ("1", "true", "YES", "on"):
        monkeypatch.setenv("SOME_SWITCH", value)
        assert env_bool("SOME_SWITCH", False) is True
    for value in ("0", "false", "no", "off"):
        monkeypatch.setenv("SOME_SWITCH", value)
        assert env_bool("SOME_SWITCH", True) is False
