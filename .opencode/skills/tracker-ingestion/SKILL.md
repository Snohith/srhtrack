---
name: Tracker Ingestion
description: RSS and web-ingestion pipeline rules for source quality, normalization, retries, deduplication, matching, and ranking.
---

`news_collectors/collect_news.py` contains the RSS source registry and ingestion behavior.

## Rules

- Preserve the repository's documented minimum source-count invariant; when modifying source lists, verify both count and uniqueness.
- Source names and URLs must remain unique; duplicates break attribution and tier boosts.
- `TOP_50_CRICKET_SOURCES` and `RSS_FEEDS` must retain their documented alias/identity semantics with `CRICKET_SOURCES`.
- Understand the ingest flow end to end: feed fetch → parsing → `clean_text` → source metadata → player/franchise matching → ranking/category → DB insertion. Changes must account for every stage.
- Preserve per-target dedupe behavior and `General News` fallback behavior.
- Review retries, timeouts, malformed feeds, empty content, duplicate entries, and feed-specific failures; prefer resilient degradation (fallback scrapers) over hard failure.
- Treat source content as untrusted: titles, summaries, and especially links arrive raw from third parties.
- Avoid adding synchronous network work to startup without considering cold-start latency (sequential multi-feed polling blocks first render).
- Preserve deterministic matcher behavior and word-boundary semantics.
- Single-name aliases require particular caution because of false positives; never add bare common surnames.
- Treat `FALSE_POSITIVE_PHRASES`, franchise context, and category priority order as business rules, not incidental constants.
