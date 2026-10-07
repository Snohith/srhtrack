# 🤝 Contributing to @SRHXtra

Thank you for your interest in contributing to **@SRHXtra**! Follow these guidelines to maintain production quality across the repository.

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

- **Strict Full-Name Matching**: All squad members added to `data/squadofsunrisers.xlsx` must include first and last names.
- **Single-Name Aliases**: Only distinct first or last names may be registered in `PLAYER_ALIASES` in `config/roster.py` (e.g. `Klaasen`, `Cummins`, `Head`). Common surnames (e.g. `Hussain`, `Sharma`, `Patel`) must never be added as single-token aliases.
- **Target-Aware Deduplication**: Never apply global uniqueness constraints to `news.link` or `news.title` in database schemas.
- **Context Managers**: Always wrap database connections using `with closing(get_connection()) as conn:`.

---

## 🧪 Testing Checklist

Before submitting a Pull Request:
- [ ] Run `pytest tests/` and verify all tests pass.
- [ ] Verify `data/squadofsunrisers.xlsx` synchronizes cleanly via `python scripts/update_squads.py`.
- [ ] Ensure no temporary files (`.DS_Store`, `*.log`, `*.db`) are staged.
