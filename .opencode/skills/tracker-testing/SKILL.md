---
name: Tracker Testing
description: Behavior-first testing strategy, regression design, coverage analysis, and test isolation rules for Tracker.
---

Tests protect behavior and invariants, not line counts. The existing `tests/test_system.py` is part of the regression contract — understand what it locks in before proposing changes.

## Prioritize coverage for

- RSS parsing and cleanup (tag stripping, entity decoding, double-encoded feeds).
- Retry and error handling (attempts, backoff, timeouts, dead-feed fallback).
- Feed metadata handling (missing/future timestamps, empty entries).
- Roster matching and aliases (full names, single-name patterns, franchise patterns, false-positive guards).
- Insert defaults (stored 5.0 / 'General News' without per-article scoring).
- Duplicate prevention (per-target URL/title dedupe, placeholder-link coercion, unique indexes).
- SQLite retention and purge (24-hour window, stale-row migration, notification pruning).
- Notifications and metadata (`last_auto_ingest_ts` coordination, write volume).
- Scheduler behavior (one-shot cycle, no `init_db()`, no redundant migrations).
- `SRH_DB_PATH` isolation (temp database at import time; production database untouched).
- Environment and configuration behavior (defaults, overrides, missing values).

## Rules

- Include positive, negative, boundary, and regression tests for behavior changes.
- Avoid tests coupled to incidental implementation details (log strings, exact HTML, internal helper names).
- Tests must not depend on the real production database; use isolated temp databases.
- Use deterministic inputs; stub external feeds and services — no network in tests.
- When changing behavior, explicitly identify the regression test that should fail before the fix.
- Flag brittle tests, time-dependent tests, network-dependent tests, and shared-state leakage (module-scoped fixtures, execution-order dependence).
- Keep test setup and teardown explicit and isolated; each test must be runnable alone and in any order.
