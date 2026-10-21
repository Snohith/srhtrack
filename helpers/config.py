"""Environment loading shared by the collector and its diagnostics.

Secrets live in environment variables (or an untracked .env file).  This is
the only place that reads .env; importing a library module never has the side
effect of loading secrets.
"""
from __future__ import annotations

import os


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_env(path=None):
    """Load KEY=VALUE lines from .env without overriding real env vars."""
    env_path = path or os.path.join(repo_root(), ".env")
    try:
        with open(env_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        return
    except OSError as exc:
        raise RuntimeError(f"Could not read {env_path}: {exc}") from exc


def env_bool(name, default=False):
    value = str(os.environ.get(name, "")).strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "y", "on")
