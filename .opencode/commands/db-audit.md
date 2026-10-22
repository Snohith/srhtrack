---
description: Audit SQLite schema, queries, concurrency, retention, deduplication, and migration safety.
agent: data-engineer
subagent: false
---

This command runs in the current session (same-session execution, no background child session).

Load the `tracker-sqlite` skill.

Audit `$ARGUMENTS` when provided; otherwise inspect the database layer and any current changes affecting it.

Explicitly verify:

* per-target deduplication
* indexes
* parameterized queries
* transaction boundaries
* connection lifecycle
* concurrency/WAL/busy-timeout behavior
* retention
* purge behavior
* startup initialization
* worker behavior
* migration safety
* accidental destructive cleanup

Distinguish confirmed defects from theoretical concerns.

Never execute destructive database operations.

End with:
DB VERDICT: SAFE / CONCERNS / HIGH RISK
