# Integrating `riley-opt` into AlgoSystem

Companion to `.codex/SPEC.md`. Everything in SPEC still applies — this document
only adds the rules specific to the new **validation** bounded context.

---

## 1. What is on `riley-opt`, and what we are actually taking

`origin/riley-opt` is an **orphan branch** — `git merge-base main origin/riley-opt`
returns nothing. It has one commit, `d6bc1ae`, by John Riley
<john.p.riley1287@gmail.com>, and 203 files. It cannot be merged; it must be
harvested.

Of those 203 files:

- `AlgoSys/algosystemv2/algosystemv2/` also contains a **complete stale fork of
  AlgoSystem itself** — pre-restructure `engine.py`, `metrics.py`, `api.py`,
  `connectors/`. Bringing any of it across would undo the entire DDD
  restructure. **It is excluded in full.**
- Working-directory junk: `AlgoLens/`, a checked-in `.zip`, `__pycache__/`,
  `.coverage`. Excluded.
- `AlgoSys/algosystemv2/algosystemv2/overfitting/` — **6,621 lines** of
  permutation-based overfitting detection. This is the payload.
- `AlgoSys/algosystemv2/tests/overfitting/` — **943 lines** across 9 test files.
  Taken in full.
- `AlgoSys/algosystemv2/OVERFITTING_DETECTION.md` — the user guide. Taken and
  rewritten against the new API.

The payload has been staged at `.codex/incoming/AlgoSys/algosystemv2/`
(gitignored). **Read from there, not from git.**

## 2. Why this integrates cheaply

The `overfitting/` package is almost perfectly standalone. Its complete set of
non-relative runtime imports is:

```
numpy, scipy.stats, itertools, math, json, os, time, webbrowser,
multiprocessing, dataclasses, typing
```

There is **no pandas**, and every reference to `algosystemv2` is in a docstring
or an `__main__` example, never in a runtime import. matplotlib and plotly are
imported *lazily, inside functions*, never at module scope.

So the work is not "make it run" — it already runs. The work is **laying it out
along the DDD seams** and **bridging it to AlgoSystem's pandas-shaped domain**.

## 3. The one hard design problem

AlgoSystem's `Backtest` aggregate models an **already-computed `EquityCurve`** —
a series of values that happened. `OverfitDetector` needs the opposite: a
**re-runnable, parameterised strategy** it can invoke thousands of times against
shuffled return series.

```python
OverfitDetector(
    backtest_fn,   # (params: dict, returns: np.ndarray) -> float  (Sharpe)
    returns,       # 1-D array-like
    param_grid,    # {name: [values]} — Cartesian product
    n_reps=1000,
    shuffle_method='complete' | 'cyclic' | 'block',
)
```

There is no existing domain concept for `backtest_fn`. One must be introduced:
a **`StrategyEvaluator` port** in `validation/domain/ports.py`.

**Constraint that shapes the whole design:** `worker.py` runs passes across a
`multiprocessing.Pool`, so `backtest_fn` **must be picklable** — a module-level
function, never a lambda, closure, or bound method. The port therefore cannot be
a callable-holding object that gets pickled wholesale; the *function reference*
crosses the process boundary, and any configuration must travel as plain data
alongside it.

Phase 8 solved this by giving `StrategySpec` a `backtest_fn_path: str` — a
qualified module path resolved inside the worker — rather than a callable field.
The spec is therefore picklable by construction, and
`MultiprocessingPassRunner` pickle-probes the evaluator up front so a lambda
produces a message that names the problem instead of a raw `PicklingError`.

**Correction to an earlier draft of this document:** `strategies/_cost_wrapper.py`
does **not** already use a picklable wrapper class. `make_cost_aware()` returns
an inner `def cost_aware_backtest(...)` — a closure, which pickle cannot handle.
Under `spawn` (the default start method on Windows and macOS) any cost-aware
strategy would fail at dispatch. Converting it to a picklable callable class is
required work in Phase 9, not an existing pattern to copy.

## 4. Decisions taken (do not relitigate these)

| Question | Decision | Reason |
|---|---|---|
| `nd_visualization.py` (790 lines) | **Drop** | The only module with a hard Python `import plotly`. Phase 1 deliberately removed plotly. Its six 3-D/parallel-coordinate plots are the least load-bearing part of the payload. |
| `dashboard.py` (954 lines) | **Keep** | Despite the name, this is not the Flask dashboard that was cut. It emits one self-contained HTML file and pulls Plotly from a **CDN `<script>` tag** — it adds **no Python dependency**. It is the validation analogue of the quantstats tearsheet. |
| `visualization.py` (528 lines) | **Keep** | matplotlib only, which is already a dependency (quantstats requires it). |
| `strategies/` (366 lines) | **Keep, shipped** | These are the canonical picklable module-level `backtest_fn`s. They make the multiprocessing story work out of the box and are what the tests exercise. |
| `data_generators.py` (53 lines) | **Move to tests** | Synthetic-series helpers; test scaffolding, not library surface. |
| `signal_analyzer.py` (506 lines) | **Keep** | Pure numpy; no dependency cost. |
| Validation metrics in `MetricKey`? | **No — separate enum** | PBO, PSR, DSR, WFE and p-values are not performance metrics; folding them into `shared.MetricKey` would blur the contexts. A `ValidationMetricKey` lives in the validation domain and obeys the same R4 discipline within its own context. |
| `git merge` the branch? | **No** | Orphan branch, no merge base, 90% junk, contains a fork of the package it would be merged into. |

