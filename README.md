# SRHXtra — Sunrisers news, straight to Telegram

SRHXtra watches **268 cricket RSS feeds**, keeps only stories about the
Sunrisers family, and sends each new article to Telegram once.

It covers:

- Sunrisers Hyderabad (IPL)
- Sunrisers Eastern Cape (SA20)
- Sunrisers Leeds Men (The Hundred)
- Sunrisers Leeds Women (The Hundred Women)

There is no dashboard and no command bot. One scheduled command collects,
stores, and delivers the news. The Excel roster remains the only source of
truth for players and staff.

---

## How it works

```
local cron (every 5 minutes)
        |
        v
regular_checks/check_news.py
  - takes a non-blocking file lock
  - reloads the Excel roster
  - collects due RSS feeds (268 configured sources)
  - matches players, coaches, owners and team names
  - inserts articles + pending delivery rows in one SQLite transaction
  - sends due pending alerts through the Telegram Bot API
  - retries failures later with backoff
        |
        +--> saved_stories/sunrisers_news.db   (persistent ledger)
        +--> Telegram chat / channel
```

A feed failure only skips that feed until its backoff expires. A Telegram
failure leaves the article pending; it is not marked sent. The collector and
the sender are separate halves of the cycle, so one cannot silently lose the
other half.

---

## Fresh setup

Requires Python 3.9 or newer.

```bash
git clone https://github.com/Snohith/srhtrack.git
cd srhtrack
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill in the Telegram values (see below). `.env` is ignored by
git and must never be committed.

Verify the roster and database without sending anything:

```bash
python -m handy_tools.validate_roster
python -m regular_checks.check_news --status
```

---

## Telegram setup

1. Open **@BotFather** in Telegram, send `/newbot`, and copy the bot token into
   `TELEGRAM_BOT_TOKEN`.
2. Open your new bot and tap **START** once. Telegram does not let a bot message
   a person who has never started it.
3. Get your personal chat id by messaging **@userinfobot**, or call
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` after pressing START.
   Put that numeric id in `TELEGRAM_CHAT_ID`.
4. For a channel, add the bot as an administrator and use the channel id
   beginning with `-100`; forward a channel message to @userinfobot if needed.
5. Send one explicit test message:

```bash
python -m regular_checks.check_news --test-telegram
```

A successful test prints `Test message sent.` and does not touch the delivery
ledger.

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `TELEGRAM_ENABLED` | `true` | Master switch. Set `false` to collect without sending. |
| `TELEGRAM_BOT_TOKEN` | empty | Token from @BotFather. Empty means alerts stay pending. |
| `TELEGRAM_CHAT_ID` | empty | Your chat or channel id. Empty means alerts stay pending. |
| `SUNRISERS_DB_PATH` | `saved_stories/sunrisers_news.db` | SQLite ledger. Use an absolute path on a persistent disk. |
| `SUNRISERS_LOG_DIR` | `logs/` | Rotating logs. Must be writable. |
| `SUNRISERS_ROSTER_PATH` | `data/squadofsunrisers.xlsx` | Optional roster location; the workbook is never modified. |

The entry point loads `.env` once. Process environment variables take
precedence over `.env`.

---

## Daily commands

```bash
# One full collection + delivery cycle
python -m regular_checks.check_news

# Ledger and Telegram status, no collection
python -m regular_checks.check_news --status

# Reset terminally failed alerts, then run a cycle
python -m regular_checks.check_news --retry-failed

# Send one test message only
python -m regular_checks.check_news --test-telegram

# Read-only roster check
python -m handy_tools.validate_roster

# Run the test suite
python -m pytest -q
```

The same actions are available as `make collect`, `make status`,
`make test-telegram`, `make validate-roster`, and `make test`.

---

## Scheduler: local cron with persistent disk

This project deliberately uses **local cron**, not GitHub Actions. The SQLite
delivery ledger must live on storage that survives between runs; GitHub Actions
runners do not provide that.

Use an absolute path to the checkout and the virtualenv. Create the log folder
first, then edit your crontab with `crontab -e`:

```bash
mkdir -p /absolute/path/to/Tracker/logs
```

```cron
*/5 * * * * cd /absolute/path/to/Tracker && /absolute/path/to/Tracker/venv/bin/python -m regular_checks.check_news >> /absolute/path/to/Tracker/logs/cron.log 2>&1
```

