---
name: Tracker SQLite
description: SQLite schema, transaction, concurrency, deduplication, retention, and migration rules for Tracker.
---

`saved_stories/tables.sql` and `saved_stories/story_storage.py` are the primary data-layer references. Verify claims against the actual SQL and code, not against docs or comments.

## Rules

- The dedupe invariant is per target: `(link|title) + player_name + franchise`. It must not become global uniqueness on `news.link` or `news.title`.
- Preserve `idx_news_link_target` and `idx_news_title_target` semantics, including the `WHERE link IS NOT NULL` partial index.
- Preserve `General News` defaults consistently between schema and insertion logic.
- Review connection lifecycle, transaction boundaries, commit placement, and rollback behavior on every data path.
- Review WAL/busy-timeout behavior and concurrent readers/writers. Treat startup ingest, background ingest, manual refresh, scheduler worker, and purge jobs as potentially concurrent.
- Review destructive cleanup carefully for false negatives and accidental data loss (player reseed, hardcoded deletes, matcher-driven purges, zero-timestamp migration).
- Preserve 24-hour news retention and 7-day notification pruning semantics.
- Treat migrations as compatibility-sensitive: legacy table rebuilds, added columns, and `INSERT OR IGNORE` data loss all need explicit reasoning.
- Check indexes against actual query patterns rather than adding indexes blindly.
- Flag lock contention, race conditions, partial writes, and migration hazards; classify each as confirmed or theoretical.
- Never execute destructive database operations as part of analysis. Propose SQL and schema changes as text only.
