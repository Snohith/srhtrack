# AGENTS.md — SRHXtra (srhtrack)

Streamlit + SQLite cricket news intelligence app. Python `>=3.9` (CI pins `3.11`). Entry point: `app.py`.

## Commands

```bash
pip install -r requirements.txt  # or: make install
streamlit run app.py              # or: make run (port 8501 per .streamlit/config.toml)
pytest tests/                     # or: make test (only suite; single file: tests/test_system.py)
python scripts/update_squads.py   # or: make sync-squads — rewrites roster Excel
```

- `pytest.ini` wins over `pyproject.toml [tool.pytest.ini_options]` (both set `testpaths=tests`, `pythonpath=.`).
- `make lint` is a phony target with no recipe (no-op) — do not rely on it. Format is black/ruff, `line-length=100` (`pyproject.toml`).
- CI (`.github/workflows/ci.yml`): `pip install -r requirements.txt` + `pytest tests/ -v` on push/PR to `main`.

## Architecture (ingest pipeline)

```
156 RSS feeds (scrapers/rss_collector.py: CRICKET_SOURCES)
→ config/roster.py: match_player_or_franchise_in_text()
→ database/db_manager.py → SQLite → app.py (4 Streamlit tabs)
```

- `TOP_50_CRICKET_SOURCES` and `RSS_FEEDS` must remain aliases of `CRICKET_SOURCES` (test asserts identity); keep source names/URLs unique, count `>= 48`.
- Ingest discards articles `>24h` old (`parse_rss_date_to_ist` in `utils/time_utils.py`; future/missing dates are clamped to pass). `fetch_feed_with_retry()` falls back to `scrape_google_news_topic()` on dead feeds.
- Dedupe is **per tracked target**, not global: `(link|title) + player_name + franchise` (`idx_news_link_target`, `idx_news_title_target` in `database/schema.sql`). Never re-add a global `UNIQUE` on `link`. Empty/`#` links are coerced to `NULL` in `insert_news()`.
- Articles are stored with database defaults (`importance_score=5.0`, `category='General News'`); per-article scoring was removed. `schema.sql` category default and `insert_news()` default must both stay `'General News'` (test-enforced).

## Roster (source of truth)

- `data/squadofsunrisers.xlsx` is canonical; repo-root `squadofsunrisers.xlsx` is legacy fallback (`config/roster.py: EXCEL_PATH`). `MASTER_ROSTER` keys: `SRH`, `SEC`, `Leeds_Men`, `Leeds_Women`.
- Matching order in `match_player_or_franchise_in_text()`: full Excel names → `PLAYER_ALIASES` single-name patterns → franchise patterns → generic `sunrisers` fallback; `FALSE_POSITIVE_PHRASES` (e.g. `nfl`, `mlb`, `baseball`) reject US-sports collisions.
- To change squads: edit `scripts/update_squads.py` (it preserves Leeds Women rows and writes **both** Excel copies), run `make sync-squads`. If a new player needs single-name matching, add a `PLAYER_ALIASES` entry with word-boundary regex.

## Gotchas

- `app.py` runs `init_db()` + `purge_expired_24h_news()` at import/startup, spawns a background ingest thread every `AUTO_INGEST_INTERVAL_SECS` (default `900`), JS page reload every 5 min, `st.cache_data(ttl=60)` on news queries. Never call `init_db()` from `scheduler/worker.py` — `run_collector_cycle()` is one-shot by design (test strips comments/docstrings and fails on any `init_db()` call).
- DB path: `SRH_DB_PATH` env overrides default `database/srh_tracker.db` (gitignored — never commit it). `tests/test_system.py` sets `SRH_DB_PATH` to a temp file **at import time**; always run tests as `pytest tests/` from repo root so the isolation holds and the prod DB is untouched.
- `init_db()` reseeds `players` from Excel, migrates legacy `pub_timestamp=0.0` rows, and purges `>24h` news + `>7d` notifications. There is a hardcoded cleanup of a known bad `'%Pranav, Irfan, Shashank%'` row — leave it.
- Logs (`utils/logger.py`, `RotatingFileHandler 5MB×3`) are written to `logs/` (`rss.log`, `database.log`, `errors.log`, …) and are gitignored; the logging test asserts `rss.log` + `database.log` exist after import.
- Env: copy `.env.example` → `.env` for `SRH_DB_PATH`, `AUTO_INGEST_INTERVAL_SECS`, `STREAMLIT_SERVER_PORT`. Do not commit `.env` or `.streamlit/credentials.toml`.
- Committed `venv/`, `__pycache__/`, `.pytest_cache/`, `*.log`, `generated/*.png` are ignored build artifacts — use `make clean`, don't delete source.