Example with a checkout in your home folder:

```cron
*/5 * * * * cd "$HOME/Tracker" && "$HOME/Tracker/venv/bin/python" -m regular_checks.check_news >> "$HOME/Tracker/logs/cron.log" 2>&1
```

Notes:

- The interval is five minutes. Each run takes a non-blocking lock; if a slow
  run is still going, the next cron invocation exits without overlapping work.
- Keep `SUNRISERS_DB_PATH` on a persistent local disk. If you move the checkout,
  update the cron line and the database path.
- The cron machine must be awake and online. A sleeping laptop misses runs; the
  next wake-up resumes with the same ledger.
- Check cron output with `tail -f logs/cron.log`. Rotating logs are under
  `logs/rss.log`, `logs/database.log`, and `logs/errors.log`.
- There are no scheduled ingest workflows left in `.github/workflows/`. Only CI
  remains.

If you prefer a launchd agent on macOS, any agent that runs the same absolute
command every 300 seconds works; cron is the documented default.

---

## Delivery rules

- One article row and one delivery row are created together. An article insert
  never marks itself sent.
- Delivery states are `pending`, `sending`, `sent`, and `failed`.
- A send is claimed atomically, so two workers cannot claim the same article.
  A claim older than 15 minutes is recovered.
- Network errors and Telegram 429 responses keep the alert `pending` with
  exponential backoff. A 429 `retry_after` is honored.
- After five failed attempts the alert becomes `failed`. Use
  `--retry-failed` to reset terminal failures intentionally.
- At most 20 alerts are sent per cycle. Remaining pending alerts wait for the
  next cycle.
- A successful send is marked `sent` and is never sent again. If the process
  crashes after Telegram accepts a message but before SQLite records it, that
  rare window can produce one duplicate retry after 15 minutes. Telegram has no
  idempotency key, so exactly-once delivery cannot be guaranteed across a
  crash.
- The first collection writes a one-time activation timestamp. Stories
  published more than one hour before activation are skipped, so a fresh
  deployment does not replay the previous 24 hours as a burst of alerts.
- There is no heartbeat, no digest, and no empty-cycle message. Silence means
  there was nothing new.
- Old articles and their delivery rows are pruned after 30 days. Recent legacy
  alert titles are kept in `suppressed_titles` during migration so they do not
  fire again.

---

## Matching and roster

The workbook `data/squadofsunrisers.xlsx` is the sole source of truth. It is
read-only at runtime; no script rewrites it. A player can appear under two
franchises, and the matcher labels both. The roster validator checks the
workbook and the alias table without writing either.

The matcher accepts:

- full roster names;
- conservative surnames and first-name aliases (`Klaasen`, `Cummins`,
  `Abhishek`, `Crawley`, and similar);
- all four franchise names and the common `SRH` abbreviation;
- tracked ownership/management names (`Kavya Maran`, `Kalanithi Maran`,
  `Sun Group`, `Sun TV Network`);
- common cricket context words, so `SEC filing` and `Brookfield` do not become
  false positives.

Stories older than 24 hours are skipped. Articles with no safe public link are
skipped. The original headline and summary are stored and escaped before being
placed in Telegram HTML.

---

## Link safety

Only `http` and `https` article links are accepted. The validator rejects:

- `javascript:`, `data:`, `file:`, and other schemes;
- localhost, `.local`, `.internal`, and `.home.arpa` hosts;
- private, loopback, link-local, reserved, multicast and unspecified IP
  addresses;
- credentials in the URL;
- malformed hosts and overlong URLs.

The collector never downloads an article page or image. It only sends the
validated publisher link to Telegram, so there is no server-side article fetch
to use as an SSRF path.

---

## Repository layout

```
Tracker/
├── news_collectors/collect_news.py   # 268 feeds, collection + matching
├── our_teams/players.py              # Excel roster, aliases, franchise matching
├── saved_stories/
│   ├── story_storage.py              # articles + delivery ledger
│   └── tables.sql                    # schema
├── helpers/
│   ├── phone_alerts.py               # Telegram send + retry loop
│   ├── links.py                      # URL validation and article identity
│   ├── config.py                     # .env loading
│   ├── dates_and_times.py            # feed dates -> IST
│   └── log_books.py                  # rotating logs
├── regular_checks/check_news.py      # the one scheduled entry point
├── handy_tools/validate_roster.py    # read-only roster check
├── data/squadofsunrisers.xlsx        # sole roster source
├── tests/                            # isolated, network-mocked tests
├── .github/workflows/ci.yml          # tests only; no schedules
└── .env.example
```

