# 🤝 Helping out with the Sunrisers news hub

Thanks for helping! These little rules keep the news hub friendly for the next fan who reads the code.

---

## 🛠️ Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Snohith/srhtrack.git
   cd srhtrack
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pytest
   ```

4. **Run the Test Suite**:
   ```bash
   pytest tests/
   ```

5. **Start Streamlit Dashboard Locally**:
   ```bash
   streamlit run app.py
   ```

---

## 📋 Code Conventions & Best Practices

- **Full names please**: everyone added to `data/squadofsunrisers.xlsx` needs a first + last name.
- **Nicknames**: only unusual names go in `PLAYER_NICKNAMES` in `our_teams/players.py` (like `Klaasen`). Common surnames (`Sharma`, `Patel`) must never stand alone.
- **Skipping copies**: never make `news.link` or `news.title` unique on their own — one story may belong to several players.
- **Context Managers**: Always wrap database connections using `with closing(get_connection()) as conn:`.

---

## 🧪 Testing Checklist

Before submitting a Pull Request:
- [ ] Run `pytest tests/` and verify all tests pass.
- [ ] Verify `data/squadofsunrisers.xlsx` synchronizes cleanly via `python handy_tools/refresh_player_list.py`.
- [ ] Ensure no temporary files (`.DS_Store`, `*.log`, `*.db`) are staged.
