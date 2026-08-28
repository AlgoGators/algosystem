# Phase 8 — Ports, use cases, and the pass runners

Read `.codex/SPEC.md`, `.codex/RILEY-OPT-INTEGRATION.md` and
`.codex/reports/phase-7.json` first. Phase 7 landed
`algosystem/validation/domain/`; this phase makes it usable.

Remaining source material is staged at
`.codex/incoming/AlgoSys/algosystemv2/algosystemv2/overfitting/` — specifically
`detector.py` (264 lines) and `worker.py` (48 lines).

Charts, the HTML report, the shipped strategies, the CLI and the facade are
Phase 9. Do not start them.

---

## The problem this phase solves

`OverfitDetector` needs a **re-runnable parameterised strategy**:

```python
backtest_fn(params: dict, returns: np.ndarray) -> float   # a Sharpe
```

AlgoSystem's `Backtest` aggregate models the opposite — an *already-computed*
`EquityCurve`. There is no domain concept for `backtest_fn`. Introduce one.

**The constraint that shapes everything here:** `worker.py` distributes passes
across a `multiprocessing.Pool`, so `backtest_fn` must be **picklable** — a
module-level function, never a lambda, closure, or bound method. That rules out
the obvious design of a port object that wraps a callable and gets pickled
wholesale. What crosses the process boundary is the *function reference* plus
plain data. `strategies/_cost_wrapper.py` in the staging area already solves
this correctly with a picklable wrapper **class** instead of a closure — read it
before designing, and follow that pattern rather than inventing another.

## Job A — `validation/domain/strategy.py`

Frozen value objects (SPEC R7), pure, no I/O:

- `ParameterSet` — one concrete combination; a frozen mapping of name → value,
  hashable, with a stable ordering so runs are reproducible.
- `ParameterGrid` — the declaration `{name: [values]}`. Validates on
  construction: non-empty, no empty value lists, no duplicate values within a
  parameter. Exposes `combinations() -> Iterator[ParameterSet]` (the Cartesian
  product, currently done inline with `itertools.product` in `detector.py`) and
  `size` so callers can see the multiple-testing burden before committing to a
  run. Raise `ValidationError` on a grid that would produce zero combinations.
- `StrategySpec` — name, the qualified path of the `backtest_fn`, and its
  `ParameterGrid`. This is the picklable description of "what to run".

Move the Cartesian-product logic out of `detector.py` and into `ParameterGrid`;
`detector.py`'s `param_list()` becomes a thin call to it.

## Job B — `validation/domain/ports.py`

Abstract, `typing.Protocol` or ABC to match whatever
`algosystem/backtesting/domain/ports.py` already uses — **be consistent with the
existing file, do not introduce a second convention**.

- `StrategyEvaluator` — evaluates one `ParameterSet` against one returns array
  and yields a score. This is the port `backtest_fn` satisfies.
- `PassRunner` — runs N permutation passes over a grid and returns the raw
  score matrix. Two adapters in Job D: multiprocessing and sequential.
- Any port Phase 9 will need for rendering (`ChartRenderer`, `ReportRenderer`)
  may be declared here now as empty protocols, but implement nothing.

Ports declare *shapes*. No numpy computation, no I/O, no imports beyond stdlib,
numpy typing and `algosystem.shared`.

## Job C — `validation/application/`

### `equity_curve_bridge.py` — the anti-corruption layer

Rule V4: pandas↔numpy conversion happens in **exactly one module**. Nowhere
else in `validation/` may import pandas.

- `returns_from(source) -> np.ndarray` accepting `EquityCurve`, `pd.Series`,
  `pd.DataFrame` (single column), or `np.ndarray`/sequence. It must
  distinguish a **price/equity series** from a **returns series** and convert
  the former — `EquityCurve` holds levels, `OverfitDetector` wants returns.
  Getting this wrong silently produces garbage Sharpes, so make the intent
  explicit in the signature rather than guessing from the data, and cover both
  directions in tests.
- Reject non-finite values, empty series, and length-1 series with
  `ValidationError` naming the problem.
- The reverse direction if Phase 9 needs it: keep it here too.

### `detect_overfitting.py`

The `DetectOverfitting` use case — the orchestration currently inside
`detector.py`'s `run()` and `_compute_results()`, lifted out. It takes a
`StrategySpec`, a returns array, a shuffle method, `n_reps`, and a `PassRunner`;
it returns the `OverfitResults` value object Phase 7 already landed.

`detector.py`'s `os.cpu_count()`, `mp.Pool`, `time.time()` and any progress
printing do **not** come with it — those are infrastructure and Job D. The use
case orchestrates; it does not parallelise and it does not print.

Keep `OverfitDetector` itself as a **thin, documented convenience wrapper** over
this use case, with its existing constructor signature intact
(`backtest_fn`, `returns`, `param_grid`, `n_reps`, `shuffle_method`,
`block_size`) and `run()` still returning `OverfitResults`. The 943 lines of
tests drive that signature and the published guide documents it; breaking it
buys nothing. Put the wrapper in `application/`, not `domain/`.

