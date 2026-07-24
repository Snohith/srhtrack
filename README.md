# 🦅 @SRHXtra Zero-API Command Center (V2.0)

> **Private Repository | Operational Media Desk for the Global Sunrisers Cricket Empire**

`@SRHXtra` is an enterprise-grade, local-first sports data operations platform that tracks **74 players** across all 4 Sunrisers global cricket franchises (**Sunrisers Hyderabad IPL**, **Sunrisers Eastern Cape SA20**, **Sunrisers Leeds Men**, **Sunrisers Leeds Women**).

---

## 🌟 Key Features

* **📊 Dynamic Excel Master Roster:** Automatically loads and tracks 74 players from `squadofsunrisers.xlsx` with regex word boundary matching (0 false positives).
* **🗓️ Section 1: 30-Day IST Schedule:** Complete chronological fixture calendar sorted by Date & Start Time strictly in **Indian Standard Time (IST)**.
* **📰 Section 2: Player Reconnaissance:** Verified match stats, podcast appearances, injury updates, and viral moments sorted latest-first by IST timestamp.
* **📡 16-Source Data Engine:** Polls 16 top-tier cricket outlets (ESPNcricinfo, Cricbuzz, BBC Sport, Sky Sports, Wisden, etc.) with exponential backoff retries.
* **🎨 Pillow Graphic Studio:** Generates 16:9 Twitter stat cards locally with smart auto-detected templates (*Century, Fifty, 5-Wickets, Bowling*).
* **💎 Glassmorphism UI:** Built with Streamlit, Google Fonts (*Outfit* & *Inter*), and mobile cross-device responsiveness (`http://localhost:8501`).

---

## 📁 Repository Directory Structure

```
Tracker/
├── app.py                      # Streamlit UI (2 Streamlined Sections)
├── squadofsunrisers.xlsx       # Master Roster Spreadsheet (74 Players)
├── config/
│   └── roster.py               # Dynamic Excel Roster Loader & Regex Engine
├── database/
│   ├── db_manager.py           # SQLite Persistence & Deduplication
│   └── schema.sql              # Multi-Table Database Schema
├── scrapers/
│   ├── rss_collector.py        # 16-Source RSS Ingestion Engine
│   └── web_scraper.py          # Scorecard Snippet Extractor
├── agents/
│   ├── ranker.py               # Importance Score (1.0 to 10.0)
│   └── tweet_generator.py      # Ready-to-Post X Update Generator
├── graphics/
│   └── generator.py            # PIL 16:9 Stat Card Synthesis Engine
├── scheduler/
│   └── worker.py               # Background Ingestion Collector
├── utils/
│   ├── logger.py               # Centralized Structured Logging
│   └── time_utils.py           # IST Timezone Conversion Helpers
├── tests/
│   └── test_system.py          # Comprehensive Test Suite
├── requirements.txt            # Python Dependencies
├── .gitignore                  # Git Exclusion Rules
└── README.md                   # Documentation
```

---

## 🚀 Local Installation & Running Guide

### 1. Clone & Setup Environment
```bash
git clone <YOUR_PRIVATE_GITHUB_REPO_URL>
cd Tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
PYTHONPATH=. python3 tests/test_system.py
```

### 3. Launch Dashboard
```bash
PYTHONPATH=. streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your browser.

---

## ☁️ Deploying to Private Cloud (Streamlit Community Cloud)

1. Push this repository to a **Private GitHub Repository**.
2. Go to **[share.streamlit.io](https://share.streamlit.io)** and log in with GitHub.
3. Select your repository, pick main branch, set main file to `app.py`, and click **Deploy**.
4. Access your live 24/7 private dashboard from any mobile phone or device!

---

© 2026 @SRHXtra. All rights reserved.
