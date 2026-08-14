# Phase 7 — Land the validation domain

Read `.codex/SPEC.md` and `.codex/RILEY-OPT-INTEGRATION.md` first. The second
document is authoritative for everything in this phase; it records decisions
that are already made and must not be relitigated.

Source material is staged at
`.codex/incoming/AlgoSys/algosystemv2/` (gitignored, not part of the package):

- `algosystemv2/overfitting/` — 6,621 lines, the payload
- `tests/overfitting/` — 943 lines across 9 files
- `OVERFITTING_DETECTION.md` — the user guide

This phase builds **`algosystem/validation/domain/`** only. Ports, use cases,
runners, charts, CLI and facade are Phases 8 and 9 — do not start them.

---

## Job A — Scaffold and the metric enum

Create `algosystem/validation/` with `domain/` and `domain/statistics/`
subpackages (`application/` and `infrastructure/` come later — create the
directories with `__init__.py` but leave them empty).

Write `validation/domain/validation_metric.py` first, before porting anything
else, because the rest of the phase must use it.

`ValidationMetricKey` is a `str`-subclassing `Enum`, modelled exactly on
`algosystem/shared/metric_key.py` — same shape, same conventions, same
docstring style. It is the **sole source of validation metric names** (rule V3).
Cover at minimum: unbiased p-value, solo p-value, PBO, PBO logit, PSR, DSR,
walk-forward efficiency, in-sample Sharpe, out-of-sample Sharpe, Sharpe
degradation, null-distribution mean/std, autocorrelation lag-1, Ljung-Box
p-value, bootstrap Sharpe CI lower/upper, Kelly fraction, alpha, beta.

Derive the exact set from the fields the ported result objects actually expose —
do not invent metrics that nothing computes, and do not omit one that does.

`ValidationMetricKey` **does not import and is not imported by**
`shared.MetricKey`. They are separate vocabularies for separate contexts.

Add `ValidationError(DomainError)` to `algosystem/shared/errors.py`, following
the existing error hierarchy exactly.

## Job B — Port the pure statistical core

Move these staged modules into the tree, unchanged in *behaviour*, restructured
per `RILEY-OPT-INTEGRATION.md` §5:

| From `overfitting/` | To |
|---|---|
| `shufflers.py` | `validation/domain/shufflers.py` |
| `costs.py` | `validation/domain/costs.py` |
| `psr_dsr.py` | `validation/domain/statistics/psr_dsr.py` |
| `cscv.py` | `validation/domain/statistics/cscv.py` |
| `stepwise.py` | `validation/domain/statistics/stepwise.py` |
| `walkforward.py` | `validation/domain/statistics/walkforward.py` |
| `diagnostics.py` | `validation/domain/statistics/diagnostics.py` |
| `robustness.py` | `validation/domain/statistics/robustness.py` |
| `data_validation.py` | `validation/domain/statistics/validity.py` |
| `signal_analyzer.py` | `validation/domain/statistics/signal_analyzer.py` |
| `results.py` | `validation/domain/results.py` |

**The numerics are John Riley's and are correct. Do not "improve" them.** Do not
change an algorithm, a default, a constant, or the sense of a comparison. If you
believe you have found a real numerical bug, leave the code alone and report it
in `followups` with a file:line citation. The only changes permitted here are
structural: import paths, module placement, the four edits below, and formatting.

### Edits that *are* required

1. **Strip I/O out of the domain (rule V2 / SPEC R6).** `results.py` — and any
   other ported module — has methods that `print()` a formatted report. Domain
   objects hold data; they do not write to stdout.

   For each such method, replace it with a pure method returning the same
   information as data (a `dict`, a `list[str]` of lines, or a frozen dataclass
   — pick whichever the caller will find easiest to render), and keep the name
   descriptive of that: `report()` that prints becomes `summary()` that returns.
   Record every rename in `deviations` so Phase 9 can wire the printing back up
   in `interfaces/`.

   Likewise remove any `import os`, `webbrowser`, file writing, or
   `os.environ`/`os.getenv` read from anything landing under `domain/`.

2. **No pandas in this context's domain (rule V1).** The core is array-based by
   design. If a ported module touches pandas, that module is misplaced — stop
   and report it rather than adding a pandas import.

3. **Error handling (SPEC R5).** Replace any `{"error": ...}` return and any
   bare `except:` with a typed raise — `ValidationError` or a more specific
   subclass you add beside it. Invariant violations raise; they do not return
   sentinel values. Chain with `raise ... from exc` where an original exception
   exists.

