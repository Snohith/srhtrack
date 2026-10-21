# Tracker Project Instructions

## Architecture contract

- This is a Telegram-only alert service. There is no dashboard, command bot,
  match scraper, or digest/heartbeat.
- `regular_checks/check_news.py` is the single production entry point. Local
  cron is the scheduler; do not add a competing GitHub Actions schedule.
- Collection and Telegram delivery are separate phases. The collector must not
  send messages, and the sender must not download RSS or article pages.
- `data/squadofsunrisers.xlsx` is the sole roster source. Never rewrite it from
  code or add a sync/regeneration script.
- SQLite is the delivery ledger. An article insert creates a `pending` delivery;
  only a confirmed Telegram response may mark it `sent`.
- One article produces one alert with all matching player/franchise/topic labels
  combined. Preserve atomic claims, bounded retries, and the no-overlap lock.
- Secrets come from environment variables or an untracked `.env` only.

## Agent Skills

Skills are installed in `.agents/skills/`.

Before starting a task, inspect the task and load the relevant skill using
OpenCode's built-in skill tool.

## Workflow

- For new features, use spec-driven-development and planning-and-task-breakdown.
- For bugs, use debugging-and-error-recovery.
- For code changes, use test-driven-development where appropriate.
- For multi-file changes, use incremental-implementation.
- Before merging, use code-review-and-quality.
- For security-sensitive changes, use security-and-hardening.

## Rules

- Inspect existing code before making changes.
- Follow the project's existing architecture and conventions.
- Do not modify unrelated files.
- Run relevant tests and report their actual results.
- Ask before destructive operations.
- Never expose secrets or credentials.
- Mock RSS and Telegram HTTP calls in tests; never send a real message from the
  test suite.

## Friendly folder map

- `our_teams/` — rostered players, coaches, aliases, and franchise matching.
- `news_collectors/` — the 268 RSS sources, fetch and filter pipeline.
- `saved_stories/` — SQLite articles and the delivery ledger.
- `regular_checks/` — the one scheduled collection + delivery cycle.
- `helpers/` — Telegram sending, link safety, env loading, dates, logs.
- `handy_tools/` — read-only operator tools such as the roster validator.
- `data/` — the canonical Excel roster.
- `tests/` — isolated, network-mocked regression tests.

Old function names are kept as aliases where practical; old module-level
dashboard/bot names are intentionally gone.

## Common commands

```bash
python -m pytest -q
python -m handy_tools.validate_roster
python -m regular_checks.check_news --status
python -m regular_checks.check_news
```
