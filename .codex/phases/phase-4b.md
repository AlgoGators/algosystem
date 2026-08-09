# Phase 4b — Finish the facade swap

Read `.codex/SPEC.md` first. This is a short completion pass, not a new phase.

The previous run built everything in `.codex/phases/phase-4.md` but exhausted its
turn budget during verification and never finished the last step. The
application layer, the tearsheet adapter and the new facade all exist and the
suite is green. One thing is missing, and it is the thing that makes any of it
reachable.

## The situation

Two facades currently coexist:

- `algosystem/api.py` (378 lines) — the **old** one. Still what
  `from algosystem import AlgoSystem` resolves to. Its surface is the legacy
  static methods: `run_backtest`, `print_results`, `export_data`,
  `export_to_db`, `get_benchmark`, `list_benchmarks`, `compare_benchmarks`.
  It still contains the `export_to_db` method that calls
  `engine.export_to_db(...)`, which does not exist and raises `AttributeError`.
- `algosystem/interfaces/api.py` (365 lines) — the **new** one, correct and
  complete: `backtest`, `tearsheet`, `save`, `load`, `compare`,
  `print_summary`, `export_data`, plus deprecated `run_backtest` /
  `print_results` shims.

`algosystem/__init__.py` still lazily imports from `algosystem.api`, so users
get the old one and none of Phase 4's work is reachable. This is currently
provable:

```
>>> from algosystem import AlgoSystem
>>> AlgoSystem().backtest(series)
AttributeError: 'AlgoSystem' object has no attribute 'backtest'
```

## What to do

1. Rewire `algosystem/__init__.py` so `AlgoSystem`, `run_backtest` and
   `quick_backtest` resolve to `algosystem.interfaces.api`. Keep the existing
   lazy `__getattr__` pattern — importing `algosystem` must not pull in
   quantstats, sqlalchemy, yfinance or matplotlib.
2. Delete `algosystem/api.py`. Anything on it still worth having
   (`get_benchmark`, `list_benchmarks`, `compare_benchmarks` — the benchmark
   convenience methods) must first be carried over to
   `algosystem/interfaces/api.py`, delegating to `algosystem.marketdata`. Do not
   carry over `export_to_db`; `.save()` replaces it.
3. Update every remaining importer of `algosystem.api` — check `cli/commands.py`
   and the tests.
4. Add `AlgoSystem` and the new methods to `__all__` in
   `algosystem/__init__.py`.

## Verify, and keep it brief

Run these four checks, once each. **Do not re-run `git diff` to review your own
work** — the previous run burned its entire budget re-emitting the same diff
repeatedly and died. Make the changes, run the checks, report.

```
poetry run python -m pytest tests/ -q
poetry run python -c "from algosystem import AlgoSystem; print([m for m in dir(AlgoSystem) if not m.startswith('_')])"
poetry run python -c "import algosystem, sys; print([m for m in ('quantstats','sqlalchemy','yfinance','matplotlib') if m in sys.modules])"
poetry run python -m black algosystem/ tests/ && poetry run python -m isort algosystem/ tests/
```

Then one end-to-end smoke test proving the whole stack works — this is the
acceptance test for Phase 4 as a whole:

```python
import numpy as np, pandas as pd
from algosystem import AlgoSystem
idx = pd.date_range("2021-01-01", periods=900, freq="B")
rng = np.random.default_rng(42)
s = pd.Series(100*np.cumprod(1+rng.normal(0.0006, 0.011, 900)), index=idx)
algo = AlgoSystem()
res = algo.backtest(s)
p = algo.tearsheet(res, output="/tmp/ts.html", title="Smoke")
# assert the file exists, is >10KB, and matplotlib's backend is still Agg
```

If the tearsheet call fails, fix it — a working quantstats tearsheet is the
entire reporting story for this library and Phase 4 is not done without it.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-4b"`. In `summary`, state
whether the end-to-end smoke test passed and how large the generated tearsheet
was. Keep `files_modified` short — this is a small change.
