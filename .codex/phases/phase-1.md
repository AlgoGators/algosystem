# Phase 1 — Prune to scope, then build the shared kernel

Read `.codex/SPEC.md` in full first. It is the authoritative design. This prompt
overrides it only where they conflict, and you must record any conflict in
`deviations`.

You are working in the `algosystem` Python package on branch `ddd-restructure`.
This phase does **no** domain modelling. It has two jobs: cut the package down
to the scope described in SPEC §1, and lay the shared kernel that every later
phase builds on. Getting the deletion right matters more than getting the kernel
elegant.

---

## Job A — Delete everything outside scope

AlgoSystem is now: backtest a price series, persist runs to Postgres, report
with a quantstats tearsheet. The custom dashboard is gone. quantstats' own
tearsheet replaces it entirely.

Delete these outright — files, directories, tests, dependencies, docs and all
call sites:

- `algosystem/backtesting/dashboard/` — the whole tree (~4,700 lines: the HTML
  generator, the Jinja-ish template modules, the Flask config editor, the
  component catalog, the PPTX writer, the slide generator, the data formatter,
  the config parser, the default-config JSON).
- `tests/test_dashboard_generation.py`, `tests/test_web_app.py`,
  `tests/test_web_app_components.py`.
- Every CLI command in `algosystem/cli/commands.py` whose purpose is the
  dashboard or its config files: `launch`, `render`, `create_config`, `IP`,
  `dashboard`, `show_config`, `list_configs`, `reset_user_config`, and the
  `ensure_user_config_exists` helper and `USER_CONFIG_*` constants that support
  them. Also remove the `sys.path.append` hack at the top of that module.
- Every method on `Engine` and on the `AlgoSystem` facade that generates a
  dashboard: `Engine.generate_dashboard`, `Engine.generate_standalone_dashboard`,
  `Engine._display_charts`, `AlgoSystem.generate_dashboard`,
  `AlgoSystem.generate_standalone_dashboard`, `AlgoSystem.load_config`,
  `AlgoSystem.save_config`.
- The now-unused dependencies in `pyproject.toml`: `flask`, `weasyprint`,
  `markdown`, `python-pptx`, `plotly`, `kaleido`. Check each for remaining
  imports before removing it. Leave `matplotlib` and `seaborn` in place —
  quantstats needs them.
- Repo-root build litter that is checked in and should not be:
  `dashboard.html`, `backtest_presentation.pptx`, `charts/`, `test_dashboard/`,
  `backtest_exports/`, `htmlcov/`, `coverage.xml`, `.coverage`, `dist/`.
  Delete them and add matching entries to `.gitignore`.

Keep, do not delete: `Engine` itself, `metrics.py`, `analysis/`,
`data/benchmark.py`, `data/connectors/`, `utils/`, `api.py`, and the CLI's
non-dashboard behaviour. Those are Phase 2–5's problem.

`AlgoSystem.export_charts` currently hand-rolls matplotlib PNG export. Delete it
too — quantstats' tearsheet supersedes it.

After deleting, the package must still import and the remaining tests must still
run. Fix whatever breaks.

## Job B — Build `algosystem/shared/`

Four modules. This is the shared kernel: it may be imported by every context and
may itself import only the stdlib, pandas and numpy.

### `shared/errors.py`

An exception hierarchy rooted at `AlgoSystemError(Exception)`. At minimum:

```
AlgoSystemError
├── DomainError                  invariant violated
│   ├── InvalidPriceSeriesError  empty, NaN, non-positive, unsorted index
│   ├── InvalidDateRangeError    end before start, no data in range
│   ├── InsufficientDataError    too few points to compute what was asked
│   └── InvalidCapitalError      non-positive initial capital
├── CalculationError             a metric could not be computed
├── RepositoryError              persistence failed
│   ├── RunNotFoundError
│   └── DuplicateRunError
├── MarketDataError              benchmark fetch/cache failed
│   └── UnknownBenchmarkError
└── ConfigurationError           missing or invalid configuration
```