4. **Frozen value objects (SPEC R7).** The result dataclasses
   (`PBOResults`, `StepwiseResults`, `WalkForwardResults`, `SharpeCI`,
   `MonteCarloResults`, `AlphaBetaResult`, `KellyResult`, `RegimeResult`,
   `PSRResult`, `DSRResult`, `BatchDSRResult`, `ReturnStats`,
   `AutocorrelationDiagnostic`, `ValidationResult`, `OverfitResults`, …) become
   `@dataclass(frozen=True)`. Where a `field(default_factory=...)` holds a
   mutable container, that is fine; where code *mutates* a result after
   construction, restructure the construction site so it does not — do not
   un-freeze the dataclass to avoid the work. `TrialTracker` accumulates by
   design and stays mutable; leave it.

### Modules explicitly NOT ported in this phase

- `detector.py`, `worker.py` — orchestration; Phase 8.
- `visualization.py`, `dashboard.py` — rendering; Phase 9.
- `strategies/` — Phase 9.
- `data_generators.py` — becomes `tests/validation/_generators.py` in Job D.
- `nd_visualization.py` — **dropped permanently**, see
  `RILEY-OPT-INTEGRATION.md` §4. Do not port it, do not stub it, do not
  reference it.

## Job C — `validation/domain/__init__.py`

A curated surface with `__all__`, in the style of the other context `__init__`
files already in the tree. Export the result types, the shufflers, the cost
model and presets, `ValidationMetricKey`, and the statistics entry points
(`compute_pbo`, `stepwise_permutation_test`, `walk_forward_analysis`,
`check_autocorrelation`, `probabilistic_sharpe_ratio`, `deflated_sharpe_ratio`,
`batch_deflated_sharpe`, `validate_returns`, the `robustness` functions,
`SignalAnalyzer`).

Leave `algosystem/validation/__init__.py` and `algosystem/__init__.py` alone
this phase — the top-level surface is Phase 9's job.

## Job D — Re-home the tests

The 9 staged test files under `tests/overfitting/` are the acceptance criteria
for the port. Move them to `tests/validation/`, following the directory shape
the rest of `tests/` already uses (mirror the package layout).

- Rewrite `from algosystemv2.overfitting…` imports to the new paths.
- `data_generators.py` becomes `tests/validation/_generators.py`; update the
  importers.
- Tests that exercise `detector.py`, `strategies/` or `visualization.py` cannot
  pass yet. **Do not delete them and do not weaken them.** Mark each with
  `@pytest.mark.skip(reason="pending phase 8")` / `"pending phase 9"` and list
  every one you skipped in the report's `followups`, by test id. A test deleted
  to make a suite green is a defect; a test skipped with a named phase is a
  handoff.
- Any test asserting on printed output must be rewritten against the new
  data-returning method from Job B1.

Add a test that imports `algosystem.validation.domain` in a **subprocess** and
asserts `pandas`, `matplotlib`, `multiprocessing` and `quantstats` are absent
from that process's `sys.modules`. Follow the pattern of the existing
subprocess-based purity test added in Phase 5 — do not write an in-process
version, which skips itself once another suite has imported those modules.

## Job E — Dependency

`scipy` is used by `psr_dsr.py`, `diagnostics.py` and `results.py`. It arrives
today only as a transitive of quantstats. Declare it directly in
`[tool.poetry.dependencies]` with a floor that resolves against the existing
constraints, and re-lock.

Do not bump the project version. It stays `0.1.9`. Add the work to the
`## Unreleased` section of `CHANGELOG.md`, crediting **John Riley
<john.p.riley1287@gmail.com>** as the author of the overfitting detection code.

## Verify

Run each **once**, at the end:

```
poetry run python -m pytest tests/ -q
poetry run lint-imports
poetry run ruff check algosystem/
poetry run black --check algosystem/ tests/
poetry run python -c "import algosystem; print(algosystem.__version__)"
poetry run python -c "from algosystem.validation.domain import ValidationMetricKey; print(len(list(ValidationMetricKey)))"
```

`lint-imports` must still report all contracts kept — the new domain package
must not break the existing layer or forbidden contracts. If a contract needs a
new module listed to stay accurate, update `.importlinter`; if a contract
genuinely *breaks*, the layout is wrong — fix the layout, not the contract.

## Budget discipline

Phase 4 died from re-emitting a 30,000-line `git diff` four times.

- Never run `git diff` over the whole tree. Diff a single file if you must.
- Run each verification command once, at the end, not after every edit.
- Work the jobs in order and finish each before starting the next. If you run
  short, stop, set `status` to `"partial"`, and report exactly what landed.

## Reply

Follow SPEC §9. One JSON object, `phase` = `"phase-7"`.

- `summary` — the final `validation/domain/` shape in two sentences, and the
  size of `ValidationMetricKey`.
- `deviations` — every printing method you renamed (old name → new name), and
  every dataclass you could not freeze, with the reason.
- `followups` — every test you skipped, by test id, with its phase tag; plus any
  numerical bug you spotted and deliberately left alone.
