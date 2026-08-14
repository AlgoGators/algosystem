.PHONY: check

check:
	poetry run python -m black --check algosystem tests
	poetry run python -m isort --check-only algosystem tests
	poetry run python -m ruff check algosystem tests
	poetry run lint-imports
	poetry run python -m pytest tests/ -q