### `run_walk_forward.py`

The `RunWalkForward` use case over `domain/statistics/walkforward.py`, same
shape: accepts a `StrategySpec` and returns `WalkForwardResults`.

### `screen_signals.py`

The `ScreenSignals` use case over `SignalAnalyzer`.

### `dto.py`

Request/response DTOs if the use cases need them, matching the style of
`algosystem/backtesting/application/dto.py`.

## Job D — `validation/infrastructure/`

### `multiprocessing_runner.py`

`worker.py` plus the pool management lifted out of `detector.py`. **This is the
only module in `algosystem/validation/` permitted to import
`multiprocessing`.** It implements `PassRunner`.

- Worker count defaults to `os.cpu_count()` but is **injectable**, and never
  computed at import time.
- A worker that raises must surface as a `ValidationError` chained from the
  original (SPEC R5) — not a swallowed exception, not a `None` in the results
  array, not a silently short result matrix.
- Guard the `if __name__ == "__main__"` / spawn-start-method problem: on
  Windows and macOS the default start method is `spawn`, so an unpicklable
  `backtest_fn` fails at dispatch. Detect that case and raise a
  `ValidationError` that says *why* — "backtest_fn must be a module-level
  function, not a lambda or closure" — rather than letting a raw
  `PicklingError` reach the user. This is the single most likely thing to bite
  someone; make the message good.

### `sequential_runner.py`

An in-process `PassRunner` doing the same work in a loop. Used by tests, by
small grids, and as the fallback when the pool cannot start. Must produce
**identical** results to the multiprocessing runner for the same seed — add a
test asserting exactly that on a small grid.

## Job E — Determinism

`n_reps=1000` permutation runs that are not reproducible are not evidence.

Thread a seed through: `DetectOverfitting` accepts an optional `seed`, derives
per-pass seeds deterministically from it, and passes them into the shufflers so
the multiprocessing and sequential runners agree. Do not use the global
`np.random` state — use `np.random.default_rng(seed)` per pass, seeded from the
parent. Add a test that the same seed produces byte-identical results across
two runs and across both runners.

If the staged `shufflers.py` signatures do not accept a generator, extend them
to accept an optional `rng` while keeping the existing positional signature
working — this is an additive change, and it is the one place in Phase 7's
ported numerics you are allowed to touch.

## Job F — Restore the stub Phase 7 left behind

Phase 7 could not port `detector.py`, so it made
`SignalAnalyzer.run_detector()` **raise `ValidationError` with a
"pending phase 8" message**. That is a deliberate, reported placeholder, not a
design decision — it is your job to remove it.

Wire `run_detector()` to the `DetectOverfitting` use case from Job C and delete
the raise. Grep `algosystem/validation/` for any other `pending phase 8` marker
before you finish; every one of them belongs to this phase. If one genuinely
cannot be resolved here, the message must be rewritten to name what actually
blocks it, and it goes in `followups` — a stub that still says "pending phase 8"
after Phase 8 is a lie in the source.

`SignalAnalyzer.visualize()` raises `pending phase 9` and stays that way. Leave
it alone.

## Job G — Un-skip

Phase 7 skipped 44 tests with `reason="pending phase 8"` — they are listed by
test id in `.codex/reports/phase-7.json`'s `followups`. Un-skip every one of
them and make them pass. If one cannot pass, it stays skipped **with the reason
rewritten to say precisely what blocks it**, and it goes in `followups`. Do not
delete a test and do not weaken an assertion to get green.

`tests/validation/domain/test_output.py::TestReport` was skipped as "pending
phase 8" but tests the domain's `summary()` methods against results a detector
run produces — it should pass once the use case exists. The three
`TestPlots` tests in the same file are Phase 9; leave those skipped.

## Verify

Run each **once**, at the end:

```
poetry run python -m pytest tests/ -q
poetry run lint-imports
poetry run ruff check algosystem/
poetry run black --check algosystem/ tests/
poetry run python -c "import algosystem, sys; assert 'multiprocessing' not in sys.modules"
```

Then one real end-to-end run, in a script, and report its numbers:

```
a small grid (~8 combinations), n_reps=50, on synthetic noise, seed fixed —
run it through BOTH runners and assert the p-values match exactly.
```

`lint-imports` must report all contracts kept.

## Budget discipline

Never run `git diff` over the whole tree — Phase 4 died that way. Run each
verification command once, at the end. Finish each job before starting the next;
if you run short, stop, set `status` to `"partial"`, and report what landed.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-8"`.

- `summary` — the port/adapter shape in two sentences, and the end-to-end
  numbers from the run above.
- `deviations` — anything about the picklability constraint that forced a design
  you would not otherwise have chosen.
- `followups` — every test still skipped, by test id, with what blocks it.
