# 🧡 @SRHXtra — Premium Obsidian Command Center

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Cloud-FF4B4B.svg?style=for-the-badge&logo=streamlit&logoColor=white)](https://srhtrack.streamlit.app/)
[![Live](https://img.shields.io/badge/Live-srhtrack.streamlit.app-orange.svg?style=for-the-badge)](https://srhtrack.streamlit.app/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

> **@SRHXtra** is a real-time cricket intelligence platform tracking the live Excel roster across all 4 Sunrisers global franchises — **Sunrisers Hyderabad (IPL)**, **Sunrisers Eastern Cape (SA20)**, **Sunrisers Leeds Men (The Hundred)**, and **Sunrisers Leeds Women (The Hundred)**.

🔗 **Live:** [https://srhtrack.streamlit.app/](https://srhtrack.streamlit.app/)

---

## 🌟 Features

| Feature | Details |
|---------|---------|
| 📡 **48-Source RSS Engine** | Polls 48 fully verified, live-tested global & hyper-local cricket outlets every 15 minutes — zero dead feeds |
| 👥 **Dynamic Roster Tracking** | Loaded from `squadofsunrisers.xlsx` with regex word-boundary matching |
| 📋 **Match Day Fixture Breakdown** | Live fixture cards with player rosters, countdown timers (IST) |
| 📰 **Live Pulse News Feed** | Real-time news cards with exact source headlines, click-to-open links |
| 🗓️ **On This Day** | Curated historical Sunrisers moments auto-filtered to today's date |
| 🔍 **Live Search** | Search across all rostered players, franchises and keywords instantly |
| ⚡ **Auto-Ingest** | Background RSS ingestion every 15 min with JS page reload every 5 min |
| 🧹 **Auto-Sanitization** | Startup purge removes expired (>24h) and misattributed articles |

---

## 📁 Repository Structure

```
srhtrack/
├── app.py                      # Main Streamlit UI (Premium Obsidian Command Center)
├── squadofsunrisers.xlsx       # Master Excel Squad Roster (4 Franchises)
├── scrapers/
│   ├── rss_collector.py        # 48-source verified RSS engine (dead feeds removed 2026-07-31)
│   └── web_scraper.py          # Utility web scraper (supplementary)
├── config/
│   ├── roster.py               # Master Roster Engine & player/franchise matcher
│   └── schedule.py             # Fixture schedule data (July–August 2026)
├── database/
│   ├── db_manager.py           # SQLite CRUD, target-aware deduplication, analytics, metadata
│   └── schema.sql              # Database schema
├── agents/
│   └── ranker.py               # Importance scorer & news categoriser
├── scheduler/
│   └── worker.py               # Background collector worker (manual trigger)
├── utils/
│   ├── logger.py               # Rotating file loggers
│   └── time_utils.py           # IST date parsing & formatting
├── tests/
│   └── test_system.py          # Full pytest verification suite
├── requirements.txt
└── .streamlit/config.toml      # Streamlit Cloud configuration
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/Snohith/srhtrack.git
cd srhtrack
pip install -r requirements.txt
streamlit run app.py
```

Dashboard available at `http://localhost:8501`.

---

## 📡 Source Coverage (48 verified feeds)

| Region | Sources |
|--------|---------|
| Global Officials | ESPNcricinfo (5 country feeds), Cricbuzz, IPL, SA20, ICC, BCCI, Cricket Australia |
| 🇮🇳 India / IPL / Trade | Sportskeeda, InsideSport, KhelNow, ABP Live, **Sportstar (The Hindu)**, NDTV, Times of India, Hindustan Times, Indian Express, The Hindu, Deccan Chronicle, RevSportz, Sakshi Telugu, + 10 more |
| 🇬🇧 UK / The Hundred | BBC Sport, Sky Sports, Wisden, ECB, Telegraph, Guardian, Yorkshire CCC, Yorkshire Post, + 5 more |
| 🇿🇦 South Africa / SA20 | SuperSport, Cricket SA, IOL, News24, TimesLIVE |
| 🇦🇺 Australia | Fox Sports, Nine WWOS, ABC, Sydney Morning Herald |
| 🟠 Hyderabad Local | Telangana Today, Siasat Daily, Munsif Daily, Namasthe Telangana, V6 Velugu, NTV Telugu, JioCinema/Sports18 |

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

---
*Maintained by [Chiluveru Snohith](https://github.com/Snohith)*
