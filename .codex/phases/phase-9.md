# Phase 9 — Reporting, strategies, CLI, and the public surface

Read `.codex/SPEC.md`, `.codex/RILEY-OPT-INTEGRATION.md` and
`.codex/reports/phase-8.json` first. Phases 7 and 8 landed the validation
domain, ports, use cases and runners. This phase makes it something a user can
actually reach.

Remaining staged source at
`.codex/incoming/AlgoSys/algosystemv2/algosystemv2/overfitting/`:
`visualization.py` (528), `dashboard.py` (954), `strategies/` (366), and
`.codex/incoming/AlgoSys/algosystemv2/OVERFITTING_DETECTION.md`.

`nd_visualization.py` is **dropped permanently** (`RILEY-OPT-INTEGRATION.md` §4).
Do not port it, stub it, or reference it anywhere — including in docs.

---

## Job A — `validation/infrastructure/strategies/`

Port `strategies/` — `momentum`, `mean_reversion`, `breakout`, `dual_momentum`,
`pairs`, `volatility`, plus `_cost_wrapper.py` and `_utils.py`.

These are the canonical `backtest_fn` implementations and the thing that makes
the multiprocessing story work out of the box.

### `_cost_wrapper.py` is broken for multiprocessing — fix it as you port it

An earlier version of the Phase 8 prompt claimed this module already used a
picklable wrapper class. **That was wrong**, and Phase 8 correctly reported it.
`make_cost_aware()` returns an inner `def cost_aware_backtest(params, returns)`
— a **closure**, which `pickle` cannot serialise. Under the `spawn` start method
(the default on Windows and macOS) every cost-aware strategy would fail at
dispatch inside `MultiprocessingPassRunner`.

Convert it to a **picklable callable class**: a module-level class holding
`cost_per_trade` and `strategy_name` as plain data, with `__call__(self, params,
returns)` doing what the closure did. Same numerics, same public signature for
`make_cost_aware()` — it just returns an instance instead of a closure.

Then prove it: the pickle round-trip test below must cover a **cost-wrapped**
strategy, not only the bare ones. This is the exact failure the guard in
`MultiprocessingPassRunner._raise_if_unpicklable` was written to catch, so a
cost-wrapped strategy that trips that guard is a shipped landmine.

Two hard requirements:

- **Every shipped `backtest_fn` stays picklable** — a module-level function, or
  a module-level callable class instance. Never a lambda, closure, or bound
  method.
- Add a test that round-trips **each** shipped strategy — bare and cost-wrapped
  — through `pickle.dumps`/`pickle.loads`, then evaluates it and asserts the
  result matches the unpickled original. Rule V5.

Expose a registry — name → `StrategySpec` (function plus its default
`ParameterGrid`) — so the CLI and facade can resolve `strategy="momentum"` to
something runnable. The parameter grids are already declared in the staged
`strategies/__init__.py`; move them into the registry rather than re-typing
them.

Do not change the strategy numerics. They are John Riley's and they are what the
tests assert against.

### Two stubs Phase 7 left for you

Phase 7 could not port the strategy and chart modules, so it replaced two
working functions with `raise ValidationError("pending phase 9")`. These are
reported placeholders, not decisions. Remove both:

- `wrap_backtest_with_costs()` in `validation/domain/costs.py` — it raises
  because the staged implementation imported `strategies/_utils.py`, which had
  not landed. Now that it has, restore the real implementation. Note that this
  puts a `domain → infrastructure` import in front of you: **do not add it.**
  Either the helper it needs is pure and belongs in the domain beside it, or the
  wrapper itself belongs in `infrastructure/strategies/`. Pick one and say which
  in `deviations`; do not break the layers contract to make it compile.
- `SignalAnalyzer.visualize()` in
  `validation/domain/statistics/signal_analyzer.py` — same situation, and the
  same constraint: a domain object cannot import matplotlib. Move the rendering
  to the `ChartRenderer` adapter and have `visualize()` either move out of the
  domain or return the data a renderer needs.