### Removed from the previous version

- Streamlit app, theme, and `.streamlit/` config;
- command bot (`bot.py`, `phone_bot.py`), match scraper, and fixture helpers;
- dashboard-only tables (`news`, `players`, `matches`, `notifications`, and
  similar) and dashboard-only tests;
- backup scraper/fallback module and one-off nightly/refresh scripts;
- root duplicate roster workbook;
- scheduled GitHub Actions ingest and keep-awake workflows;
- stale OpenCode prompts under `.opencode/` that documented the removed
  dashboard and legacy tables (generic skills in `.agents/skills/` remain);
- Streamlit, pandas, and Pillow dependencies.

The old database is migrated in place: recent alert titles are preserved in
`suppressed_titles`, then legacy dashboard tables are dropped. Keep a backup of
the old database before the first run if you want to inspect its history later.

---

## Test results

The suite uses an isolated temporary database and mocks all RSS HTTP and
Telegram HTTP calls. It never sends a real message and never touches the
production ledger.

Last run:

```text
45 passed
```

Coverage includes fresh schema creation, legacy migration, roster read-only
validation, multi-franchise matching, false-positive guards, URL safety,
collector isolation, stale and malformed articles, concurrency-safe claims,
retry/backoff bounds, 429 handling, permanent failures, HTML escaping, entry
point ordering, lock behavior, and removed-module checks.

Run it yourself with:

```bash
python -m pytest -q
```

---

## Limitations

- RSS feeds are third-party and can be late, dead, rate-limited, or changed
  without notice. A dead feed is retried with backoff, not scraped by another
  service.
- The 24-hour age cutoff and five-minute polling window mean a story can be
  missed if the source never publishes a usable date or removes it quickly.
- Telegram is the only delivery channel. There is no dashboard, digest,
  heartbeat, command bot, or historical web view.
- The ledger is local SQLite. A machine that is off, asleep, or offline does not
  collect or deliver until it runs again.
- Exactly-once delivery is impossible across a crash after Telegram accepts a
  message but before SQLite records it. The retry window can duplicate that one
  message; the ledger prevents duplicates in normal operation.
- URL validation rejects literal private targets but does not perform DNS
  resolution checks. This is safe here because article pages are never fetched
  server-side.
- The matcher is deliberately conservative. A nickname not listed in
  `our_teams/players.py` will not match until it is added there; aliases are
  validated against the workbook.
- The roster workbook is maintained by hand. There is no sync or regeneration
  script anymore.

---

## Manual disable checklist

These actions are outside the repository and must be done by you:

1. **Old Streamlit app** — delete or pause the old
   `srhtrack.streamlit.app` deployment in the Streamlit dashboard. Deleting
   `app.py` stops new deploys, but the already-hosted app is a separate service.
2. **Old bot process** — stop any process still running `phone_bot.py`,
   `bot.py`, `app.py`, `make bot`, or a similar command. Those files are gone.
3. **Old GitHub schedules** — after pushing this commit, open the repository's
   **Actions** tab and confirm `Headless Ingest` and `Keep Streamlit Awake` are
   gone or disabled. The workflow files have been deleted.
4. **Old local schedulers** — check `crontab -l` and any launchd agent for
   references to `handy_tools/nightly_news_job.py`, `app.py`, or `phone_bot.py`
   and remove them.
5. **Leaked GitHub token** — the old local git remote contained a token. It has
   been removed from `.git/config`; revoke that token on GitHub and create a new
   one only if you need one.
6. **BotFather command menu** — the command bot is gone. If you previously set
   `/matches`, `/refresh`, or `/status` commands, clear them in BotFather
   (`/deletecommands`). The bot now only sends messages.
7. **Old Streamlit secrets** — delete the old Telegram keys from Streamlit
   Cloud's secrets page if that app still exists.

Rotate the Telegram bot token with BotFather if it was ever shared or committed.

---

## License

MIT. Maintained by [Chiluveru Snohith](https://github.com/Snohith).
