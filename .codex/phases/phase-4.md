# Phase 4 — Application layer and quantstats tearsheet reporting

Read `.codex/SPEC.md` and `.codex/reports/phase-3.json` first.

The domain and the adapters exist. Nothing yet composes them, and there are
still two rival orchestration paths (`api.py` and the CLI) that have already
drifted apart. This phase adds the use-case layer they both sit on, and wires
reporting to quantstats' own tearsheet.

---

## Job A — `backtesting/application/`

Use cases. Each is a class with an injected collaborator set and a single
`execute()` method taking a request DTO and returning a response DTO. No use
case constructs its own dependencies — they arrive through `__init__`. No use
case imports an adapter module; it depends only on the ports.

### `dto.py`

Frozen request/response dataclasses. Keep them dumb: primitives, `pd.Series`,
and shared value objects only — no domain aggregates leaking out to callers.

`RunBacktestRequest` (data, benchmark, start, end, initial capital, price
column), `RunBacktestResponse` (run id, metrics dict, equity series, summary
figures). `ArchiveRunRequest/Response`, `LoadRunRequest/Response`,
`CompareRunsRequest/Response`, `GenerateTearsheetRequest/Response`.

### The use cases

- `run_backtest.py` — `RunBacktest(calculator: MetricsCalculator)`. Coerces the
  incoming `DataFrame`/`Series` into an `EquityCurve`, builds the `Backtest`,
  runs it, maps the result to a response DTO. The input-coercion rules currently
  living in `Engine.__init__` belong here, not in the aggregate: the aggregate
  should receive an already-valid `EquityCurve`.
- `archive_run.py` — `ArchiveRun(repository: BacktestRunRepository)`. Replaces
  the deleted `Engine.export_db`. Takes a `BacktestResult` plus name,
  description and hyperparameters; returns the `RunId`.

  **Fix this defect first — it currently breaks the library's main path.**
  A `BacktestResult` built without an explicit run id carries the sentinel
  `RunId("unpersisted")`. Saving two such results therefore raises
  `DuplicateRunError` on the second one:

  ```
  >>> repo.save(run_a)   -> RunId('unpersisted')
  >>> repo.save(run_b)   -> DuplicateRunError: Backtest run already exists: unpersisted
  ```

  Run a backtest and save it is the single most common thing a user will do, so
  this must work. Remove the sentinel entirely: make `BacktestResult.run_id`
  an `Optional[RunId]` defaulting to `None`, and have the repository assign
  `RunId.generate()` on save when it is `None`, returning the assigned id.
  Identity belongs to persistence, not to a freshly-computed result. Update
  both repository adapters, the `Backtest` aggregate, and any test that asserts
  the sentinel. Add a regression test that saves two un-identified results and
  asserts two distinct ids come back.
  `Engine.export_db` had `include_positions` / `include_pnl` parameters reading
  `self.positions` / `self.symbol_pnl`, which were never assigned anywhere and
  so were permanently dead (SPEC §6). Do not carry them over. Note it in
  `deviations`.
- `load_run.py` — `LoadRun(repository)`. Rehydrates a stored run into a
  `BacktestResult`.
- `compare_runs.py` — `CompareRuns(repository)`. Takes run ids, returns their
  summaries plus aligned equity curves in one DataFrame.
- `generate_tearsheet.py` — `GenerateTearsheet(renderer: TearsheetRenderer)`.

## Job B — `infrastructure/quantstats_tearsheet.py`

`QuantStatsTearsheetRenderer` implementing the `TearsheetRenderer` port. This is
all the reporting AlgoSystem has now — we are not rebuilding what quantstats
already does well.

Wrap `quantstats.reports`. Support three modes via a `mode` argument:

- `"html"` → `qs.reports.html(...)` writing a self-contained file. This is the
  default and the replacement for the deleted dashboard.
- `"full"` → `qs.reports.full(...)` printing to stdout for notebook use.
- `"basic"` → `qs.reports.basic(...)`.