Then grep `algosystem/validation/` for `pending phase` and confirm zero matches
remain. A stub still claiming to be pending after the last phase is a lie in the
source.

## Job A2 — Move `SignalAnalyzer` out of the domain

**This is a real architecture violation, not a style preference. Fix it before
anything else in this phase.**

`algosystem/validation/domain/statistics/signal_analyzer.py` currently does:

```python
detect_module = import_module("algosystem.validation.application.detect_overfitting")
runner_module = import_module("algosystem.validation.infrastructure.sequential_runner")
runner_module = import_module("algosystem.validation.infrastructure.multiprocessing_runner")
```

A **domain** module reaching up into **application** and **infrastructure**.
That is SPEC R2 violated outright. It reports clean only because import-linter
resolves static `import` statements and cannot see a string passed to
`import_module` — so the contract says KEPT while the dependency is real. Phase
8's report described this as "lazy resolution ... without adding import-time
domain dependencies"; laziness changes *when* the coupling happens, not
*whether* it exists.

`SignalAnalyzer` is not a domain object. It selects a runner, orchestrates a
detector run, and caches results across calls — that is a use case. Move it:

- The orchestrating class moves to
  `algosystem/validation/application/signal_analyzer.py`, with the runner
  **injected** through its constructor like `DetectOverfitting` already is, not
  chosen internally by `import_module`.
- Any genuinely pure statistics it carries stay in
  `domain/statistics/`, imported downward in the normal way.
- `SignalAnalysisReport` is a frozen result object; it belongs in the domain.
- Update `screen_signals.py`, the domain and application `__init__` surfaces,
  and the tests.

Then add a **guard test** so this cannot silently return: assert that no file
under `algosystem/*/domain/` contains `import_module`, `__import__`, or
`importlib`. Static contracts plus one dynamic-import ban is what actually keeps
the layer honest.

### The same evasion exists a second time — fix it too

`algosystem/validation/application/detect_overfitting.py:140,143`:

```python
def _build_runner(self) -> PassRunner:
    if self.n_workers == 1:
        runner_module = import_module("algosystem.validation.infrastructure.sequential_runner")
        ...
    runner_module = import_module("algosystem.validation.infrastructure.multiprocessing_runner")
```

An **application** module reaching into **infrastructure**, hidden from the
contract the same way. The `DetectOverfitting` use case itself is clean — it
takes an injected `PassRunner` and is a good design. The offender is the
`OverfitDetector` convenience wrapper sharing the file: choosing a concrete
adapter is *composition*, and composition does not belong in the application
layer.

Fix it by moving the choice to where it is allowed, not by hiding it better:

- Add a `default_pass_runner(evaluator, n_workers)` factory in
  `validation/infrastructure/`, which may name both adapters with ordinary
  static imports.
- Move `OverfitDetector` to a module that is permitted to touch infrastructure —
  the composition root, alongside the other facade wiring. Its published
  constructor signature and `run()` behaviour must not change; the 943 lines of
  ported tests and the user guide both depend on them, and it must stay
  importable from `algosystem.validation`.

After both fixes, `algosystem/validation/domain/` and
`algosystem/validation/application/` must contain **zero** `import_module`
calls that name another layer. `_strategy_loader.py`'s `import_module` is
different and stays — it resolves a caller-supplied `backtest_fn_path`, which is
the whole point of the picklable-spec design, not a layer bridge.

If you find any other `import_module` call bridging layers anywhere in
`algosystem/`, fix it the same way and list it in `deviations`. Note that the
lazy `import_module` calls in `backtesting/__init__.py`,
`backtesting/infrastructure/__init__.py` and `marketdata/infrastructure/__init__.py`
are **not** violations — they defer vendor imports to keep `import algosystem`
fast, and they point downward or sideways. Leave them alone.

## Job B — `validation/infrastructure/matplotlib_charts.py`

