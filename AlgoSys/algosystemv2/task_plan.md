# Task Plan: Overfitting Detection System Improvements

## Goal
Implement 6 improvements to the permutation-based overfitting detector + comprehensive visualization showing HOW overfitting is detected visually.

## Phases

### Phase 1: Autocorrelation Detection (LOW complexity, HIGH impact)
- [ ] Create `overfitting/diagnostics.py` with `check_autocorrelation(returns)` 
- [ ] Ljung-Box test + first-order ACF + partial ACF
- [ ] Returns warning dict: {has_autocorrelation, acf_1, ljung_box_pvalue, recommended_shuffle}
- [ ] Auto-call in `OverfitDetector.run()` before permutation loop
- [ ] Print warning if complete shuffle chosen but autocorrelation detected
- **Files**: `diagnostics.py` (new), `detector.py` (modify)

### Phase 2: Analytical Deflated Sharpe Ratio (LOW complexity, MEDIUM impact)
- [ ] Add `deflated_sharpe_analytical()` to `results.py`
- [ ] Bailey/Lopez de Prado formula: DSR = Phi[(SR-SR0)*sqrt(T-1)/sqrt(1-gamma3*SR+(gamma4-1)/4*SR^2)]
- [ ] SR0 from False Strategy Theorem with Euler-Mascheroni constant
- [ ] Add MinTRL (minimum track record length) computation
- [ ] Include in report() output alongside permutation-based deflated Sharpe
- **Files**: `results.py` (modify)

### Phase 3: CSCV / Probability of Backtest Overfitting (MEDIUM complexity, MEDIUM impact)
- [ ] Create `overfitting/cscv.py` with `compute_pbo(sharpe_matrix, n_splits=10)`
- [ ] Temporal partitioning into S blocks (no shuffling — preserve time order)
- [ ] All C(S, S/2) IS/OOS combinations
- [ ] For each combo: find best IS config, compute its OOS rank
- [ ] Logit transform: lambda = log(omega/(1-omega)) where omega = (rank-0.5)/N
- [ ] PBO = P(lambda < 0) via KDE
- [ ] Integration: `OverfitDetector.run()` stores per-config Sharpe time series for CSCV
- **Files**: `cscv.py` (new), `detector.py` (modify), `results.py` (modify)

### Phase 4: Stepwise Permutation Test (MEDIUM complexity, HIGH impact)
- [ ] Create `overfitting/stepwise.py` with `stepwise_permutation_test()`
- [ ] Romano-Wolf algorithm from VarScreen manual p32
- [ ] Process best-to-worst, at each step compute max of only NOT-YET-REJECTED competitors
- [ ] FWE alpha parameter controls stopping
- [ ] Returns: passed[] array, stepwise p-values per competitor
- [ ] Add `stepwise=True, alpha=0.10` option to `OverfitDetector.__init__()`
- **Files**: `stepwise.py` (new), `detector.py` (modify), `results.py` (modify)

### Phase 5: Walk-Forward with Purging + WFE (MEDIUM complexity, MEDIUM impact)
- [ ] Create `overfitting/walkforward.py`
- [ ] `walk_forward_analysis(backtest_fn, returns, param_grid, n_splits, purge_gap)`
- [ ] Rolling window IS/OOS splits with purge gap
- [ ] Per-fold: optimize on IS, evaluate on OOS
- [ ] WFE = mean(OOS_sharpe) / mean(IS_sharpe)
- [ ] Degradation ratio per fold
- [ ] Returns WalkForwardResults with per-fold metrics
- **Files**: `walkforward.py` (new)

### Phase 6: Comprehensive Visualization Suite (MEDIUM complexity, HIGH impact)
- [ ] `plot_overfit_dashboard()` — single-figure multi-panel diagnostic
  - Panel A: Null distribution histogram with S* marked (existing, enhanced)
  - Panel B: Parameter surface heatmap (existing, enhanced)
  - Panel C: IS vs OOS degradation scatter (new)
  - Panel D: PBO logit distribution (new)
  - Panel E: Autocorrelation diagnostics (ACF/PACF bars) (new)
  - Panel F: Cumulative p-value curve — solo vs unbiased vs stepwise (new)
- [ ] Individual plot functions for each panel
- [ ] `plot_overfit_report()` — generates full HTML/PNG report
- **Files**: `visualization.py` (modify + expand)

### Phase 7: Wire into algosystemv2 (LOW complexity, MEDIUM impact)
- [ ] Add `overfit_check()` method to backtesting `Engine` class
- [ ] Add `/overfit` CLI command via click
- [ ] Connect Engine results → OverfitDetector input automatically
- **Files**: `backtesting/engine.py` (modify), `cli/commands.py` (modify)

### Phase 8: Tests for New Features
- [ ] `test_diagnostics.py` — autocorrelation detection
- [ ] `test_analytical_dsr.py` — DSR formula verification
- [ ] `test_cscv.py` — PBO computation
- [ ] `test_stepwise.py` — stepwise vs traditional comparison
- [ ] `test_walkforward.py` — walk-forward mechanics
- **Files**: `tests/overfitting/` (new test files)

## Decisions
- Stepwise test is SLOWER (re-runs permutations at each step) — make it opt-in via `stepwise=True`
- CSCV runs on the SAME data as the permutation test — no additional backtest runs needed
- Visualization dashboard uses matplotlib with 2x3 or 3x2 grid layout
- Walk-forward is a SEPARATE analysis from the permutation test — different entry point

## Risk
- Stepwise test with many competitors + many reps = O(n_competitors * n_reps * n_params) backtests
- Mitigate: add early stopping when p-value exceeds alpha (as per Masters' algorithm)
