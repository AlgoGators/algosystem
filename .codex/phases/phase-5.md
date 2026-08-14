# Phase 5 — Market data context, CLI, and enforcing the architecture

Read `.codex/SPEC.md` and `.codex/reports/phase-4.json` first.

Last phase. The market-data context gets the same treatment as backtesting, the
CLI becomes a thin adapter, and the architectural rules stop depending on
everyone's good intentions and start being checked by CI.

---

## Job 0 — Fix `PerformanceMetrics.get()` first (small, do it before anything else)

`get()` accepts only a `MetricKey` and crashes on a plain string with an error
that tells the user nothing:

```
>>> result.metrics.get("sharpe_ratio")
AttributeError: 'str' object has no attribute 'value'
```

`MetricKey` subclasses `str`, `__getitem__("sharpe_ratio")` works, and
`"sharpe_ratio" in metrics` works — so passing a string to `get()` is the
obvious thing to write and it is the one accessor that breaks. Everything else
on the value object is fine; this is a one-method fix.

Make `get()` accept `Union[MetricKey, str]`: pass `MetricKey` through, resolve
strings via `MetricKey(...)` and `LEGACY_ALIASES`, and raise a clear
`KeyError`/`ValueError` naming the unknown key and listing valid ones for
anything unrecognised. No `DeprecationWarning` on this path — unlike
`__getitem__`, string access here is a supported convenience, not a legacy
shim. Add tests covering `MetricKey`, canonical string, legacy alias, and
unknown key.

## Job A — `algosystem/marketdata/`

`benchmark.py` (455 lines) is currently one module doing four jobs: a hardcoded
alias table, yfinance fetching, parquet caching, and category metadata. It also
runs `os.makedirs(BENCHMARK_DIR, exist_ok=True)` at **import time**
(`benchmark.py:21`) — importing the library creates a directory on the user's
disk. That must stop.

Split it:

- `domain/benchmark.py` — `Ticker` (validated symbol value object), `Benchmark`
  (alias, ticker, description, category), and `BenchmarkCatalog` holding the
  ~35 aliases currently in `BENCHMARK_ALIASES` plus the category groupings from
  `get_benchmark_info`. Today those two structures are declared separately and
  can disagree; make the catalog the single declaration and derive both the
  alias lookup and the category listing from it. Lookup of an unknown alias
  raises `UnknownBenchmarkError` listing near-matches.
- `domain/ports.py` — `BenchmarkProvider` (`fetch(ticker, date_range) ->
  pd.Series`) and `BenchmarkCache` (`get`/`put`/`has`).
- `infrastructure/yfinance_provider.py` — the only module permitted to import
  yfinance. Network failures raise `MarketDataError` chained from the original.
- `infrastructure/parquet_cache.py` — the parquet caching, with the storage
  directory **passed in**, not computed at import. Default it lazily to
  `platformdirs`-style user cache or `~/.algosystem/benchmarks`, created on
  first write, never on import.

  **Resolve this name collision while you are here.** Phase 3 left
  `algosystem/marketdata/` containing *both* a `benchmark.py` module and a
  `benchmark/` directory holding ~35 checked-in `.parquet` files. The module
  currently wins the import race, but the arrangement is fragile and the cached
  market data should never have been inside the package or shipped in the
  wheel. Move those parquet files out to the user cache directory (or delete
  them and let the cache refill on demand — they are reproducible), remove the
  `benchmark/` directory from the package, and make sure nothing in
  `pyproject.toml`'s package data still references it. Verify afterwards that
  `import algosystem.marketdata.benchmark` still resolves to a module and not a
  namespace package.
- `application/fetch_benchmark.py` — `FetchBenchmark(provider, cache)`,
  cache-then-fetch, returning an `EquityCurve`.

Keep the public helpers working: `get_benchmark_list()`, `get_benchmark_info()`,
`fetch_benchmark_data()`, `compare_benchmarks()`, and `DEFAULT_BENCHMARK` are
used by the CLI and the facade. Re-export them from `algosystem.marketdata` with
the same signatures, implemented over the new pieces.

## Job B — `interfaces/cli/`

`cli/commands.py` was 1,451 lines; Phase 1 cut the dashboard commands out of it.
What remains should become thin click handlers over use cases — parse arguments,
call a use case, format output. No business logic, no metric calculation, no
file-format knowledge beyond reading the input.

Commands to provide:

- `algosystem backtest INPUT_FILE` — run a backtest from a CSV. Options:
  `--benchmark` (alias or file), `--start`, `--end`, `--initial-capital`,
  `--price-column`, `--detailed`. Prints the rich summary.
- `algosystem tearsheet INPUT_FILE` — backtest, then render a quantstats
  tearsheet. Options: `--output`, `--title`, `--mode {html,full,basic}`,
  `--benchmark`, plus the date/capital options above. Opens the file in a
  browser only with `--open`.