Port `visualization.py`'s eight functions behind the `ChartRenderer` port:
`plot_null_distribution`, `plot_parameter_sensitivity`, `plot_surface_2d`,
`plot_overfit_dashboard`, `plot_pbo_distribution`,
`plot_walkforward_degradation`, `plot_autocorrelation`,
`plot_pvalue_comparison`.

matplotlib is already a dependency (quantstats requires it). Two rules carried
over from the tearsheet adapter — read
`algosystem/backtesting/infrastructure/quantstats_tearsheet.py` and do exactly
what it does:

- Force the `Agg` backend before rendering and **restore the user's original
  backend afterwards**. A library that leaves the caller's backend switched is
  a bug.
- Never call `plt.show()`. Close every figure you create — a test must assert
  zero leaked figures after a full render.

Keep the lazy `import matplotlib.pyplot as plt` *inside* the functions, as the
staged code already does; that is what keeps `import algosystem` fast.

## Job C — `validation/infrastructure/html_report.py`

Port `dashboard.py`'s `generate_overfit_dashboard` behind the `ReportRenderer`
port.

Note what this actually is, because the name is misleading: it emits **one
self-contained HTML file** and pulls Plotly from a **CDN `<script>` tag**. It is
not the Flask dashboard that was deleted in Phase 1, and it adds **no Python
dependency**. It is the validation analogue of the quantstats tearsheet, and it
stays.

- `webbrowser.open(...)` must not fire by default. Gate it behind an explicit
  `open_browser: bool = False`, exactly as the tearsheet adapter gates `--open`.
- Writing the file is the adapter's job; choosing the path is the caller's.
  No `os.makedirs` at import time, ever (SPEC R6, and the defect Phase 5 fixed
  in `benchmark.py`).
- The generated page requires network access to load Plotly from the CDN. Say
  so in the docstring and in the docs — a user generating a report to read on a
  plane should not be surprised.

## Job D — CLI

Add to `algosystem/interfaces/cli/`, as thin handlers in the established style —
parse arguments, call a use case, format output. No business logic.

```
algosystem validate INPUT_FILE
    --strategy NAME            shipped archetype, or module:function path
    --param  KEY=V1,V2,V3      repeatable; overrides the strategy's default grid
    --reps N                   default 1000
    --shuffle {complete,cyclic,block}
    --seed N
    --output PATH              write the HTML report
    --open                     open it in a browser
    plus the shared date/price-column options the other commands take

algosystem validate-strategies    list shipped archetypes and their default grids
```

Reuse `cli/loaders.py` for CSV loading — do not copy-paste input handling.

Printing the results is **this layer's** job. Phase 7 turned the domain's
printing methods into data-returning methods and recorded the renames in its
report; wire the rich-formatted output up here, over those methods. Read
`.codex/reports/phase-7.json`'s `deviations` for the exact list.

A 1000-rep run over a large grid takes real time. Show progress — the other
long-running commands already establish how.

## Job E — Facade and public surface

Add to `AlgoSystem` in `algosystem/interfaces/api.py`:

```python
report = algo.detect_overfitting(
    strategy="momentum",          # name, StrategySpec, or module-level callable
    returns=equity_curve,         # EquityCurve, pd.Series, or np.ndarray
    param_grid={"lookback": [10, 20, 50]},   # optional; defaults to the strategy's
    n_reps=1000,
    seed=None,
)
algo.validation_report(report, output="overfit.html")
```

Accepting an `EquityCurve` goes through `application/equity_curve_bridge.py` —
the single conversion point (rule V4). Nothing else in `validation/` imports
pandas.

Update `algosystem/__init__.py`'s curated `__all__` with the validation surface:
`ValidationMetricKey`, `OverfitResults`, `ParameterGrid`, `StrategySpec`,
`ValidationError`, and the top-level convenience function if you add one.

**`import algosystem` must still not import** quantstats, yfinance, sqlalchemy,
matplotlib **or multiprocessing**. The heavy validation adapters stay lazy. The
subprocess purity test from Phase 5 must be extended to cover
`multiprocessing`, and it must still run in a subprocess.

## Job F — Tidy `ValidationMetricKey`

