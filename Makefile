.PHONY: help install test collect status test-telegram validate-roster clean

help:
	@echo "SRHXtra commands:"
	@echo "  make install        - Install dependencies"
	@echo "  make test           - Run the test suite"
	@echo "  make collect        - Run one collection + Telegram delivery cycle"
	@echo "  make status         - Show article and delivery counts"
	@echo "  make test-telegram  - Send one explicit Telegram test message"
	@echo "  make validate-roster - Validate the Excel roster (read-only)"
	@echo "  make clean          - Remove bytecode and test caches"

install:
	pip install -r requirements.txt

test:
	pytest tests/

collect:
	python -m regular_checks.check_news

status:
	python -m regular_checks.check_news --status

test-telegram:
	python -m regular_checks.check_news --test-telegram

validate-roster:
	python -m handy_tools.validate_roster

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".DS_Store" -delete
	rm -rf .pytest_cache
