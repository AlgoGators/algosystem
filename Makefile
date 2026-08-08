# algosystem developer entrypoints.
#
# Fresh clone, first time:
#     make install        # dependencies
#     make test           # run the suite
#     make lint           # style + static checks

POETRY  ?= poetry
PYTHON  ?= python
PACKAGE ?= algosystem

.DEFAULT_GOAL := help
.PHONY: help install test test-cov lint format typecheck docs clean

help: ## Show available targets
	@$(PYTHON) -c "from pathlib import Path; import re; rows=[]; pattern=re.compile(r'^([A-Za-z_-]+):.*?## (.*)$$'); [rows.append(m.groups()) for line in Path('Makefile').read_text().splitlines() for m in [pattern.match(line)] if m]; print('algosystem -- backtesting and dashboard library'); print(); [print('  {0:<12} {1}'.format(name, desc)) for name, desc in sorted(rows)]"

install: ## Install dependencies (main entrypoint)
	@$(POETRY) --version
	@$(POETRY) install
	@$(PYTHON) -c "print(); print('Ready. Run make test or make lint.')"

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
	@$(PYTHON) -c "from pathlib import Path; import sys; sys.exit(0 if Path('docs/conf.py').is_file() else 'docs/conf.py not present on this branch yet -- see the docs PR.')"
	@$(POETRY) install --only docs --no-root
	@$(POETRY) run sphinx-build -b html docs docs/_build/html
	@$(PYTHON) -c "print('Docs built -> docs/_build/html/index.html')"

clean: ## Remove caches and build artifacts
	@$(PYTHON) -c "import shutil; from pathlib import Path; [shutil.rmtree(p, ignore_errors=True) for p in Path('.').rglob('__pycache__')]; [shutil.rmtree(Path(p), ignore_errors=True) for p in ('.pytest_cache', '.mypy_cache', '.ruff_cache', 'dist', 'docs/_build')]; print('Cleaned caches and build artifacts.')"