Phase 7 landed 91 members. Several are near-duplicates of one concept:

- `acf1` / `acf_1`
- `min_trl` / `min_track_record`
- `pbo` / `prob_overfit`

Singular/plural pairs where one names a scalar and the other an array
(`solo_pvalue` / `solo_pvalues`, `unbiased_pvalue` / `unbiased_pvalues`) are
legitimate and stay. Genuine synonyms are not — collapse each to one canonical
member and update every use site. If an old name is load-bearing for a ported
result object's public field, keep it as an explicit alias in a `LEGACY_ALIASES`
mapping, exactly as `shared/metric_key.py` already does — do not keep two enum
members for one concept.

Rule V3 says this enum is the *sole* source of validation metric names; two
names for one metric defeats the point.

## Job G — Enforce it

Update `.importlinter`:

- Add `algosystem.validation` to the **layers** contract in the same position as
  the other contexts: `interfaces` → `application` → `domain`, with
  `infrastructure` depending on `domain` only.
- Add `algosystem.validation.domain` to the **forbidden** contract, and forbid
  `pandas`, `matplotlib`, `multiprocessing` and `webbrowser` there specifically
  (rule V1). Note that `pandas` is forbidden in *this* domain but not in
  `backtesting.domain` — that asymmetry is deliberate.
- Add `algosystem.validation` to the **independence** contract so it and
  `backtesting`/`marketdata` only meet at published `__init__` surfaces.

All contracts must report kept. If one breaks, the layout is wrong — fix the
layout, not the contract.

## Job H — Docs

- Rewrite the staged `OVERFITTING_DETECTION.md` as `docs/VALIDATION_GUIDE.md`
  against the new API. Every example must be one you have actually run. Delete
  the sections describing `nd_visualization`'s 3-D and parallel-coordinate
  plots — that module is gone.
- Add validation to `README.md` as a fourth thing the library does, in the same
  register as the existing three: a short, working example.
- `CHANGELOG.md` `## Unreleased` — describe the validation context and credit
  **John Riley <john.p.riley1287@gmail.com>** as the author of the overfitting
  detection code.
- The version stays **`0.1.9`**. Do not bump it.

## Job I — Un-skip

Phase 7 and 8 left tests skipped with `reason="pending phase 9"`. Un-skip every
one and make it pass. Anything that still cannot pass keeps its skip with the
reason rewritten to say exactly what blocks it, and goes in `followups`. Do not
delete a test and do not weaken an assertion to reach green.

## Acceptance criteria

1. `lint-imports` — all contracts kept, including the three new validation ones.
2. `python -c "import algosystem, sys; assert not {'quantstats','yfinance','sqlalchemy','matplotlib','multiprocessing'} & sys.modules.keys()"`
3. `python -c "import algosystem"` creates no directories anywhere.
4. `algosystem validate --help` and `algosystem validate-strategies` both work.
5. A real end-to-end run: load a CSV, `--strategy momentum --reps 200 --seed 7
   --output report.html`, twice — identical p-values, report written, no
   browser opened, matplotlib backend unchanged afterwards, zero leaked figures.
   Report the file size and the p-values.
6. Every shipped strategy survives a pickle round-trip.
7. `pytest -q`, ruff, black, isort all clean.
8. No file in `algosystem/` mentions `nd_visualization`, plotly-as-a-Python-
   import, or `algosystemv2`.

## Budget discipline

Never run `git diff` over the whole tree — Phase 4 died that way. Run each
verification command once, at the end. This is a large phase: finish each job
before starting the next, so a short run still leaves coherent work. If you run
low, stop, set `status` to `"partial"`, and report precisely what is done.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-9"`.

- `summary` — the shipped validation surface in two sentences, plus the
  acceptance-criterion-5 numbers.
- `deviations` — anything you could not do as specified.
- `followups` — everything a human should check before this is called done,
  including anything you could not exercise (a live Postgres, a real CSV of
  someone's returns, a slow full-scale 1000-rep run).