Pass the strategy returns from `result.equity_curve.returns()` and, when
present, the benchmark returns from `result.benchmark_curve.returns()`.
Support `title`, `output` path, `rf` (risk-free rate) and `periods_per_year`.

Two things to get right:

1. **quantstats calls `matplotlib.pyplot` and will try to open a GUI window.**
   Force the `Agg` backend inside this adapter before importing quantstats, and
   restore whatever was there afterwards. The library must never pop a window
   open on a user who only asked for an HTML file.
2. quantstats is noisy — it emits `FutureWarning`s from pandas and sometimes
   writes to stdout. Suppress within the adapter, do not let it leak.

Failures raise `CalculationError` chained from the original. If the output
directory does not exist, create it — this is infrastructure, so file I/O is
allowed here (SPEC R6 constrains the domain only).

Together with `quantstats_calculator.py` from Phase 2, this module and that one
are the only two places in the package permitted to import quantstats.

## Job C — Rewrite `interfaces/api.py`

`AlgoSystem` becomes a thin facade over the use cases. It is the ergonomic
pythonic surface users actually touch, so it may construct sensible default
adapters (a `QuantStatsMetricsCalculator`, a `QuantStatsTearsheetRenderer`) —
but every one of them must be overridable through constructor injection so
tests and advanced users can swap them.

Surface to provide:

```python
AlgoSystem(calculator=None, repository=None, renderer=None)
  .backtest(data, benchmark=None, start=None, end=None,
            initial_capital=None, price_column=None) -> BacktestResult
  .tearsheet(result, output="tearsheet.html", title=..., mode="html") -> Path
  .save(result, name=..., description=..., hyperparameters=None) -> RunId
  .load(run_id) -> BacktestResult
  .compare(run_ids) -> pd.DataFrame
  .print_summary(result, detailed=False) -> None
```

Plus a module-level `run_backtest(data, benchmark=None, **kwargs)` convenience
function returning a `BacktestResult`.

`print_summary` keeps the existing `rich` table output from `api.py`'s
`print_results`, driven off `MetricKey.label()` rather than the current
hardcoded label list. `rich` belongs in `interfaces/`, never below it.

Delete `AlgoSystem.export_to_db` — it called `engine.export_to_db(db_url,
table_name)`, a method `Engine` never had, so it raised `AttributeError` on
every call (SPEC §6). `.save()` replaces it. Keep `AlgoSystem.export_data`
(CSV/Excel export of the equity and time series) — it is small, it works, and
it is genuinely useful; move it onto the facade and have it take a
`BacktestResult`.

Retain the old static-method entry points (`AlgoSystem.run_backtest(...)` etc.)
as deprecated classmethods delegating to the instance API, emitting
`DeprecationWarning`. Existing PyPI users must not break.

## Job D — Tests

`tests/backtesting/application/` — one file per use case, all using the
in-memory repository and the fake calculator from Phase 2. These are the tests
that prove the composition works; they must be fast and require nothing
external.

`tests/interfaces/test_api.py` — the facade, with injected fakes. Assert the
deprecated static methods still work and warn.

`tests/backtesting/infrastructure/test_quantstats_tearsheet.py` — renders a
real tearsheet to a `tmp_path`, asserts the file exists and is non-trivial,
and asserts no matplotlib window was opened (check the backend is still `Agg`
and that `plt.show` was not called — monkeypatch it and assert).

Rewrite `tests/test_api_complete.py` against the new facade.

## Acceptance criteria

1. `grep -rn "quantstats" algosystem/` matches only the two adapter modules.
2. `grep -rn "rich\|click" algosystem/backtesting/ algosystem/marketdata/`
   returns nothing.
3. No use case imports anything from `infrastructure/`.
4. Application tests run with no database, no network, and no quantstats.
5. `python -m pytest tests/ -q` — real numbers, no new failures.
6. black + isort clean.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-4"`.

In `deviations`, note anything about the quantstats tearsheet API that did not
fit the port cleanly. In `followups`, list what Phase 5 must do to the CLI.
