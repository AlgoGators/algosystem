# Phase 2 — The domain model and the quantstats anti-corruption layer

Read `.codex/SPEC.md` in full first, and read `.codex/reports/phase-1.json` to
see what the previous phase actually did and deferred.

This is the phase the whole restructure exists for. Two things happen: the
backtesting domain gets a real model with its own vocabulary, and quantstats
gets pushed behind a port so the model never sees it.

---

## Job A — `algosystem/backtesting/domain/`

Pure Python + pandas + numpy + `algosystem.shared`. Nothing else (SPEC R1, R6).
No file I/O, no network, no database, no plotting, no `os.getenv`.

### `domain/equity_curve.py`

`EquityCurve` — a value object wrapping a `pd.Series`.

Validates on construction, raising `InvalidPriceSeriesError`: index is a
`DatetimeIndex`, index is monotonically increasing and unique, at least 2
points, no NaN, all values strictly positive.

API: `.values` → the underlying `pd.Series` (adapters need the raw thing —
this is the deliberate escape hatch from SPEC §4; do not box individual
elements); `.returns()` → simple pct-change `pd.Series` with the first NaN
dropped; `.log_returns()`; `.start` / `.end` → `pd.Timestamp`;
`.initial_value` / `.final_value` → `Money`; `.date_range` → `DateRange`;
`.slice(DateRange)` → a new `EquityCurve`, raising `InvalidDateRangeError` if
the slice is empty; `.rebase(to: Money)` → a new `EquityCurve` normalised so the
first value equals `to` (this is what `Engine.run()` currently does inline at
`engine.py:132-134`); `.align_with(other)` → a tuple of two curves on the
intersection of their indices; `__len__`.

Constructors: `EquityCurve.from_series(s)` and `EquityCurve.from_frame(df,
column=None)` — the latter carries over the existing rule from
`engine.py:43-52` (use the named column, or the only column, else raise).

### `domain/metrics.py`

`PerformanceMetrics` — frozen dataclass, one `Optional[float]` field per
`MetricKey` member. A metric that could not be computed is `None`, never a
fabricated value.

API: `.get(key: MetricKey) -> Optional[float]`; `.to_dict() -> dict[str, float]`
keyed by `MetricKey.value`, omitting `None`s; `.from_dict(mapping)` classmethod
accepting `MetricKey` or string keys and resolving `LEGACY_ALIASES`;
`.benchmark_relative()` → only the benchmark-dependent metrics;
`.__getitem__(key: str)` for backward compatibility, emitting
`DeprecationWarning` and resolving through `LEGACY_ALIASES` — existing user code
does `results["metrics"]["sharpe_ratio"]` and must not break;
`.__contains__` likewise.

### `domain/backtest.py`

`Backtest` — the aggregate root. Replaces `Engine` as the model.

Construct from: `equity_curve: EquityCurve`, `benchmark: Optional[EquityCurve]`,
`date_range: Optional[DateRange]`, `initial_capital: Optional[Money]`,
`run_id: Optional[RunId]`. Port the existing behaviour from
`engine.py:42-113`: slice both curves to the date range; default the range to
the strategy's own index; default initial capital to the curve's first value;
align the benchmark to the strategy where they overlap. Every failure raises a
typed error from `shared/errors.py` — `InvalidDateRangeError` when the slice is
empty, `InvalidCapitalError` for non-positive capital, and so on.

`run(calculator: MetricsCalculator) -> BacktestResult` — rebase the curve to
initial capital, hand the rebased curve and benchmark to the calculator, wrap
the answer in a `BacktestResult`. That is all it does. It is pure and it is
idempotent.

`BacktestResult` — frozen: `run_id`, `equity_curve`, `benchmark_curve`,
`metrics`, `date_range`, `initial_capital`, `final_capital`, `total_return`
(as `Percent`). Add `.summary()` returning a small plain dict for display, and
`.to_legacy_dict()` returning the exact shape `Engine.results` used to have
(keys: `equity`, `initial_capital`, `final_capital`, `returns`, `data`,
`start_date`, `end_date`, `metrics`, `plots`) so the deprecation shim in Job C
can be thin. `plots` is now empty — time-series data moves to the calculator
port; see Job B.

### `domain/ports.py`

Abstract interfaces (`abc.ABC` with `@abstractmethod`, or `typing.Protocol` —
pick one and be consistent). Declare all three now even though Phases 3 and 4
implement two of them:

- `MetricsCalculator` — `calculate(equity: EquityCurve, benchmark:
  Optional[EquityCurve]) -> PerformanceMetrics` and `time_series(equity:
  EquityCurve, benchmark: Optional[EquityCurve], window: int) -> dict[str,
  pd.Series]`.
