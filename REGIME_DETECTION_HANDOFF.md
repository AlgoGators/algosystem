# Regime Detection — Implementation Handoff

**Branch:** `feat/regime-detection` · **Commit:** `594d202` · **Base:** `main` (`d929556`)
**Scope:** 19 files, +1345 / −3

---

## 1. What the task turned out to be

The ticket read "implement regime detection." The important discovery is that **most of it already existed.**

`algosystem/validation/domain/statistics/robustness.py` already contained
`regime_conditional_performance()` and `RegimeResult` — volatility-tercile classification
answering *"does this strategy only work in calm markets?"* It arrived with John Riley's
overfitting port in phase 7 (commit `d929556`).

But it was **dead code**:

- exported from `validation/domain/__init__.py` and referenced by nothing else in the package
- no use case, no `AlgoSystem` method, no CLI command
- zero tests
- absent from every guide

So the work was **not** "write a regime detector from scratch." It was: make the existing,
correct statistics reachable, safe to call, and tested. That framing matters — `AGENTS.md`
and `.codex/phases/phase-7.md` both forbid altering Riley's numerics.

> The alternative reading — build a *new* detector (HMM / Markov-switching) — would have been
> a multi-day design job duplicating working code. If that was actually intended, this branch
> is still the right foundation for it.

---

## 2. What was built

Wired through the existing DDD layering (`interfaces → application → domain`).

| Layer | File | Change |
|---|---|---|
| Domain | `validation/domain/statistics/robustness.py` | `RegimeResult.to_metrics()` — lossless export keyed by `ValidationMetricKey`. **+26 lines, 0 deletions — no numerics touched.** |
| Domain | `validation/domain/validation_metric.py` | Added `REGIME_COUNTS`, `WORST_REGIME_NAME`, `WORKS_IN_ALL_REGIMES` so every computed field has a canonical name (rule R4/V3). |
| Application | `validation/application/analyze_regimes.py` *(new, 199 lines)* | `AnalyzeRegimes` use case: input coercion, parameter validation, date-alignment and sufficient-data guards. |
| Interfaces | `interfaces/api.py` | `AlgoSystem.analyze_regimes()` |
| Interfaces | `interfaces/cli/main.py` | `algosystem regimes` command + rich rendering |
| Exports | `algosystem/__init__.py`, `validation/__init__.py`, `validation/application/__init__.py` | `AnalyzeRegimes`, `RegimeResult` |
| Docs | `VALIDATION_GUIDE.md`, `API_GUIDE.md`, `CLI_GUIDE.md`, `README.md`, `CHANGELOG.md` | New sections |
| Tests | 3 new files + 2 extended | **58 new test functions** |

### Design decisions worth defending

**No `facade.py` entry point.** `validation/facade.py` exists to compose *infrastructure*
(`detect_overfitting` builds a `PassRunner`, resolves strategies from
`validation.infrastructure.strategies`). `AnalyzeRegimes` composes nothing — it takes a
realized return series and calls one pure function. A facade wrapper would be a pure
pass-through.

**The CLI calls the use case directly, not `AlgoSystem`.** `AlgoSystem.__init__` eagerly
builds a quantstats metrics calculator that regime analysis never uses. Routing the CLI
around it keeps the command usable. Precedent exists — `validate-strategies` and
`benchmarks` also import their dependencies directly. *(See §6 — the underlying eagerness
is a pre-existing issue worth its own ticket.)*

**`AnalyzeRegimes` is a stateless class with one `execute`.** Effectively a namespaced
function, but it preserves the uniform `X(...).execute(...)` protocol used by
`DetectOverfitting`, `RunWalkForward`, and `ScreenSignals`.

---

## 3. What code review caught (and how it was fixed)

I put the first version through three review passes — correctness, architecture/spec
compliance, and test/doc quality. **The first pass had real defects.** All are fixed; this
section records them so the fixes can be scrutinised rather than taken on trust.

| # | Defect | Fix |
|---|---|---|
| 1 | **Silent date misalignment.** Regimes are assigned *positionally*; only series *length* was checked. A strategy dated 2020 with a benchmark dated 2010 produced confident, meaningless output — and the docs recommended exactly that call. | `_require_matching_dates()` compares the converted returns indices when both inputs carry a `DatetimeIndex`. Undated arrays still fall back to the length check. |
| 2 | **Data shortage reported as a finding.** A bucket under 5 observations scores `0.0`. A 30-row CSV printed "every regime 0.0, REGIME-DEPENDENT", exit 0 — for a strategy whose true Sharpe was ~93. | `_require_classifiable()` rejects a series no longer than `vol_window`, or too short to fill `n_regimes`, naming the fixable parameter. |
| 3 | **`nan` annualize poisoned every Sharpe silently** (`nan <= 0` is `False`). Non-integer `n_regimes` leaked a raw `TypeError` past the typed-error boundary. | Explicit finite/integer checks raising `ValidationError`. |
| 4 | **Tautological test.** `test_low_and_high_regimes_track_the_actual_volatility_break` asserted only bucket *sizes* — a third each by construction. It passed on pure IID noise with no regime structure. | Now measures realized volatility inside each bucket. Verified: **8.01×** separation on the regime fixture vs **0.97×** on IID noise. |
| 5 | **The branch was red.** `to_metrics()` was expanded from 4 keys to 7 without updating its test. | Test asserts all 7 keys plus a round-trip reconstruction of the whole `RegimeResult`. |
| 6 | **`--benchmark` was a dead end** for calendar-day files (a business-day benchmark always errored), and its happy-path test passed even with the flag ignored entirely. | Date **intersection** instead of strict reindex; added a test that runs with and without `--benchmark` and asserts the classification changes. |
| 7 | `to_metrics()` was lossy (4 of 8 fields) and had no consumer. | Added the missing enum members; the CLI now renders from it. |

