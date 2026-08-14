# AlgoSystem — DDD Restructure Spec

This is the authoritative target design. Every phase prompt refers back to it.
Read this file in full before starting any phase.

---

## 1. What AlgoSystem is (after this work)

A pythonic library that does exactly three things:

1. **Backtest** a strategy given its price/equity series (and an optional benchmark).
2. **Persist** backtest runs to Postgres and read them back.
3. **Report** via **quantstats tearsheets** — we do not build reporting ourselves.

Anything outside those three things is out of scope and should be deleted, not
refactored. In particular the custom HTML dashboard, its Flask editor, its
JSON component-config system, and the PowerPoint exporter are **removed
entirely**. quantstats' own tearsheet replaces all of it.

## 2. Non-negotiable architectural rules

These are the rules the whole restructure exists to establish. A change that
violates one of them is wrong even if the tests pass.

**R1 — The domain imports nothing from outside itself.**
`algosystem/*/domain/**` may import: the Python stdlib, `pandas`, `numpy`, and
`algosystem.shared`. It may **not** import `quantstats`, `yfinance`,
`sqlalchemy`, `psycopg2`, `matplotlib`, `click`, `rich`, `flask`, or anything
from `application/` or `infrastructure/`.

**R2 — Dependencies point inward.**
`interfaces → application → domain` and `infrastructure → domain`.
Never the reverse. `domain` is a leaf.

**R3 — Vendor libraries live behind ports.**
A *port* is an abstract interface declared in `domain/ports.py`. An *adapter* is
a concrete implementation in `infrastructure/`. quantstats, yfinance and
Postgres are all reached only through ports. This is an anti-corruption layer:
vendor types (e.g. whatever quantstats returns) must not leak past the adapter.

**R4 — Metric names are declared exactly once.**
The `MetricKey` enum in `algosystem/shared/metric_key.py` is the single source
of truth for every performance-metric name. The calculator, the value object,
the ORM columns and any serialization all reference `MetricKey`. A bare string
literal like `"sharpe_ratio"` appearing anywhere outside `metric_key.py` is a
defect.

**R5 — Invariants raise; they never return error dicts.**
Every failure path raises a typed exception from `algosystem/shared/errors.py`.
Returning `{"error": ...}` is forbidden. Bare `except:` is forbidden. `except
Exception` is only acceptable when the exception is re-raised as a typed
domain error with the original chained via `raise ... from e`.

**R6 — No I/O, no global state, no side effects in the domain.**
No file reads, no network, no database, no plotting, no `os.getenv`, no
`os.makedirs`, no module-level mutable state. Configuration is passed in
explicitly, never discovered ambiently.

**R7 — Value objects are immutable.**
`@dataclass(frozen=True, slots=True)`. Validate in `__post_init__`. This applies
to everything in `shared/values.py` and to `PerformanceMetrics`.

## 3. Target package layout

```
algosystem/
  __init__.py                   public API surface (see §5)
  shared/                       shared kernel — importable by every context
    errors.py                   exception hierarchy
    metric_key.py               MetricKey enum (R4)
    values.py                   Money, Ratio, Percent, RunId, DateRange
    logging.py                  get_logger

  backtesting/                  bounded context: running and storing backtests
    domain/
      equity_curve.py           EquityCurve value object (wraps pd.Series)
      metrics.py                PerformanceMetrics value object
      backtest.py               Backtest aggregate root + BacktestResult
      ports.py                  MetricsCalculator, BacktestRunRepository,
                                TearsheetRenderer  (abstract)
    application/
      dto.py                    request/response DTOs
      run_backtest.py           RunBacktest use case
      archive_run.py            ArchiveRun use case
      load_run.py               LoadRun use case
      compare_runs.py           CompareRuns use case
      generate_tearsheet.py     GenerateTearsheet use case
    infrastructure/
      quantstats_calculator.py  QuantStatsMetricsCalculator (MetricsCalculator)
      quantstats_tearsheet.py   QuantStatsTearsheetRenderer (TearsheetRenderer)
      persistence/
        config.py               DatabaseConfig (explicit, injected)
        schema.py               SQLAlchemy models
        postgres_repository.py  PostgresBacktestRunRepository
        in_memory_repository.py InMemoryBacktestRunRepository

  marketdata/                   bounded context: benchmark price data
    domain/
      benchmark.py              Benchmark, BenchmarkCatalog, Ticker
      ports.py                  BenchmarkProvider, BenchmarkCache
    application/
      fetch_benchmark.py        FetchBenchmark use case
    infrastructure/
      yfinance_provider.py      YFinanceBenchmarkProvider
      parquet_cache.py          ParquetBenchmarkCache

  portfolio/                    standalone: mean-variance optimization
    optimization.py             (moved from analysis/portfolio.py, kept intact)

  interfaces/
    api.py                      AlgoSystem facade — thin, over use cases
    cli/main.py                 click commands — thin, over use cases
```

## 4. Domain model

