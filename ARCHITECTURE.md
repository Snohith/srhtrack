# Tracker — How Our Project Works

**One-sentence version:** Tracker reads cricket news from 156 RSS feeds, keeps only stories about our Sunrisers players, stores them with standard defaults, and shows them in a web dashboard.

Live app: `https://srhtrack.streamlit.app/` — run locally with `streamlit run app.py`.

## The 4 teams we follow

| Team | League |
|---|---|
| Sunrisers Hyderabad | IPL (India) |
| Sunrisers Eastern Cape | SA20 (South Africa) |
| Sunrisers Leeds Men | The Hundred (England) |
| Sunrisers Leeds Women | The Hundred Women (England) |

The player list lives in `data/squadofsunrisers.xlsx` (~90 rows). Everything the app knows about "our players" comes from this file.

## The journey of one news story

```
156 RSS feeds
  → scrapers/rss_collector.py  (download each feed, retry if it fails)
  → config/roster.py           (is a Sunrisers player or team mentioned? if no, drop it)
  → database/srh_tracker.db   (SQLite file — saved for 24 hours)
  → app.py                    (Streamlit dashboard you see in the browser)
```

**Step by step:**

1. **Collect** — Every 15 minutes the app downloads all 156 feeds (ESPNcricinfo, Cricbuzz, BBC, Google News searches, regional papers, etc.). If a feed is dead, a Google News fallback tries to recover its stories.
2. **Filter** — Stories older than 24 hours are thrown away. Then each headline is checked: does it mention one of our players (full name like "Abhishek Sharma", or a nickname like "Klaasen", "Stubbs") or one of our 4 team names? Non-cricket lookalikes (NFL, MLB…) are rejected. No match = dropped.
3. **Store** — Matching stories are saved in SQLite with standard defaults. The same story can be saved once *per player it mentions* (so one article about Head *and* Klaasen appears under both), but never twice for the same player. Anything older than 24 hours is deleted automatically.
4. **Show** — The dashboard displays the newest stories first, with search, team filters, and a live timeline.

## The 4 dashboard tabs (`app.py`)

1. **Live Pulse** — hero story + news cards + 10-item timeline, with search.
2. **Fixture Breakdown** — match schedule (`config/schedule.py`) with LIVE / UPCOMING / COMPLETED status.
3. **On This Day** — historical milestones and birthdays (a fixed list inside `app.py`).
4. **Squad Directory** — every player card, filterable by role, captain, coach, overseas, etc.

The page refreshes itself every 5 minutes; news data is cached for 60 seconds.

## Key files

| File | Job |
|---|---|
| `app.py` | The whole dashboard (UI + scheduling). |
| `scrapers/rss_collector.py` | The 156-feed list + download/filter pipeline. |
| `scrapers/web_scraper.py` | Backup fetcher when a feed fails. |
| `config/roster.py` | Reads the Excel roster; matches names in headlines. |
| `config/schedule.py` | Fixture list. |
| `config/theme.py` | Page styling + card layouts. |
| `database/db_manager.py` | All database reads/writes, dedupe, cleanup. |
| `database/schema.sql` | Table definitions (news, players, notifications, metadata). |
| `scheduler/worker.py` | Runs one collection cycle on demand. |
| `scripts/update_squads.py` | Rebuilds the Excel roster (`make sync-squads`). |
| `tests/test_system.py` | 20 automated checks (`make test`). |

## Good to know

- **Database resets itself:** news older than a day is purged on every startup; player list is re-seeded from Excel.
- **Two Excel copies exist:** `data/squadofsunrisers.xlsx` (the real one) and a root-level backup. The sync script writes both.
- **Settings:** copy `.env.example` to `.env` to change the database location or ingest interval.
- **Tests never touch real data:** they use a temporary database.
- **Tech:** Python + Streamlit + SQLite + pandas. Install with `pip install -r requirements.txt`.

## Technical companion

This file is the plain-language overview. For the engineering spec (matching rules, schema details), see `docs/ARCHITECTURE.md`. For agent working rules, see `AGENTS.md`.