- `algosystem benchmarks` — list available benchmark aliases as a rich table.
- `algosystem db save INPUT_FILE --name ...` — backtest and archive.
- `algosystem db list` / `db show RUN_ID` / `db compare RUN_ID...` /
  `db delete RUN_ID` / `db init` — over the repository.

Input loading (CSV → DataFrame, date-column detection) is shared across
commands: put it in one `cli/loaders.py` helper, not copy-pasted per command.
`load_dotenv()` is called **here**, in the CLI entry point, if at all — never in
the library (Phase 3 established this).

Update the `[tool.poetry.scripts]` entry in `pyproject.toml` to the new module
path.

## Job C — Enforce the rules mechanically

Rules that only exist in a document decay. Make them checkable.

Add `import-linter` as a dev dependency and configure contracts in
`pyproject.toml` (or `.importlinter`):

- **Layers contract**: `algosystem.interfaces` → `algosystem.*.application` →
  `algosystem.*.domain`, with `algosystem.*.infrastructure` allowed to depend on
  `domain` but nothing depending on `infrastructure` except `interfaces` and the
  composition root.
- **Forbidden contract**: `algosystem.backtesting.domain` and
  `algosystem.marketdata.domain` may not import `quantstats`, `yfinance`,
  `sqlalchemy`, `psycopg2`, `matplotlib`, `flask`, `click` or `rich`.
- **Independence contract**: `algosystem.backtesting` and
  `algosystem.marketdata` do not import each other's internals — only their
  published `__init__` surfaces.

Add a `lint-imports` step to `.github/workflows/` alongside the existing checks,
and a `make check` / script target running `black --check`, `isort --check`,
`ruff`, `lint-imports` and `pytest` together.

Note: `pyproject.toml`'s `[tool.ruff]` uses the deprecated top-level `select`
key, which newer ruff versions reject — move it to `[tool.ruff.lint]` while you
are in there. Ruff's `line-length` is 88 while black's is 100; reconcile to 100.

## Job D — Public API and docs

`algosystem/__init__.py` — a real, curated public surface with `__all__`:

```python
from algosystem import (
    AlgoSystem, run_backtest,
    Backtest, BacktestResult, EquityCurve, PerformanceMetrics,
    MetricKey, Money, Percent, Ratio, RunId, DateRange,
    AlgoSystemError, DomainError, RepositoryError, MarketDataError,
)
```

Plus `__version__`. Importing it must not import quantstats, yfinance,
sqlalchemy or matplotlib — keep the heavy adapters lazy so `import algosystem`
stays fast. Verify this with a test asserting those modules are absent from
`sys.modules` after a fresh import.

That test must run in a **subprocess**, not in the shared pytest session.
Phase 2 added an in-process version of this check at
`tests/backtesting/domain/test_equity_curve.py:26` which skips itself whenever
the adapter suite has already imported quantstats — so in a normal full-suite
run it never actually asserts anything. Replace it with a
`subprocess.run([sys.executable, "-c", ...])` check that imports into a clean
interpreter and asserts on that process's `sys.modules`. A guard that silently
skips is worse than no guard, because it reads green.

Rewrite `README.md` around the three things the library now does. The current
README documents the dashboard heavily; all of that is gone. Show: a five-line
backtest, a tearsheet, and saving/loading a run. Update `docs/` to match and
delete the pages describing removed features. Delete the stale root-level
scripts `main.py`, `test.py` and `troubleshoot.py` if they reference removed
functionality — check first.

Bump the version in `pyproject.toml` to `0.2.0` and write a `CHANGELOG.md`
entry covering the removals, the deprecations and the new API. Be explicit that
the dashboard is gone and that quantstats tearsheets replace it.

## Acceptance criteria

1. `lint-imports` passes with all three contracts.
2. `python -c "import algosystem, sys; assert 'quantstats' not in sys.modules
   and 'yfinance' not in sys.modules and 'sqlalchemy' not in sys.modules"`
   succeeds.
3. `python -c "import algosystem"` creates no directories anywhere.
4. `algosystem --help` and every subcommand's `--help` work.
5. `python -m pytest tests/ -q` — real numbers, no new failures.
6. black + isort + ruff clean.
7. No file in `algosystem/` mentions the dashboard, Flask, or PPTX.

## Budget discipline — read this before you start

The Phase 4 run exhausted its turn budget and died without reporting, because
it kept re-running `git diff` to review its own work and re-emitted the same
30,000-line diff four times. Do not do that.

- Never run `git diff` on the whole tree. If you must inspect a change, diff a
  single file.
- Run each verification command **once**, at the end, not after every edit.
- This is the largest remaining phase. Work through the jobs in order and
  finish each before starting the next, so that if you do run short, the work
  that landed is coherent and the report reflects reality.
- If you sense you are running low, stop early, set `status` to `"partial"`,
  and report precisely what is done and what is not. A truthful partial report
  is far more useful than dying mid-verification.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-5"`.

In `summary`, state the final structure in one or two sentences. In `followups`,
list everything a human should do before releasing 0.2.0 — migrations, docs, and
anything you could not verify.
