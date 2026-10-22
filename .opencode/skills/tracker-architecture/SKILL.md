---
name: Tracker Architecture
description: Repository-specific architecture rules, dependency boundaries, invariants, and safe refactoring guidance for the Tracker application.
---

`AGENTS.md` is the project contract. Consult it first, before reasoning about any structural change.

## Responsibility boundaries

- `app.py` = Streamlit orchestration and UI only (startup sequencing, ingest scheduling, caching, tab rendering).
- `news_collectors/` = collection and normalization (feed fetching, retries, fallback, `clean_up_story_text`).
- `our_teams/players.py` = roster source loading and player/franchise matching.
- `our_teams/upcoming_matches.py`, `our_teams/website_look.py` = static fixture data and rendering helpers.
- `saved_stories/` = persistence, dedupe, retention, migrations, startup initialization.
- `regular_checks/check_news.py` = one-shot worker orchestration only.
- `tests/` = executable regression contract.

## Rules

- Avoid moving business rules into UI code. Matching, retention, and dedupe decisions belong in their owning modules, not in `app.py` or `theme.py`.
- Avoid introducing new global state or hidden startup side effects (module-import work, unguarded threads, cache writes at import time).
- Preserve dependency direction unless an explicit migration is proposed and justified.
- Before refactoring, identify: current boundary, problem, target boundary, migration sequence, and regression risk.
- Prefer incremental, reversible refactors with explicit rollback points.

## Architectural invariants (non-negotiable without explicit approval)

- `regular_checks/check_news.py` must not call `set_up_story_box()`.
- The roster source of truth remains the documented workbook flow (`data/squadofsunrisers.xlsx` canonical, root copy fallback).
- Per-target dedupe (`(link|title) + player_name + franchise`) remains intact; never global uniqueness.
- Source-list aliases (`TOP_50_CRICKET_SOURCES`, `RSS_FEEDS`, `CRICKET_SOURCES`) retain identity semantics with `NEWS_WEBSITES`.
- Retention semantics remain consistent (24-hour news window, 7-day notification pruning).

Explicitly identify architectural drift when existing code violates these principles. Do not recommend large rewrites merely to improve style; justify every structural change against a concrete defect, risk, or invariant violation, with file and line references.
