# Phase 3 — Persistence behind a repository port

Read `.codex/SPEC.md` and `.codex/reports/phase-2.json` first.

The database currently reaches into the domain and the domain reaches back. This
phase severs that. When it is done, the entire domain test suite runs with no
Postgres anywhere, and the Postgres implementation is one swappable adapter.

---

## What is wrong today

`algosystem/data/connectors/` is 1,284 lines across six modules:

- `DBManager` composes by **inheritance**: `class DBManager(LoaderManager,
  DeleterManager, InserterManager)`, all three inheriting `BaseDBManager`. This
  is composition modelled as a diamond. Replace it with actual composition.
- `BaseDBManager.__init__` (`base_db_manager.py:20-39`) reads five environment
  variables and raises `RuntimeError` if any is missing. Constructing the object
  at all therefore requires a configured Postgres, which is why the domain is
  untestable and why `tests/test_database_mock.py` is 16 lines.
- `db_models.py:get_engine()` calls `load_dotenv()` and reads `os.getenv` at
  call time — ambient configuration.
- Two connection mechanisms coexist: SQLAlchemy (`_init_sqlalchemy`) and raw
  psycopg2 (`_connect_psycopg2`), used inconsistently across the managers.
- **`compare_backtests` (`db_manager.py:201-211`) interpolates caller-supplied
  run IDs straight into the SQL string.** This is an injection vector. Its
  siblings `find_best_backtest` and `search_backtests` guard their interpolated
  identifiers with allowlists; this one validates nothing.

## Job A — `infrastructure/persistence/config.py`

`DatabaseConfig` — a frozen dataclass: `host`, `port`, `database`, `user`,
`password`, `schema` (default `"backtest"`), `pool_size`. Validates and raises
`ConfigurationError` with a message naming exactly which field is missing.

Provide `DatabaseConfig.from_env(env: Mapping[str, str] | None = None)` as an
**explicit opt-in** classmethod reading `DB_HOST` / `DB_PORT` / `DB_NAME` /
`DB_USER` / `DB_PASSWORD`, taking the mapping as a parameter (default
`os.environ`) so tests inject a dict. No `load_dotenv()` inside the library —
if the CLI wants dotenv, the CLI calls it. Also `.url()` building the SQLAlchemy
connection string, with the password redacted in `__repr__`.

## Job B — `infrastructure/persistence/schema.py`

The SQLAlchemy models, carried over from `db_models.py`: `run_metadata`,
`equity_curve`, `results`, `final_positions`, `symbol_pnl` in the `backtest`
schema.

Two changes. First, the `results` table columns must be generated from
`MetricKey` (SPEC R4) rather than hand-listed — today `db_models.py` declares
~20 metric columns that duplicate the names in `metrics.py`, and they have
already drifted (the table has `downside_volatility`, `win_rate`,
`profit_factor`, `total_trades` which nothing computes; it lacks `sortino_ratio`
persistence parity with what is calculated). Reconcile: generate a column per
`MetricKey` member that is a scalar float, and drop the columns nothing produces.

Second, `run_id` is `BigInteger` in the ORM but `RunId.generate()` produces
`"20250115_143022_881"`, a string — and `db_manager.py` casts run ids to `str`
throughout while `create_backtest_table()` declares `BIGINT PRIMARY KEY`. This
is an existing latent bug. Make `run_id` a `String` primary key consistently
across every table and the DDL. Record it in `deviations` as a schema-breaking
change, and provide `schema.create_all(engine)` plus a short note in
`followups` about migrating an existing database.

## Job C — The adapters

### `in_memory_repository.py`

`InMemoryBacktestRunRepository` implementing the full `BacktestRunRepository`
port from `domain/ports.py`. Backed by a dict. Correct semantics, not a stub:
`get` on a missing id raises `RunNotFoundError`; `save` of a duplicate id raises
`DuplicateRunError` unless `overwrite=True`; `find_best` sorts ascending for
drawdown and volatility and descending for everything else, matching the rule
at `db_manager.py:265`; `search` does case-insensitive substring matching on the
requested field.

This is the artifact that makes everything above it testable. Give it real care.

### `postgres_repository.py`

`PostgresBacktestRunRepository` implementing the same port, constructed with a
`DatabaseConfig`. One connection mechanism only — use SQLAlchemy Core/ORM
throughout and drop the raw psycopg2 path entirely.

- **Every** query parameterized. No f-string interpolation of caller data
  anywhere, including `compare_backtests`' run-id list — use an `IN` clause with
  bound parameters or SQLAlchemy's `in_()`.
- Where an identifier genuinely must be interpolated (a sort column in
  `find_best`), resolve it through `MetricKey` and reject anything that is not a
  valid member. An enum lookup is the allowlist.
- Connections are managed with context managers and always released. Failures
  raise `RepositoryError` chained from the original via `raise ... from e`.
- Serialize `PerformanceMetrics` through `MetricKey`, never through literals.

Port the useful read methods from the old managers onto the port or as extra
methods: `get_backtest_stats`, `compare_backtests`, `get_backtest_summary`,
`get_equity_curve`. Drop anything that has no caller.

## Job D — Delete the old layer

Once the adapters are in place, delete `algosystem/data/connectors/` entirely —
`base_db_manager.py`, `db_manager.py`, `db_models.py`, `deleter_manager.py`,
`inserter_manager.py`, `loader_manager.py`. Do not leave a shim; `DBManager` was
never a documented public API. Move `algosystem/data/benchmark.py` to
`algosystem/marketdata/` untouched for now — Phase 5 restructures it — and
delete `algosystem/data/`.

Update `tests/test_engine_db_export.py` and `tests/test_database_mock.py` to
exercise the in-memory repository instead of mocking a connection.

## Acceptance criteria

1. `grep -rn "psycopg2" algosystem/` returns nothing.
2. `grep -rn "os.getenv\|load_dotenv" algosystem/` matches only
   `persistence/config.py` and the CLI.
3. No f-string or `%`-format SQL containing caller-supplied values anywhere.
   Verify by reading every query you wrote.
4. `algosystem/data/` does not exist.
5. The domain and application test suites pass with no database available.
6. `python -m pytest tests/ -q` — real numbers, no new failures.
7. black + isort clean.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-3"`.

In `deviations`, be explicit about the `run_id` type change and anything you
dropped from the old managers. In `followups`, note what a human must do to an
existing production database before this code can talk to it.
