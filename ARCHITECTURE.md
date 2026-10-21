# Architecture

SRHXtra is a Telegram-only news alert service. One scheduled process collects
cricket RSS stories, matches them against the Sunrisers roster, and delivers
each new article through the Telegram Bot API. SQLite is both the article store
and the delivery ledger.

## Goals

- Poll 268 configured RSS sources without letting one bad source stop a sweep.
- Keep only stories about the four Sunrisers franchises or the people attached
  to them.
- Send one Telegram message per unique relevant article, with every matching
  player, team, and ownership label combined.
- Never mark an article delivered merely because it was stored.
- Survive Telegram rate limits, transient network failures, process crashes,
  and overlapping scheduler runs.
- Keep all runtime secrets in environment variables.
- Remove the dashboard, command bot, match scraper, and their dependencies.

## Runtime topology

```
cron (every 5 minutes)
  └─ python -m regular_checks.check_news
       ├─ collector_lock()                  one non-blocking flock
       ├─ load_env() + configure_logs()
       ├─ reload_roster()                   read-only Excel load
       ├─ set_up_story_box()                schema + legacy migration + stale claims
       ├─ collect_fresh_stories()           network workers, no Telegram
       │    ├─ feed_is_due()                 per-feed backoff
       │    ├─ _download_feed()              HTTP + feedparser
       │    └─ save_article()                article + pending delivery transaction
       ├─ send_pending_alerts()              Telegram send loop
       │    ├─ claim_due_deliveries()        atomic claim
       │    ├─ send_telegram_message()
       │    └─ mark_delivery_sent/failed/dead
       └─ prune_expired()                    remove old terminal rows
```

The collector never sends Telegram messages. The sender never downloads RSS or
article pages. This split means a network failure in either half cannot silently
corrupt the other half's state.

## Module responsibilities

| Path | Responsibility |
|---|---|
| `regular_checks/check_news.py` | The only production entry point: argument parsing, lock, cycle order, exit codes, status/test/retry flags. |
| `news_collectors/collect_news.py` | `NEWS_WEBSITES` (268 feeds), due-feed selection, HTTP fetch, feed parsing, freshness/link filtering, roster matching, article extraction. |
| `our_teams/players.py` | Read-only Excel roster loader, franchise ownership, aliases, context guards, multi-franchise match results. |
| `saved_stories/story_storage.py` | SQLite connection management, schema setup, legacy migration, article insert + delivery queueing, atomic claims, retry transitions, feed health, pruning. |
| `saved_stories/tables.sql` | Canonical schema for `articles`, `deliveries`, `feed_health`, `suppressed_titles`. |
| `helpers/phone_alerts.py` | Telegram settings, HTML card formatting, send request, retry loop, explicit test message. |
| `helpers/links.py` | URL canonicalization and safety checks, article identity keys, title normalization. |
| `helpers/config.py` | The single `.env` loader and boolean env parsing. |
| `helpers/dates_and_times.py` | Feed timestamp parsing and IST display text. |
| `helpers/log_books.py` | Rotating logs; reconfigured after `.env` loads. |
| `handy_tools/validate_roster.py` | Read-only workbook/alias validation for CI and operators. |

Dependency direction is one-way: entry point → collectors/helpers → storage and
roster. Storage does not import collectors or the entry point.

## Database model

The schema file is `saved_stories/tables.sql`. The default database is
`saved_stories/sunrisers_news.db`; `SUNRISERS_DB_PATH` overrides it.

### `articles`

One row per unique relevant story.

| Column | Meaning |
|---|---|
| `id` | Auto-increment primary key. |
| `dedupe_key` | `url:<sha256>` of the canonical link, or a title fallback. Unique. |
| `title_key` | Normalized headline for cross-feed duplicate detection. Unique. |
| `title`, `source`, `summary`, `link` | Display data. `link` is always a validated public URL. |
| `published_at`, `published_ts` | Display text and sortable timestamp. Unknown dates are allowed. |
| `people`, `franchises`, `topics` | JSON arrays of all matching labels. |
| `first_seen_ts` | Used by retention pruning. |

The unique constraints ensure one alert per article even when the same story
arrives from several feeds. A title collision is deliberately treated as the
same article for alert purposes.

### `deliveries`

Exactly one row per article, created in the same transaction as the article.

| Column | Meaning |
|---|---|
| `article_id` | Primary key and foreign key to `articles`. |
| `status` | `pending`, `sending`, `sent`, or `failed`. |
| `attempts` | Number of send attempts, capped at five. |
| `next_attempt_ts` | Earliest time this row may be claimed again. |
| `claimed_at` | When a worker took the row; `NULL` after a terminal transition. |
| `sent_at`, `last_error`, `updated_at` | Audit fields. |

The article insert and `pending` delivery insert are committed atomically. There
is no code path that marks a newly stored article as sent.

### `feed_health`

Per-feed failure count and next attempt time. A successful sweep deletes the
row. A failure stores exponential backoff capped at six hours, so a dead feed is
not hit every five minutes.

### `suppressed_titles`

Migration-only memory for recent titles from the old dashboard's
`alerted_stories` table. It keeps those titles quiet for the remainder of their
14-day life, then is pruned. New deduplication uses `articles`.

## Collection and matching

`collect_fresh_stories()`:

1. Selects feeds whose `feed_health.next_attempt_ts` is due.
2. Polls them with a bounded `ThreadPoolExecutor`.
3. Records success or a per-feed failure. One failed feed never aborts the
   sweep.
