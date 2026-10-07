# 📊 SRHXtra Master Datasets

This directory houses the structured reference data for the **SRHXtra** intelligence engine.

---

## 📁 Datasets Overview

### 1. `squadofsunrisers.xlsx`
The master squad roster registry covering all 4 franchises across the Sunrisers global franchise network:

| Franchise | League | Squad Count | Key Staff / Leadership | Home Venue |
| :--- | :--- | :---: | :--- | :--- |
| **Sunrisers Hyderabad** | Indian Premier League (IPL) | 30 | Pat Cummins (C), Daniel Vettori (Coach) | Rajiv Gandhi Int'l Stadium, Hyderabad |
| **Sunrisers Eastern Cape** | SA20 League | 18 | Tristan Stubbs (C), Adrian Birrell (Coach) | St George's Park, Gqeberha |
| **Sunrisers Leeds Men** | The Hundred Men | 20 | Zak Crawley (C), Dan Vettori (Coach) | Headingley Cricket Ground, Leeds |
| **Sunrisers Leeds Women** | The Hundred Women | 20 | Dani Gibson (C) | Headingley Cricket Ground, Leeds |

#### Schema Definition

| Column | Type | Description |
| :--- | :--- | :--- |
| `Team` | `string` | Full franchise identifier (e.g. `Sunrisers Hyderabad IPL 2026`) |
| `Player` | `string` | Official member name used for exact-boundary regex matching |
| `Role` | `string` | Primary functional role (`Batter`, `Bowler`, `All-rounder`, `Head Coach`, `Wicket-keeper`) |
| `Country` | `string` | Nationality / ICC national team representation |
| `Notes` | `string` | Contractual designations (`Captain`, `Overseas`, `Wildcard`, `Replacement`, `Injury`) |

---

## 🔄 Updating Data

To regenerate or synchronize squad rosters from code, execute:

```bash
python scripts/update_squads.py
```

This updates both `data/squadofsunrisers.xlsx` and the root fallback mirror.