Also fixed: shared test fixtures moved to `tests/validation/conftest.py`; `pytest.approx`
tolerances tightened from `1e-6` to `1e-9` (measured error is ~`1e-16`); exact float equality
on `sum(regime_frac)` replaced with `approx`; `FrozenInstanceError` used instead of a
`try/except/else`; `CLI_GUIDE.md` and `API_GUIDE.md` updated (originally missed).

---

## 4. Verification

```
python -m pytest tests/
→ 22 failed, 301 passed, 1 error in 479s
```

**All 22 failures and the 1 collection error reproduce identically on `main`.** Confirmed by
running the same selection in a clean `git worktree` at `main`. They are `quantstats` not
being installed in this environment (no poetry venv on this machine), plus one sandbox
`parquet_cache` filesystem failure. **Zero regressions.**

| Check | Result |
|---|---|
| `black --check` / `isort --check` | clean, 132 files |
| `import algosystem` under `-W error` | clean — no side effects, no warnings |
| `validation_domain_forbidden` contract | KEPT across 16 domain modules |
| Domain purity (subprocess test) | passes |
| Layering contracts R1/R2/R5/R6/R7 | verified by AST across all 90 modules |
| New tests | 58 functions, all green |

> **Environment caveat:** `ruff` and `import-linter` are not installed on this machine, so
> contracts were verified by AST analysis rather than the real tool. **CI is the authoritative
> check** — run it before merging.

---

## 5. How to demo it

### A. The script — strongest for a non-engineering audience

```bash
python examples/regime_detection_demo.py
```

Builds two strategies calibrated to the **identical** headline Sharpe of 1.62, then separates
them:

```
Strategy A (robust)  Sharpe : 1.62      Strategy B (fragile) Sharpe : 1.62
        ↓                                        ↓
  low_vol    0.3333                        low_vol    4.8624
  med_vol    3.4279                        med_vol    1.6555
  high_vol   0.8719                        high_vol  -1.3092  ← WARNING
  [ALL REGIMES]                            [REGIME-DEPENDENT]
  works_in_all_regimes = True              works_in_all_regimes = False
```

**The pitch in one screen: a tearsheet cannot tell these apart. This can.**

The script also demonstrates both guardrails rejecting bad input rather than producing
confident nonsense.

### B. The CLI — live demo, no Python

```bash
algosystem regimes strategy.csv --price-column Strategy
algosystem regimes strategy.csv --price-column Strategy --benchmark market.csv
algosystem regimes strategy.csv --price-column Strategy --regimes 4 --vol-window 63
```

**Worth knowing when demoing this.** Without `--benchmark`, regimes come from the strategy's
*own* volatility. A strategy with constant volatility but changing drift reports
`ALL REGIMES` (1.48 / 0.34 / 2.03) — its own vol cannot see the regimes. Add `--benchmark`
and the same data reads **4.44 / 2.15 / −3.05, REGIME-DEPENDENT**.

> That is the answer to "why didn't it catch it?" — classify on the **market** when asking
> whether the market's state breaks the strategy.

### C. The tests — engineering proof

```bash
python -m pytest tests/validation/ tests/test_cli.py tests/test_cli_integration.py
```

The strongest evidence that these tests are meaningful is item 4 in §3: the classification
test now fails on scrambled data. The first version of it didn't.

### D. Python API

```python
from algosystem import AlgoSystem
from algosystem.backtesting.domain.equity_curve import EquityCurve

curve = EquityCurve.from_series(prices["Strategy"])
result = AlgoSystem().analyze_regimes(curve, market_returns=benchmark_curve)

print("\n".join(result.summary()))
print(result.works_in_all_regimes, result.worst_regime_name)
print(result.to_metrics())   # keyed by ValidationMetricKey
```

---

## 6. Known gaps and follow-ups

Recording these up front rather than leaving them to surface in review.

1. **Not integrated into the HTML validation report.** `html_report.py::_add_robustness`
   already dispatches on a `robustness` mapping, and `RenderValidationReport.execute` takes
   `robustness=`. Regimes were left out **because that parameter is currently dead for all
   five robustness statistics** — wiring only regimes would be inconsistent. ~6 lines if
   wanted. *Defensible scope boundary, but expect the question.*

2. **`AlgoSystem.__init__` eagerly builds a quantstats calculator**, so `AlgoSystem()` cannot
   be constructed without quantstats even for regime analysis, which uses none of it. Worked
   around (CLI routes direct; facade tests inject `FakeMetricsCalculator`). The real fix is
   lazy adapter construction — **a pre-existing issue, deliberately out of scope here.**

3. **Thin buckets remain possible.** The sufficient-data guard is necessary, not sufficient:
   percentile thresholds can still leave a bucket under 5 observations, scored `0.0`. This is
   why `regime_counts` is exposed in `to_metrics()` — it distinguishes an empty bucket from a
   genuine loss. Documented and tested.

4. **Calendar mismatch shifts the Sharpe.** Restricting to shared dates drops observations and
   widens gaps between survivors, while `vol_window` counts observations and annualization
   stays at 252. Documented in `CLI_GUIDE.md`; no `--annualize` flag was added.

5. **Two return-coercion paths coexist.** `AnalyzeRegimes` uses the public `returns_from`;
   `run_walk_forward.py` and `screen_signals.py` use the private `_coerce_returns_array`.
   The new code picked the better one; collapsing the siblings is a follow-up.

---

## 7. Reverting

```bash
git checkout main                        # walk away, branch intact
git branch -D feat/regime-detection      # delete outright
```

Untracked helper files not in the commit: `examples/regime_detection_demo.py`, and this file.