Each carries a useful message. `RunNotFoundError` should hold the run id it
looked for. These replace every `{"error": ...}` return and every bare `except:`
in the codebase — but you only *define* them in this phase; later phases wire
them in.

### `shared/metric_key.py`

`class MetricKey(str, Enum)` — the single source of truth for metric names
(SPEC R4). Derive the members from what `algosystem/backtesting/metrics.py`
currently produces, so nothing is lost. Read that file and enumerate every key
it can set. Group the members with comments: returns, risk, ratios, trade
statistics, monthly statistics, benchmark-relative.

Subclassing `str` is deliberate: `MetricKey.SHARPE_RATIO == "sharpe_ratio"` is
`True`, so existing string-keyed call sites keep working while we migrate.

Also provide, in the same module:

- `MetricKey.label()` → a human-readable name ("Sharpe Ratio").
- `MetricKey.is_benchmark_relative()` → `True` for alpha, beta, correlation,
  tracking error, information ratio, capture ratios.
- A module-level `LEGACY_ALIASES: dict[str, MetricKey]` mapping the historical
  duplicate names to their canonical member. `metrics.py:272-273` currently
  emits `annual_return` as an alias of `annualized_return` and `volatility` as
  an alias of `annualized_volatility` — capture exactly that, and search the
  codebase for any other alias pairs before you finish.

### `shared/values.py`

Frozen dataclasses, validating in `__post_init__`, raising the errors above:

- `Money` — amount plus 3-letter currency, default `"USD"`. Rejects NaN and
  infinity. Arithmetic (`+`, `-`, `*` by a scalar) that refuses to mix
  currencies. `__str__` formats as `$1,234.56`.
- `Ratio` — a dimensionless ratio (Sharpe, beta). Rejects NaN/inf.
- `Percent` — stores the **fraction** (0.0523), exposes `.as_fraction` and
  `.as_percent` (5.23), `__str__` as `5.23%`. Getting this direction wrong is
  the classic bug here, so make the constructor unambiguous and test it.
- `RunId` — wraps a string. Non-empty, no whitespace. Classmethod
  `RunId.generate()` producing the existing timestamp format
  `YYYYMMDD_HHMMSS_mmm` (see `inserter_manager.py:get_next_run_id`).
- `DateRange` — `start` and `end` as `pd.Timestamp`. Rejects end-before-start.
  `.contains(ts)`, `.days`, `.mask(index)` returning a boolean mask for a
  `DatetimeIndex`, and `DateRange.from_index(idx)`.

### `shared/logging.py`

Move `algosystem/utils/_logging.py` here unchanged in behaviour. Update the
handful of importers. Delete `algosystem/utils/` if `decorators.py` turns out to
be unused — check first.

## Job C — Tests

Add `tests/shared/test_errors.py`, `test_metric_key.py`, `test_values.py`.
Cover: every value object's validation rejects bad input with the right typed
error; `Percent` round-trips fraction↔percent correctly; `Money` refuses to add
different currencies; `RunId.generate()` produces unique, correctly-formatted
ids; `DateRange.mask` selects the right rows; every `MetricKey` member has a
label; `LEGACY_ALIASES` resolves to real members.

Also: `tests/test_risk_analysis.py` is 0 bytes. Either write real tests for
`algosystem/analysis/risk.py` or delete the empty file. Do not leave it empty.

## Acceptance criteria

1. `algosystem/backtesting/dashboard/` does not exist. `grep -ri "dashboard"
   algosystem/` returns nothing meaningful.
2. `python -c "import algosystem"` succeeds, prints nothing, creates no
   directories.
3. `python -m pytest tests/ -q` runs. Report the real numbers.
4. `python -m black algosystem/ tests/ && python -m isort algosystem/ tests/`
   applied, then `--check` passes.
5. `pyproject.toml` no longer lists the six removed dependencies.
6. The new tests pass.

## Reply

Follow SPEC §9 exactly. Reply with one JSON object matching the output schema,
no prose around it. Set `phase` to `"phase-1"`.

In `deviations`, be specific about anything you kept that this prompt told you
to delete, and why. In `followups`, flag anything in the remaining code that you
noticed will fight Phase 2's domain model.
