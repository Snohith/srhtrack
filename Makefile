.PHONY: help install run test sync-squads clean lint

help:
	@echo "Available commands for SRHXtra:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make run          - Launch Streamlit dashboard locally"
	@echo "  make test         - Run full pytest automated verification suite"
	@echo "  make sync-squads  - Synchronize squad database from script to Excel & DB"
	@echo "  make clean        - Remove bytecode, test caches, and temporary artifacts"

install:
	pip install -r requirements.txt

run:
	streamlit run app.py

bot:
	python bot.py

test:
	pytest tests/

sync-squads:
	python scripts/update_squads.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf .pytest_cache