4. Cleans title/summary HTML.
5. Canonicalizes and validates the link.
6. Skips stories older than 24 hours.
7. Runs the roster matcher over title + summary.
8. Inserts the article and a `pending` delivery.
9. Returns a `CollectionResult` for logs and tests.

A feed that returns HTTP 200 but zero entries is treated as failed; a 4xx does
not get retried in the same sweep. `FETCH_RETRIES` is intentionally one attempt
by default so 268 feeds can finish well inside the five-minute interval.

The matcher (`find_our_players_in_story`) produces one match per roster row. A
person listed under two franchises therefore produces two labels. Team-name
matches produce a franchise label, and tracked owners/management produce a
`topic` or `person` label. `_summarise_matches` combines all of them into the
three JSON arrays stored on the article.

False-positive controls:

- full-name matching is word-boundary based;
- ambiguous bare surnames are listed and, where needed, require cricket context;
- `Abhishek Porel`, `Ishan Porel`, `SEC filing`, and `Brookfield` are guarded;
- American-sports phrases are ignored unless cricket context is also present.

The roster is read with `openpyxl` in read-only mode. No code saves the
workbook. `reload_roster()` re-reads it after `.env` is loaded so
`SUNRISERS_ROSTER_PATH` works from either the process environment or `.env`.

## Delivery and retry semantics

`send_pending_alerts()`:

1. Checks `TELEGRAM_ENABLED`, token, and chat id. Missing configuration leaves
   rows `pending` and returns an `unconfigured` reason.
2. Claims at most one due row at a time, up to 20 per cycle.
3. Revalidates the link; an unsafe link becomes terminally `failed` without an
   HTTP call.
4. Formats an escaped HTML message and posts `sendMessage` with a validated link
   preview.
5. On success, marks `sent`; on a retryable failure, marks `pending` with
   backoff; on a permanent 4xx configuration error, marks `failed`.
6. Stops the loop on a transient outage or rate limit rather than hammering
   Telegram.

Retry delays are `60 * 2^(attempt-1)` seconds, capped at one hour, and raised to
honor Telegram's `retry_after`. After five attempts the row becomes `failed` and
is only retried if an operator runs `--retry-failed`.

The claim update is conditional inside `BEGIN IMMEDIATE`, so two workers cannot
both move the same row from `pending` to `sending`. A `sending` row older than
15 minutes is recovered as `pending` (or `failed` if it already used all five
attempts).

There is one unavoidable duplicate window: if Telegram accepts a message and
the process dies before SQLite records `sent`, the stale claim is retried after
15 minutes and the message may appear twice. Telegram has no idempotency key,
so the design favors not losing alerts over absolute exactly-once delivery.

## Concurrency and locking

`collector_lock()` uses `fcntl.flock(..., LOCK_EX | LOCK_NB)` on a lock file next
to the database. A second cron run exits with status 0 and a log line rather
than waiting. SQLite uniqueness and atomic claims are the second line of
defense. WAL mode and a 30-second busy timeout allow the short-lived storage
connections to coexist with each other.

On platforms without `fcntl`, the lock degrades to no-op; the SQLite constraints
still prevent duplicate articles and claims, but overlapping runs can do
redundant work. The documented deployment target is a Unix-like local cron
machine.

## Scheduler decision

Local cron with persistent disk is the chosen scheduler because the delivery
ledger is local SQLite. GitHub Actions caches and ephemeral runners cannot be
treated as a reliable ledger. All scheduled workflows were removed; CI remains
the only GitHub Actions workflow.

The exact cron line is documented in `README.md`. Five minutes is the target
interval. A run that takes longer than five minutes is protected by the lock,
and the next invocation exits until the current one finishes.

## Security

- Secrets are read from the process environment or an untracked `.env`; library
  imports do not load `.env`.
- The Telegram token is never logged. Error logs contain exception type, status,
  and Telegram's description, not the request URL.
- Article links are untrusted input. They are validated before storage and
  again before sending. Article pages and images are never fetched server-side.
- The old git remote contained an embedded GitHub token. It was removed from
  `.git/config`; the token should be revoked manually.
- `.env`, SQLite databases, WAL/SHM files, locks, and logs are gitignored.

## Testing design

`tests/conftest.py` gives every test a temporary database and log directory and
forces `TELEGRAM_ENABLED=false` with empty credentials. All RSS and Telegram HTTP
calls are monkeypatched. Tests cover:

- fresh schema and idempotent setup;
- legacy table migration;
- roster counts, read-only validation, and actionable load errors;
- multi-franchise and alias matching, false-positive guards;
- URL scheme/host/IP validation and title normalization;
- collector isolation, dedupe, stale/malformed entries, feed backoff;
- atomic claims and stale-claim recovery;
- successful sends, no resend, retry backoff, attempt cap, 429 handling,
  permanent failures, escaping, and no image fetch;
- entry-point ordering, lock exclusion, roster/config failures, and status/test
  flags;
- removal of the dashboard and command-bot modules.

## Removed surface

The following were removed because they are not part of the Telegram alert
service: `app.py`, `bot.py`, `phone_bot.py`, `.streamlit/`, match scraping and
fixture helpers, dashboard rendering helpers, backup news scraping, nightly and
refresh scripts, dashboard-only tables/tests/docs, the root duplicate roster,
scheduled GitHub workflows, and Streamlit/pandas/Pillow dependencies.

The operator-facing migration steps are listed under “Manual disable checklist”
in `README.md`.
