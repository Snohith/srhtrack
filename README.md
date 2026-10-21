# Sunrisers News Hub — all our teams in one friendly place

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Cloud-FF4B4B.svg?style=for-the-badge&logo=streamlit&logoColor=white)](https://srhtrack.streamlit.app/)
[![Live](https://img.shields.io/badge/Live-srhtrack.streamlit.app-orange.svg?style=for-the-badge)](https://srhtrack.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

Cricket news about our Sunrisers family, collected for fans — **Sunrisers Hyderabad (IPL)**, **Sunrisers Eastern Cape (SA20)**, **Sunrisers Leeds Men (The Hundred)**, and **Sunrisers Leeds Women (The Hundred)**.

Live: [https://srhtrack.streamlit.app/](https://srhtrack.streamlit.app/)

---

## 1. How it works (in plain words)

```
268 news websites → news_collectors/collect_news.py → our_teams/players.py (do we know them?)
    → saved stories file → app.py (the website you see)
```

1. **Check** — `try_to_download_one_website()` visits each website in `NEWS_WEBSITES` (waits a few seconds, tries twice). Stories older than 24 hours are recycled right away.
2. **Keep only ours** — `find_our_players_in_story()` keeps stories that mention one of our players (full name like "Abhishek Sharma", or a nickname like "Klaasen") or one of our 4 team names. American sports with similar words are ignored.
3. **Save** — `save_story()` files the story in our little database. The same story can be filed once *per player it mentions* (so one story about two players shows under both), but never twice for the same player. Stories older than 24 hours are tidied away when the app starts.
4. **Show** — `app.py` shows 3 friendly tabs: latest news, upcoming matches, and our squads. We check the news every 15 minutes; the page refreshes every 5 minutes.

---

## 2. Features

| Area | What you get |
|------|----------|
| Latest news | Big top story + story cards + 10-item timeline, newest first; tap to read the full story |
| Search | Search across headlines, summaries and player names (`search_stories`) |
| Team filter | Sidebar filter for all 4 teams; filters news and matches |
| Upcoming matches | Live match finder (`news_collectors/find_matches.py`): today → next 4 days, playing squads checked against our player list, live matches first (`our_teams/upcoming_matches.py` is the offline backup list) |
| Squad directory | Player cards grouped by team; filters for role, coach, captain, wicket-keeper, overseas; Owners section with business news and stock-exchange links |
| Tidying up | Stories kept for 24 hours (`throw_away_old_stories`); little notes tidied after 7 days |
| Diaries | `logs/news.log`, `logs/storage.log` plus problems diary via `helpers/log_books.py` |

---

## 3. Repository structure

```
sunrisers-news-hub/             # friendly names, Python >= 3.9
├── app.py                      # the website you see: 3 tabs, news checks, sidebar
├── data/squadofsunrisers.xlsx  # our player list: 88 rows, 86 players, 4 teams
├── squadofsunrisers.xlsx       # backup copy at the top level
├── news_collectors/
│   ├── collect_news.py         # NEWS_WEBSITES (268 sites), check + keep-ours pipeline
│   ├── find_matches.py         # live match list → playing squads vs our players
│   └── backup_news_finder.py   # find_match_highlights() helper for when a site is down
├── our_teams/
│   ├── players.py              # reads the Excel list, finds our names in stories
│   ├── upcoming_matches.py     # backup match list (the Matches tab uses live data)
│   └── website_look.py         # colours + story and player cards
├── saved_stories/
│   ├── story_storage.py        # save, find, search and tidy stories
│   └── tables.sql              # tables: news, players, notes, saved facts
├── regular_checks/
│   └── check_news.py           # check the news once, right now (no setup inside)
├── handy_tools/
│   └── refresh_player_list.py  # rebuild the Excel player list
├── helpers/
│   ├── log_books.py            # little diaries of what happened
│   └── dates_and_times.py      # read website dates → friendly Indian time
├── tests/
│   └── test_system.py          # checks: players, no copies, search, tables
├── .streamlit/config.toml      # port 8501, warm colours
├── requirements.txt
└── .env.example                # where to save stories, how often to check news
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
make sync-squads  # python handy_tools/refresh_player_list.py
make clean        # remove bytecode / caches
```

Dependencies: `streamlit`, `feedparser`, `beautifulsoup4`, `requests`, `pandas`, `openpyxl`, `pillow`, `pytest`.

---

## 5. Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `SUNRISERS_DB_PATH` | `saved_stories/sunrisers_news.db` | Where to keep saved stories (old `SRH_DB_PATH` still works; tests use a throwaway file) |
| `HOW_OFTEN_TO_CHECK_NEWS_SECS` | `900` | Seconds between news checks (old `AUTO_INGEST_INTERVAL_SECS` still works) |
| `STREAMLIT_SERVER_PORT` | `8501` | Local server port (see `.env.example`, `.streamlit/config.toml`) |
| `TELEGRAM_ENABLED` | `true` | Master switch for Telegram fresh-article alerts |
| `TELEGRAM_BOT_TOKEN` | _(empty)_ | Bot token from `@BotFather` (empty = alerts off) |
| `TELEGRAM_CHAT_ID` | _(empty)_ | Target chat/channel id (empty = alerts off) |
| `TELEGRAM_MODE` | `per_article` | `per_article` (overflow → digest) or `digest` (one summary/cycle) |
| `TELEGRAM_MAX_ALERTS_PER_CYCLE` | `10` | Cap for per-article mode, 1–50 |
| `TELEGRAM_HEARTBEAT` | `true` | `true` = DM on empty cycles too (~96/day when quiet); `false` = silent unless fresh news |

Copy `.env.example` to `.env` to customize a deployment. Page auto-reload is fixed at 5 min (`app.py`, JS `setTimeout 300000`); news query cache TTL is 60s.

### Telegram alerts (fresh article → phone)

Every news check (auto-refresh, tapping `Check for fresh stories`, `regular_checks/check_news.py`) can text your phone about new stories via `helpers/phone_alerts.py` — no extra installs needed. Texting is best-effort: if Telegram is down or not set up, news saving carries on and the hiccup is written in `logs/problems.log` (your secret code is never written down).

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

### Command bot (`/matches` live fixtures + `/refresh` on demand)

`phone_bot.py` long-polls your bot — no server, no dashboard. From chat:

- `/matches` — Crex fixtures with our players, LIVE first: team names, IST date + start time, our players grouped by franchise, venue + score link. Empty window? An honest "nothing live" card instead of silence.
- `/refresh` — sweep all 268 feeds now (summary + DMs follow)
- `/status` — rows stored, players tracked, alert mode

Only your `TELEGRAM_CHAT_ID` can issue commands (strangers silently ignored); one sweep at a time; no buttons anywhere. Run with `python phone_bot.py` (or `make bot`) anywhere Python runs. Register the menu in BotFather once via `/setcommands`: `matches`, `refresh`, `status`, `start`, `help`.

### Nightly news check (texts you with zero tabs open)

The website only checks news while someone has it open. `.github/workflows/headless-ingest.yml` removes that limit: every 15 min a helper computer runs `handy_tools/nightly_news_job.py` (make tables + `do_one_news_check()` + phone texts). The memory of what we already texted lives in the saved `sunrisers_news.db`, so stories never text twice; overlapping runs cancel each other to keep it safe.

Setup: repo **Settings → Secrets and variables → Actions → New repository secret** — add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (values from your local `.env`). Then trigger one manual run (**Actions → Headless Ingest → Run workflow**) and watch for the DMs. Note: the very first run has no cache, so it delivers a bounded one-time catch-up (cap + digest).

### Keeping the app awake on Community Cloud

The free tier sleeps apps after ~12h with no visit or commit. `.github/workflows/keep-awake.yml` pushes a scheduled empty commit every 10h to reset that timer (the officially documented method — plain URL pingers no longer reliably count). After merging, wake the app once manually via `Yes, get this app back up!`, then the schedule holds it. Use `Actions → Keep Streamlit Awake → Run workflow` for an on-demand ping.

---

## 6. Source coverage (268 configured feeds & resilient scraper fallback)

Listed in `news_collectors/collect_news.py` (`NEWS_WEBSITES`; older names like `CRICKET_SOURCES` still work).

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
| Deep-scan round 1 — community & direct feeds | 8 | Reddit r/SunrisersHyderabad, r/ipl, r/CricketAus; The Age Sport; ESPNcricinfo All Stories (feed 0); Firstpost; Zee direct; Telegraph UK |
| Deep-scan round 1 — league market mirrors | 10 | Google News: IPL retention/mini-auction, trade window, Impact Player rule, Livingstone, Harshal Patel, T Natarajan, SRH factory kids, Malinga, SRH release list, CA workload |
| Deep-scan round 2 — insider bylines | 13 | Google News: Brettig, Lalor, McGlashan, Gollapudi, Monga, Kishore, Sundaresan, Malhotra, Shriniwas Rao, Lokapally, Karhadkar, Muthu, Purohit |
| Deep-scan round 2 — full-squad player feeds | 16 | Google News: Travis Head, Nitish Kumar Reddy, Unadkat, Kamindu Mendis, Carse, Jack Edwards, Smaran, Aniket Verma, Shivang Kumar, Harsh Dubey, Baartman, Hermann, Adil Rashid, Yuvraj, Gambhir, Kalanithi Maran |
| Deep-scan round 2 — league mechanics & market | 3 | Google News: BCCI governing council, IPL auction Goa logistics, Hardik Pandya trade |
| Deep-scan round 2 — wires & agencies | 6 | Google News: ANI, IANS, PTI, UNI, Rediff; The Bridge |
| Deep-scan round 2 — Telugu & regional | 4 | Google News (te): Eenadu, TV9 Telugu, Telugu Oneindia, Andhra Jyothy |
| Deep-scan round 2 — overseas plus | 2 | Google News: Sport24 SA cricket, Yorkshire Evening Post cricket |
| Deep-scan round 2 — YouTube channels | 13 | SRH, IPL, Cricbuzz, Sky Sports, The Hundred, Star Sports, Betway SA20, Fox Cricket, BBC Sport, cricket.com.au, Wisden, ICC, Ashwin Ravi (identity-verified channel IDs) |

### Resilient scraper & dead source recovery engine

- **Dead feeds removed / upgraded:** Removed dead domain `CricketCountry` (NXDOMAIN) and replaced with `SA Cricket Mag`. Replaced broken `Deccan Chronicle`, paywalled `Telegraph UK`, and blocked `Zee News` with high-yield Google News site-search mirrors. Replaced `NDTV` with active FeedBurner XML feed.
- **Deep-scan additions (Oct 2026):** +75 lanes (bylines, full-squad player feeds, wires, Telugu, YouTube channels, league market). A few are browser-only for scripted pollers (Reddit 429; Firstpost / Zee direct 403; Telegraph UK 402) — they stay listed, fail gracefully, and the resilient fallback recovers what it can.
- **Resilient fallback scraper:** `news_collectors/collect_news.py` integrates `news_collectors/backup_news_finder.py`. If any feed endpoint experiences HTTP errors, SSL failures, or returns 0 items, the collector automatically invokes `scrape_google_news_topic()` to recover articles seamlessly with 0% data loss.
- **4-Franchise Scaling:** Balanced coverage across all 4 Sunrisers teams (SRH, SEC, Leeds Men, Leeds Women) with dedicated intelligence channels and complete single-name alias patterns in `our_teams/players.py`.

---

## 7. Verification

```bash
pytest tests/          # or: make test
```

`tests/test_system.py` checks: player list vs Excel, skipping copies, one story filed under several players, search, counts, friendly defaults, finding players and teams (nicknames included), diary files, website list, no-copy rules in tables, and that the regular checker never rebuilds the whole box (`check_news.py` must not call `set_up_story_box()`).

---

## 8. License

MIT — see [`LICENSE`](LICENSE). Maintained by [Chiluveru Snohith](https://github.com/Snohith).