**Attribution:** John Riley wrote this code. The commit that lands it must say so
in the message body, and `CHANGELOG.md` must credit him. No Claude co-author
trailer on any commit or PR (standing instruction).

## 5. Target layout

```
algosystem/validation/
  domain/
    __init__.py
    validation_metric.py   ValidationMetricKey enum — sole source of validation metric names
    strategy.py            ParameterSet, ParameterGrid, StrategySpec (frozen value objects)
    ports.py               StrategyEvaluator, PassRunner, ChartRenderer, ReportRenderer
    shufflers.py           complete_shuffle, cyclic_shuffle, block_shuffle (pure numpy)
    costs.py               CostModel + the five presets; pure cost application
    results.py             OverfitResults, PBOResults, StepwiseResults, WalkForwardResults …
                           — data only; no printing, no formatting to stdout
    statistics/
      __init__.py
      psr_dsr.py           PSR / DSR / batch DSR / TrialTracker
      cscv.py              CSCV + PBO
      stepwise.py          Romano-Wolf stepwise permutation test
      walkforward.py       walk-forward analysis + WFE
      diagnostics.py       autocorrelation + shuffle recommendation
      robustness.py        bootstrap CI, Monte-Carlo trades, alpha/beta, Kelly, regimes
      validity.py          validate_returns (was data_validation.py)
  application/
    __init__.py
    dto.py
    detect_overfitting.py  DetectOverfitting use case — orchestrates the passes
    run_walk_forward.py
    screen_signals.py      over SignalAnalyzer
    equity_curve_bridge.py ACL: EquityCurve (pandas) <-> np.ndarray returns
  infrastructure/
    __init__.py
    multiprocessing_runner.py  the ONLY module importing multiprocessing (was worker.py + detector's pool)
    sequential_runner.py       in-process PassRunner, for tests and small grids
    matplotlib_charts.py       the 8 plot_* functions behind ChartRenderer
    html_report.py             generate_overfit_dashboard behind ReportRenderer
    strategies/                momentum, mean_reversion, breakout, dual_momentum, pairs,
                               volatility, _cost_wrapper, _utils — picklable backtest_fns
  __init__.py                  published surface

tests/validation/
  domain/  application/  infrastructure/   ← the 943 lines, re-homed
  _generators.py                            ← was data_generators.py
```

## 6. Rules for this context (extend SPEC §2)

- **V1** — `algosystem/validation/domain/**` may import only stdlib, `numpy`,
  `scipy`, and `algosystem.shared`. **No pandas** (the numeric core is
  array-based by design), no matplotlib, no multiprocessing, no `webbrowser`,
  no `os`.
- **V2** — `results.report()` and every other stdout-printing method comes **out
  of the domain**. Results objects hold data and expose plain accessors;
  rendering lives in `interfaces/` or `infrastructure/`. This is R6.
- **V3** — `ValidationMetricKey` is the sole source of validation metric names,
  exactly as `MetricKey` is for performance metrics (R4). The two enums never
  merge and never import each other.
- **V4** — `algosystem.validation` and `algosystem.backtesting` may only reach
  each other through published `__init__` surfaces (existing independence
  contract), and the pandas↔numpy conversion happens in **one** place:
  `application/equity_curve_bridge.py`.
- **V5** — Any `backtest_fn` the library ships must be a module-level function
  and must stay picklable. A test must assert this by round-tripping each
  shipped strategy through `pickle.dumps`.

## 7. Public surface to add

```python
from algosystem import AlgoSystem

algo = AlgoSystem()
report = algo.detect_overfitting(
    strategy="momentum",              # or a module-level callable
    returns=equity_curve,             # EquityCurve, pd.Series or np.ndarray
    param_grid={"lookback": [10, 20, 50]},
    n_reps=1000,
)
report.p_value_unbiased
report.pbo
algo.validation_report(report, output="overfit.html")
```

CLI:

```
algosystem validate INPUT_FILE --strategy momentum --reps 1000 [--output report.html]
algosystem validate strategies          # list shipped archetypes and their grids
```

## 8. Phasing

| Phase | Scope | Prompt |
|---|---|---|
| 7 | Domain extraction: statistics core, shufflers, costs, results-as-data, `ValidationMetricKey`, tests re-homed | `.codex/phases/phase-7.md` |
| 8 | Ports, use cases, the multiprocessing/sequential runners, the pandas↔numpy ACL | `.codex/phases/phase-8.md` |
| 9 | Charts + HTML report adapters, shipped strategies, CLI, facade, import-linter contracts, docs | `.codex/phases/phase-9.md` |

Version stays at **0.1.9** throughout. Do not bump it.
