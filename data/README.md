# 📊 Our player lists

This folder holds our player lists in plain Excel — the heart of the news hub.

---

## 📁 Datasets Overview

### 1. `squadofsunrisers.xlsx`
Our 4 Sunrisers family teams:

| Team | League | Players | Captain & coach | Home ground |
| :--- | :--- | :---: | :--- | :--- |
| **Sunrisers Hyderabad** | Indian Premier League (IPL) | 30 | Pat Cummins (C), Daniel Vettori (Coach) | Rajiv Gandhi Int'l Stadium, Hyderabad |
| **Sunrisers Eastern Cape** | SA20 League | 18 | Tristan Stubbs (C), Adrian Birrell (Coach) | St George's Park, Gqeberha |
| **Sunrisers Leeds Men** | The Hundred Men | 20 | Zak Crawley (C), Dan Vettori (Coach) | Headingley Cricket Ground, Leeds |
| **Sunrisers Leeds Women** | The Hundred Women | 20 | Dani Gibson (C) | Headingley Cricket Ground, Leeds |

#### Schema Definition

| Column | Type | Description |
| :--- | :--- | :--- |
| `Team` | `words` | Team name (like `Sunrisers Hyderabad IPL 2026`) |
| `Player` | `words` | Player's full name (we match whole names only) |
| `Role` | `words` | What they do (`Batter`, `Bowler`, `All-rounder`, `Head Coach`, `Wicket-keeper`) |
| `Country` | `words` | Which country they play for |
| `Notes` | `words` | Extra notes (`Captain`, `Overseas`, and so on) |

---

## 🔄 Updating Data

To refresh the player list, run:

```bash
python handy_tools/refresh_player_list.py
```

This updates both `data/squadofsunrisers.xlsx` and the root fallback mirror.
