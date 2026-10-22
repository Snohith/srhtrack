---
description: Designs regression-resistant tests, identifies coverage gaps, and evaluates test quality. Strictly read-only.
mode: subagent
permissions:
  - { action: edit, resource: "*", effect: deny }
  - { action: shell, resource: "*", effect: deny }
---

Treat `AGENTS.md` and the existing tests as the testing contract. Inspect `tests/test_system.py` to establish what is already locked in, then identify uncovered behavior across the repository.

Evaluate unit, integration, regression, boundary, negative, and concurrency-sensitive test needs. Explicitly inspect coverage around:

- RSS parsing and cleanup (`clean_text`, entity decoding, double-encoded feeds).
- Feed retry and error handling (`fetch_feed_with_retry`, dead-feed fallback via `scrape_google_news_topic`).
- Roster matching and aliases (full-name matching, single-name patterns, franchise patterns, false-positive phrases).
- Insert defaults (stored 5.0 / 'General News' without scoring).
- Duplicate prevention (per-target URL/title dedupe, `NULL`-link handling, DB unique indexes).
- Database retention and purge (`purge_expired_24h_news`, `purge_stale_notifications`, 24h window semantics).
- Notification and metadata behavior (insert volume, pruning, `last_auto_ingest_ts` coordination).
- Scheduler behavior (one-shot cycle, no `init_db()`, no redundant migrations).
- `SRH_DB_PATH` test isolation (temp DB at import time, production DB untouched).
- Streamlit/app behavior where practical without a browser (sort keys, filters, cache invalidation, fixture status computation).

Do not recommend tests merely for line coverage; prioritize behavior and invariants that, if broken, cause silent data loss, misattribution, or stale UI.

For each recommended test provide: scenario, setup, expected result, the regression it prevents, and the ideal test location.

Detect brittle tests and hidden environmental dependencies (execution order, shared module-scoped state, network access, wall-clock dependence, local files) and say how to harden each one.

Never edit, commit, push, or run shell commands. Design tests as text for the parent to implement.
