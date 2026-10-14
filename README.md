# SRHXtra — Sunrisers Cricket Intelligence Platform

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Cloud-FF4B4B.svg?style=for-the-badge&logo=streamlit&logoColor=white)](https://srhtrack.streamlit.app/)
[![Live](https://img.shields.io/badge/Live-srhtrack.streamlit.app-orange.svg?style=for-the-badge)](https://srhtrack.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

Real-time cricket news intelligence over the active Excel roster for all 4 Sunrisers franchises — **Sunrisers Hyderabad (IPL)**, **Sunrisers Eastern Cape (SA20)**, **Sunrisers Leeds Men (The Hundred)**, and **Sunrisers Leeds Women (The Hundred)**.

Live: [https://srhtrack.streamlit.app/](https://srhtrack.streamlit.app/)

---

## 1. How it works

```
193 RSS feeds → scrapers/rss_collector.py → config/roster.py matcher
    → SQLite → app.py (Streamlit)
```

1. **Poll** — `fetch_feed_with_retry()` fetches each feed in `CRICKET_SOURCES` (3s timeout, 2 attempts). Articles older than 24h are discarded at ingest.
2. **Match** — `match_player_or_franchise_in_text()` keeps only articles mentioning a rostered player (word-boundary match + single-name aliases) or one of the 4 franchise names. US-sports false positives (`nfl`, `mlb`, etc.) are rejected.
3. **Store** — `insert_news()` writes to SQLite with target-aware dedupe (same URL/title can exist once *per player/franchise*, not once globally). `purge_expired_24h_news()` deletes rows older than 24h on startup.
4. **Serve** — `app.py` renders 3 tabs: Live Pulse news, live Crex matchday fixtures, squad directory. Background ingest runs every 15 min; the page reloads every 5 min; query cache TTL is 60s.

---

## 2. Features

| Area | Behavior |
|------|----------|
| Live Pulse news feed | Hero card + list cards + 10-item timeline, newest first by `pub_timestamp`; click-through to source URL |
| Live search | Full-text search over title, summary, player name (`search_news`) |
| Franchise filter | Sidebar filter across all 4 squads; applies to news and fixtures |
| Fixture breakdown | Live Crex engine (`scrapers/matchday_scraper.py`): today→+4 days, schedule → Playing XI vs roster, LIVE first, finished removed (`config/schedule.py` is offline fallback) |
| Squad directory | Roster cards grouped by franchise; filters for role, coach, captain, wicket-keeper, overseas; Ownership & Business section with live business news and exchange/registry links |
| Retention | 24h rolling window for news (`purge_expired_24h_news`); notifications pruned after 7 days |
| Logging | `logs/rss.log`, `logs/database.log` plus error log via `utils/logger.py` |

---

## 3. Repository structure

```
srhtrack/                         # v14.1.0, Python >= 3.9
├── app.py                        # Streamlit UI: 3 tabs, ingest scheduling, sidebar controls
├── data/squadofsunrisers.xlsx    # Master roster: 88 rows, 86 distinct players, 4 squads
├── squadofsunrisers.xlsx         # Legacy fallback copy at repo root
├── scrapers/
│   ├── rss_collector.py          # CRICKET_SOURCES (193 feeds), fetch + filter pipeline
│   ├── matchday_scraper.py       # Live Crex schedule → Playing XI vs roster fixtures
│   └── web_scraper.py            # scrape_match_highlights() helper (no feeds)
├── config/
│   ├── roster.py                 # Excel loader, word-boundary matcher, aliases
│   ├── schedule.py               # Offline fixture fallback (live tab uses Crex)
│   └── theme.py                  # CSS tokens + card render helpers
├── agents/
│   └── __init__.py               # Agents package (per-article scoring removed)
├── database/
│   ├── db_manager.py             # SQLite CRUD, dedupe, search, analytics, metadata
│   └── schema.sql                # Tables: news, players, notifications, metadata
├── scheduler/
│   └── worker.py                 # Manual one-shot collector cycle (no init_db)
├── scripts/
│   └── update_squads.py          # Excel roster builder / migration
├── utils/
│   ├── logger.py                 # Rotating file loggers
│   └── time_utils.py             # RSS date → IST parsing and formatting
├── tests/
│   └── test_system.py            # Pytest suite (roster, dedupe, search, defaults, schema)
├── .streamlit/config.toml        # Port 8501, light theme (#F26522 / #F8FAFC)
├── requirements.txt
└── .env.example                  # SRH_DB_PATH, Streamlit + ingest-interval overrides
```

---

## 4. Quick start

```bash
git clone https://github.com/Snohith/srhtrack.git
cd srhtrack
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`.

Makefile shortcuts:

```bash
make install      # pip install -r requirements.txt
make run          # streamlit run app.py
make test         # pytest tests/
make sync-squads  # python scripts/update_squads.py
make clean        # remove bytecode / caches
```

Dependencies: `streamlit`, `feedparser`, `beautifulsoup4`, `requests`, `pandas`, `openpyxl`, `pillow`, `pytest`.

---

## 5. Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SRH_DB_PATH` | `database/srh_tracker.db` | Override SQLite file location (tests use a temp file) |
| `AUTO_INGEST_INTERVAL_SECS` | `900` | Seconds between background ingest cycles |
| `STREAMLIT_SERVER_PORT` | `8501` | Local server port (see `.env.example`, `.streamlit/config.toml`) |
| `TELEGRAM_ENABLED` | `true` | Master switch for Telegram fresh-article alerts |
| `TELEGRAM_BOT_TOKEN` | _(empty)_ | Bot token from `@BotFather` (empty = alerts off) |
| `TELEGRAM_CHAT_ID` | _(empty)_ | Target chat/channel id (empty = alerts off) |
| `TELEGRAM_MODE` | `per_article` | `per_article` (overflow → digest) or `digest` (one summary/cycle) |
| `TELEGRAM_MAX_ALERTS_PER_CYCLE` | `10` | Cap for per-article mode, 1–50 |
| `TELEGRAM_HEARTBEAT` | `true` | `true` = DM on empty cycles too (~96/day when quiet); `false` = silent unless fresh news |

Copy `.env.example` to `.env` to customize a deployment. Page auto-reload is fixed at 5 min (`app.py`, JS `setTimeout 300000`); news query cache TTL is 60s.

### Telegram alerts (fresh article → phone)

Every ingest cycle (auto-refresh, manual `Refresh feeds`, `scheduler/worker.py`) sends Telegram messages for newly stored articles via `utils/telegram.py` — no extra dependency (`requests` only). Alerting is best-effort: if Telegram is down or unconfigured, ingest continues and the failure lands in `logs/errors.log` (token never logged).

1. Message `@BotFather` → `/newbot` → copy the token into `TELEGRAM_BOT_TOKEN`.
2. Message `@userinfobot` → copy the id into `TELEGRAM_CHAT_ID` (channel: add the bot as admin, use the `-100…` id).
3. `cp .env.example .env`, fill the two values, restart the app. Sidebar shows `🔔 Telegram alerts ON` when live.

On Streamlit Community Cloud `.env` never deploys (gitignored) — put the same keys under the app's **Settings → Secrets** instead (TOML; quote the values):
```toml
TELEGRAM_ENABLED = "true"
TELEGRAM_BOT_TOKEN = "paste-from-BotFather"
TELEGRAM_CHAT_ID = "your-chat-id"
TELEGRAM_MODE = "per_article"
```
The bot can only message you **after you tap START on it once** (Telegram rule — bots can't message first). No channel needed; alerts arrive as DMs from the bot itself.

### Headless ingest (alerts with zero tabs open)

The app only runs while a browser tab is open. `.github/workflows/headless-ingest.yml` removes that limitation: every 15 min a GitHub runner executes `scripts/ingest_job.py` (schema init + `run_collector_cycle()` + Telegram sends). Dedupe memory persists via the cached `srh_tracker.db`, so stories never resend; overlapping runs cancel each other to protect it.

Setup: repo **Settings → Secrets and variables → Actions → New repository secret** — add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (values from your local `.env`). Then trigger one manual run (**Actions → Headless Ingest → Run workflow**) and watch for the DMs. Note: the very first run has no cache, so it delivers a bounded one-time catch-up (cap + digest).

### Keeping the app awake on Community Cloud

The free tier sleeps apps after ~12h with no visit or commit. `.github/workflows/keep-awake.yml` pushes a scheduled empty commit every 10h to reset that timer (the officially documented method — plain URL pingers no longer reliably count). After merging, wake the app once manually via `Yes, get this app back up!`, then the schedule holds it. Use `Actions → Keep Streamlit Awake → Run workflow` for an on-demand ping.

---

## 6. Source coverage (193 configured feeds & resilient scraper fallback)

Defined in `scrapers/rss_collector.py:17-233` (`CRICKET_SOURCES`; `TOP_50_CRICKET_SOURCES` and `RSS_FEEDS` are aliases).

| Group | Count | Outlets |
|-------|------:|---------|
| Global / specialist | 11 | ESPNcricinfo England, Australia, South Africa, India, Sri Lanka; Cricbuzz; CricTracker; Sportskeeda; OneCricket; Cricket Addictor; Cricket Times |
| SRH / India regional | 24 | Google News SRH + Telangana Today, Siasat, Munsif, Namasthe Telangana, V6 Velugu, NTV Telugu, Sakshi, JioCinema/Sports18, Sportstar, Hindu, NDTV, TOI, HT, Indian Express, News18, Deccan Chronicle + Business Standard, LiveMint, Zee News, RevSportz, InsideSport, KhelNow, ABP Live mirrors |
| SEC / SA20 | 3 | Google News SEC, Google News SA20 League, SA Cricket Mag |
| Leeds Men / The Hundred | 10 | Google News Leeds Men + The Hundred, BBC, Sky, Yorkshire CCC, Guardian, Independent, Daily Mail, Evening Standard, TalkSPORT |
| Leeds Women / Women's | 3 | Google News Leeds Women + Women's Cricket World, Female Cricket |
| Premium editorial | 1 | Wisden Cricket |
| Official league/board/franchise channels | 7 | Google News mirrors: IPL, SRH, BCCI, SA20, SEC, The Hundred, ECB official sites |
| Women's game depth | 1 | Google News England Women's Cricket |
| Ownership / business / leadership | 4 | Economic Times Cricket + Sun TV Network, Kavya Maran, Leeds Business mirrors |
| Australia & international | 2 | ABC News Australia Sport, SMH Sport |
| ESPNcricinfo feed expansion | 18 | ESPNcricinfo Feeds 4, 5, 7, 9, 11, 15, 17, 19, 20, 25, 27–30, 33, 35, 37, 40 |
| League & domestic topics | 15 | Google News mirrors: SA20 Betway, CSA 4-Day, CSA T20, The Hundred Exact, County Championship, Vitality Blast, BBL, WBBL, CPL, PSL, ILT20, MLC, Duleep Trophy, IPL-wide, WPL |
| Country topics | 10 | Google News mirrors: New Zealand, Pakistan, Bangladesh, Zimbabwe, Ireland, Scotland, Netherlands, Nepal, UAE, Afghanistan |
| Franchise exact-phrase mirrors | 4 | Google News: SRH Exact, SEC Exact, Leeds Men Superchargers, Leeds Women Superchargers |
| Site-restricted mirrors | 4 | Google News: ICC, Yorkshire CCC, ESPNcricinfo, Cricbuzz site searches |
| Player & coach topics | 12 | Google News: Abhishek, Cummins, Klaasen, Markram, Jansen, Brook, Stubbs, Ishan, Deepti, Litchfield, Coaches, Leeds Women Stars (filtered by roster matcher downstream) |
| Ownership / business expansion | 6 | Google News: Sun TV Exact, Kavya Maran Exact, Sun Group, Sunrisers Valuation, IPL Valuation, Yorkshire Investment |
| Women's game expansion | 4 | Google News: Global, England Women, India Women, WPL Auction |
| Aggregators & community | 1 | Reddit r/Cricket (real post dates; Bing mirrors removed — they re-surface evergreen pages with fresh timestamps) |
| UK & SA direct feeds | 5 | BBC The Hundred, Sky 12040, Yorkshire Post, The Citizen SA, CricToday |
| Business direct feeds | 4 | LiveMint Markets, Hindu BusinessLine, ET Top Stories, Business Today |
| Telugu regional depth | 4 | Telangana Today General, Vaartha, Hans India, GreatAndhra |
| Overseas depth (non-India) | 14 | SA: Daily Maverick, IOL, News24 + SuperSport mirrors; AUS: Cricket Australia + Fox mirrors; NZ: Stuff + Herald mirror; SL: ThePapare, AdaDerana; PK: Dawn Sport; BD: Daily Star mirror; SCO: Scotsman mirror; UK: Cricketer mirror |
| National teams & overseas press | 12 | SABC Sport, Tribune PK Sport; national-team mirrors: England, Australia, Proteas, Black Caps, Pakistan, Bangladesh, Sri Lanka, Scotland; Dhaka Tribune + Daily Mirror LK mirrors |
| SA depth + women's weight | 9 | HeraldLive; Proteas Women, SA domestic, ICC Women, England domestic, WBBL/Ashes, India Women stars, Hundred Women clubs, WPL stars mirrors |
| Ownership filings & leadership | 5 | Google News: BSE filings, Moneycontrol, Kavya Maran Statements, Sun Group filings, Leeds Companies House |

### Resilient scraper & dead source recovery engine

- **Dead feeds removed / upgraded:** Removed dead domain `CricketCountry` (NXDOMAIN) and replaced with `SA Cricket Mag`. Replaced broken `Deccan Chronicle`, paywalled `Telegraph UK`, and blocked `Zee News` with high-yield Google News site-search mirrors. Replaced `NDTV` with active FeedBurner XML feed.
- **Resilient fallback scraper:** `scrapers/rss_collector.py` integrates `scrapers/web_scraper.py`. If any feed endpoint experiences HTTP errors, SSL failures, or returns 0 items, the collector automatically invokes `scrape_google_news_topic()` to recover articles seamlessly with 0% data loss.
- **4-Franchise Scaling:** Balanced coverage across all 4 Sunrisers teams (SRH, SEC, Leeds Men, Leeds Women) with dedicated intelligence channels and complete single-name alias patterns in `config/roster.py`.

---

## 7. Verification

```bash
pytest tests/          # or: make test
```

`tests/test_system.py` covers: roster seeding vs Excel, URL/title dedupe, multi-target inserts, search, analytics summary, insert defaults (5.0 / 'General News'), player + franchise matching (incl. case-insensitivity and single-name aliases), log files, source-count/dedupe invariants, schema dedupe indexes, category-default alignment, and scheduler isolation (`worker.py` must not call `init_db()`).

---

## 8. License

MIT — see [`LICENSE`](LICENSE). Maintained by [Chiluveru Snohith](https://github.com/Snohith).
