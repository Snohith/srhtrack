# Tracker Project Instructions

## Agent Skills

Skills are installed in `.agents/skills/`.

Before starting a task, inspect the task and load the relevant skill using OpenCode's built-in skill tool.

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
## Friendly folder map (human names)

- `our_teams/` — our players, matches and website look (was `config/`)
- `news_collectors/` — checking news websites and matches (was `scrapers/`)
- `saved_stories/` — our filing box of saved stories (was `database/`)
- `regular_checks/` — checking the news once right now (was `scheduler/`)
- `helpers/` — little helpers: diaries, dates, phone texts (was `utils/`)
- `handy_tools/` — handy one-off tools (was `scripts/`)
- `phone_bot.py` — chat bot for Telegram (was `bot.py`)
- Old function and bot names still work as aliases; the old folder names do not.
