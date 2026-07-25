# algosystem developer entrypoints.
#
# Fresh clone, first time:
#     make install        # dependencies
#     make test           # run the suite
#     make lint           # style + static checks
SHELL := /bin/bash

POETRY  ?= poetry
PACKAGE ?= algosystem

.DEFAULT_GOAL := help
.PHONY: help install test test-cov lint format typecheck docs clean

help: ## Show available targets
	@echo "algosystem -- backtesting and dashboard library"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (main entrypoint)
	@command -v $(POETRY) >/dev/null 2>&1 || { \
		echo "poetry not found. Install it: https://python-poetry.org/docs/#installation"; \
		exit 1; \
	}
	@$(POETRY) install
	@echo ""
	@echo "Ready. Run 'make test' or 'make lint'."

test: ## Run the test suite
	@$(POETRY) run pytest -q

test-cov: ## Run tests with a coverage report
	@$(POETRY) run pytest --cov=$(PACKAGE) --cov-report=term-missing

lint: ## Check formatting and lint rules (read-only)
	@$(POETRY) run black --check $(PACKAGE) tests
	@$(POETRY) run isort --check-only $(PACKAGE) tests
	@$(POETRY) run ruff check $(PACKAGE)

format: ## Auto-fix formatting and import order
	@$(POETRY) run black $(PACKAGE) tests
	@$(POETRY) run isort $(PACKAGE) tests

typecheck: ## Run mypy
	@$(POETRY) run mypy $(PACKAGE)

docs: ## Build the Sphinx docs site
	@if [ ! -f docs/conf.py ]; then \
		echo "docs/conf.py not present on this branch yet -- see the docs PR."; \
		exit 1; \
	fi
	@$(POETRY) install --only docs --no-root
	@$(POETRY) run sphinx-build -b html docs docs/_build/html
	@echo "Docs built -> docs/_build/html/index.html"

clean: ## Remove caches and build artifacts
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache .mypy_cache .ruff_cache dist docs/_build
	@echo "Cleaned caches and build artifacts."