- `BacktestRunRepository` — `save(result) -> RunId`, `get(run_id) ->
  BacktestResult`, `delete(run_id) -> None`, `list_runs(limit, offset) ->
  list[RunSummary]`, `find_best(metric: MetricKey, limit: int) ->
  list[RunSummary]`, `search(query: str, field: str) -> list[RunSummary]`.
  Define `RunSummary` as a small frozen dataclass here.
- `TearsheetRenderer` — `render(result: BacktestResult, output_path: Path,
  title: str) -> Path`.

## Job B — `infrastructure/quantstats_calculator.py`

`QuantStatsMetricsCalculator` implements `MetricsCalculator`. This is the only
module in the package permitted to import quantstats (SPEC R3).

Port the real logic from `algosystem/backtesting/metrics.py` — every metric it
computes must still be computed, keyed by `MetricKey`. But the error handling
inverts completely:

- **Delete every fabricated fallback.** `metrics.py:298` sets
  `cvar_95 = var_95 * 1.3`; `metrics.py:308-314` invents Sharpe from the
  annualised numbers when quantstats raises. All of it goes. A metric that
  cannot be computed is `None`.
- Replace the 10 bare `except:` clauses. Catch narrowly, and where you must
  catch broadly, log at debug and set the metric to `None`. Never swallow
  silently, never guess.
- The `{"error": ...}` returns at `metrics.py:208-239` become raised
  `InsufficientDataError` / `CalculationError`.
- Keep the `max_abs_return > 10` sanity check but raise
  `InvalidPriceSeriesError` instead of returning an error dict.

`time_series()` ports `calculate_time_series_data` from the same file — rolling
Sharpe/Sortino/volatility/skew/VaR/drawdown-duration, monthly and yearly
returns, the 3m/6m/1y rolling returns, and the benchmark-relative series. It
returns raw `pd.Series` because that is genuinely what callers want; it is not
part of the aggregate.

`algosystem/analysis/performance.py` and `algosystem/analysis/risk.py` overlap
heavily with this. Fold anything they compute that quantstats does not into this
adapter, then delete both modules. Move `analysis/portfolio.py` to
`algosystem/portfolio/optimization.py` unchanged — it is mean-variance
optimization, unrelated to this context, and it stays as-is. Delete
`algosystem/analysis/` once empty.

Add `infrastructure/fake_calculator.py`: a deterministic `MetricsCalculator`
returning fixed values, so domain tests never touch quantstats.

## Job C — Keep the old API alive

`Engine` must keep working for one release. Rewrite `algosystem/backtesting/
engine.py` as a thin shim: same constructor signature, same `run()`,
`get_results()`, `get_metrics()`, `print_metrics()`, `get_plots()` surface.
Internally it builds a `Backtest`, runs it with a `QuantStatsMetricsCalculator`,
and returns `result.to_legacy_dict()`. Emit `DeprecationWarning` on construction
pointing at `Backtest`.

Delete `Engine.export_db` — Phase 3 replaces it with the repository. Note it in
`followups`.

## Job D — Tests

`tests/backtesting/domain/` — `test_equity_curve.py`, `test_metrics.py`,
`test_backtest.py`. These must run with **no quantstats import**, using the fake
calculator. Cover every invariant and every typed error. Test that `rebase`
preserves returns exactly, that `align_with` intersects correctly, and that
`PerformanceMetrics.__getitem__` warns but works.

`tests/backtesting/infrastructure/test_quantstats_calculator.py` — real
quantstats, on a small deterministic series. Assert that an uncomputable metric
comes back `None` rather than fabricated.

Update `tests/test_engine.py` and `tests/test_metrics.py` to the new reality:
keep them as the deprecation-shim regression suite, asserting the legacy dict
shape still holds.

## Acceptance criteria

1. `grep -rn "quantstats" algosystem/` matches only
   `infrastructure/quantstats_calculator.py`.
2. `grep -rn "^from\|^import" algosystem/backtesting/domain/` shows only stdlib,
   pandas, numpy and `algosystem.shared`.
3. `grep -rn "except:" algosystem/` returns nothing.
4. `grep -rn '"error"' algosystem/` returns nothing.
5. Domain tests pass with quantstats uninstallable — verify by running them with
   `-p no:cacheprovider` and confirming no quantstats import occurs (e.g. assert
   `"quantstats" not in sys.modules` in a test).
6. `python -m pytest tests/ -q` — report real numbers, no new failures.
7. black + isort applied and clean.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-2"`.

`deviations` must call out any metric from the old `metrics.py` you could not
carry over, and any place you kept a fallback value. `followups` must list
anything Phase 3 needs to know about the repository port's shape.