**`EquityCurve`** — value object wrapping a `pd.Series` indexed by a
`DatetimeIndex`. Validates: non-empty, monotonic index, no NaN, all positive.
Exposes `.values` (the raw Series, for adapters), `.returns()`, `.start`,
`.end`, `.initial_value`, `.final_value`, `.slice(DateRange)`. Users who want a
DataFrame get it here — do **not** box individual elements.

**`PerformanceMetrics`** — frozen value object holding one typed field per
`MetricKey`, all `Optional[float]` except where a value is always computable.
Provides `.get(MetricKey)`, `.to_dict()` → `dict[str, float]` keyed by
`MetricKey.value`, and `__getitem__(str)` for one deprecation cycle so existing
`metrics["sharpe_ratio"]` callers keep working (emit `DeprecationWarning`).

**`Backtest`** — aggregate root. Constructed from an `EquityCurve`, an optional
benchmark `EquityCurve`, a `DateRange` and initial capital (`Money`).
Enforces all invariants in the constructor and raises typed errors. `run()`
takes a `MetricsCalculator` and returns a `BacktestResult`; it is **pure** —
no I/O of any kind.

**`BacktestResult`** — frozen: `run_id`, `equity_curve`, `benchmark_curve`,
`metrics`, `date_range`, `initial_capital`, `final_capital`, `total_return`.

## 5. Public API (must keep working)

```python
from algosystem import Backtest, BacktestResult, MetricKey, PerformanceMetrics
from algosystem import AlgoSystem          # facade
from algosystem import run_backtest        # convenience function
```

Legacy names `Engine` and `AlgoSystem.run_backtest(...)` must continue to work
through a deprecation shim that emits `DeprecationWarning` and delegates to the
new model. Do not silently break users on PyPI.

## 6. Known defects to fix along the way

Fix these as part of whichever phase touches the code. Do not leave them.

- `db_manager.py:201-211` `compare_backtests` interpolates caller-supplied run
  IDs directly into SQL. **SQL injection.** Must be parameterized.
- `api.py:317` calls `engine.export_to_db(db_url, table_name)`, which does not
  exist — `Engine` defines `export_db(run_id=...)`. Raises `AttributeError` on
  every call.
- `engine.py:383-389` reads `self.positions` / `self.symbol_pnl`, never assigned
  anywhere, so `include_positions` / `include_pnl` are permanently dead. Either
  wire them to real data or delete the parameters.
- `metrics.py` — 10 bare `except:` clauses that fabricate fallback values
  (e.g. `cvar_95 = var_95 * 1.3`). Delete the fabrication; raise or return
  `None` for a metric that genuinely cannot be computed.
- `benchmark.py:21` runs `os.makedirs` at import time. Import must have no
  side effects.
- `tests/test_risk_analysis.py` is 0 bytes.

## 7. Conventions

- Python 3.9+ compatible syntax (`pyproject.toml` declares `>=3.9,<4.0`). Use
  `from __future__ import annotations`; do not use `X | Y` unions at runtime,
  `slots=True` on dataclasses is 3.10+ so guard it or omit it if targeting 3.9.
  **Confirm the floor in `pyproject.toml` before choosing syntax.**
- Full type hints on every public function and method.
- Google-style docstrings on public API; no docstring padding on trivial code.
- `black` (line-length 100) and `isort` (profile=black) formatting.
- Tests use `pytest`. Domain tests must run with no database, no network, and
  no filesystem writes.

## 8. Definition of done for every phase

A phase is complete only when all of these hold:

1. `python -c "import algosystem"` succeeds with no side effects and no warnings.
2. `python -m pytest tests/ -q` runs. Pre-existing failures unrelated to your
   phase may remain, but you must report them; you may not introduce new ones.
3. `python -m black --check algosystem/ && python -m isort --check algosystem/`
   passes (run the formatters, do not just check).
4. No rule in §2 is violated by code you wrote.
5. You updated the tests that your phase's changes affected.

## 9. How to reply

Your final message must be a single JSON object matching the supplied output
schema. No prose outside the JSON, no markdown fences.

Rules for the fields:

- `summary` — under 800 characters, plain prose. What you actually did, what
  changed structurally. Not a file list.
- `checks` — you must actually run the commands and report real numbers. Do not
  estimate. If a command could not run, set the count to `-1` and explain in
  `deviations`.
- `deviations` — anything you did differently from this spec or the phase
  prompt, and **why**. This is the most important field. An empty array means
  you followed the spec exactly; only use it if that is literally true.
- `followups` — work you deliberately left for a later phase, and anything you
  found that this spec does not cover and that a human needs to decide.

Write nothing to `.codex/reports/` yourself; the harness captures your reply.

## 10. Working style

- Work only inside this repository. Do not touch files outside it.
- Commit nothing. Leave changes in the working tree; the human reviews and
  commits.
- Delete dead code outright. Do not comment it out, do not leave
  `_deprecated_old_thing.py` files lying around. Git has the history.
- If a phase prompt and this spec conflict, the phase prompt wins for that
  phase, and you must record the conflict in `deviations`.
- If you find yourself unable to satisfy a rule, stop, set `status` to
  `blocked`, and explain precisely what blocked you. Do not silently work
  around an architectural rule.
