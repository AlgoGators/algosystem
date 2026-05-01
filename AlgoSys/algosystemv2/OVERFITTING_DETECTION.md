# Overfitting Detection System — Technical Reference

## Table of Contents

1. [What Problem This Solves](#what-problem-this-solves)
2. [Architecture Overview](#architecture-overview)
3. [Layer 1: Permutation-Based Detection (VarScreen/RANSAC)](#layer-1-permutation-based-detection)
4. [Layer 2: Analytical Corrections (jsharpe / Bailey-LdP)](#layer-2-analytical-corrections)
5. [Layer 3: Cross-Validation (PBO / CSCV)](#layer-3-cross-validation)
6. [Layer 4: Walk-Forward Analysis](#layer-4-walk-forward-analysis)
7. [Layer 5: Robustness Checks](#layer-5-robustness-checks)
8. [Layer 6: N-Dimensional Visualization](#layer-6-n-dimensional-visualization)
9. [Layer 7: Trial Tracking (VARRD-Inspired)](#layer-7-trial-tracking)
10. [How the Verdict Is Synthesized](#how-the-verdict-is-synthesized)
11. [Visual Signatures of Overfitting](#visual-signatures-of-overfitting)
12. [API Reference](#api-reference)
13. [Open-Source Lineage](#open-source-lineage)

---

## What Problem This Solves

When you backtest a trading strategy, you search over a parameter grid — lookback windows, thresholds, weights. The more combinations you test, the better your "best" result will look, **even on pure noise**. This is the multiple testing problem, also called p-hacking or data snooping.

**Example:** Test 100 parameter combos on random data. The best one will have a Sharpe of ~0.5-0.8 just by luck. If you didn't know it was random, you'd think you found an edge.

This system answers one question: **"Is this strategy's performance real, or is it the inevitable winner of a lottery?"**

It combines two complementary approaches:

1. **VarScreen/RANSAC** (Timothy Masters) — Permutation-based empirical p-values that directly simulate the null hypothesis by shuffling returns
2. **Bailey/Lopez de Prado** (jsharpe, PBO libraries) — Analytical corrections using Deflated Sharpe Ratio, Probabilistic Sharpe Ratio, and Combinatorially Symmetric Cross-Validation

Neither approach alone is sufficient. Permutation tests are assumption-free but computationally expensive. Analytical corrections are fast but assume specific distributional properties. Together, they cross-validate each other.

---

## Architecture Overview

```
INPUT                           DETECTION                      OUTPUT
─────                           ─────────                      ──────
                           ┌─── Permutation Test ──────┐
                           │    (VarScreen/RANSAC)      │──→ Unbiased p-value
                           │    Solo + Unbiased p-vals  │──→ Prob of overfitting
backtest_fn(params, ret)   │    Stepwise (Romano-Wolf)  │──→ Per-param significance
         +                 │                            │
    returns array          ├─── Analytical (jsharpe) ───┤──→ PSR (vs zero)
         +                 │    PSR, DSR, MinTRL        │──→ DSR (vs expected max)
    param_grid             │    Batch DSR               │──→ Min track record
         │                 │                            │
         ▼                 ├─── CSCV / PBO ─────────────┤──→ P(backtest overfit)
  OverfitDetector.run()    │    (Bailey et al. 2015)    │──→ Logit distribution
         │                 │                            │
         ▼                 ├─── Walk-Forward ───────────┤──→ WFE score
  SignalAnalyzer.analyze() │    IS/OOS with purging     │──→ Per-fold degradation
         │                 │                            │
         ▼                 ├─── Robustness ─────────────┤──→ Bootstrap CI
  Visualization            │    Bootstrap, Kelly, etc.  │──→ Alpha/Beta decomp
  (auto-routed by dims)    │                            │──→ Regime conditional
                           ├─── Surface Analysis ───────┤──→ Plateau score
                           │    Sobol indices           │──→ Robustness ratio
                           │                            │
                           ├─── Trial Tracker ──────────┤──→ Rising SR0* threshold
                           │    (VARRD-inspired)        │──→ Survivor list
                           │                            │
                           └─── N-D Visualization ──────┘──→ 3D volumes, surfaces
                                (vectorbt-style)             Parallel coordinates
                                                             Pairwise grids
```

---

## Layer 1: Permutation-Based Detection

**Origin:** Timothy Masters' VarScreen/RANSAC approach. Implemented in `detector.py`, `worker.py`, `shufflers.py`.

### How It Works

#### Step 1: Evaluate All Parameter Combinations on Real Data

Run `backtest_fn(params, returns)` for every combination in the Cartesian product of `param_grid`. Record the Sharpe ratio for each. Call the best one **S***.

```
param_grid = {
    'lookback': [10, 20, 30],
    'threshold': [0.0, 0.001, 0.002],
}
# → 9 combinations, each produces a Sharpe
# → S* = max of those 9 Sharpes
```

#### Step 2: Build the Null Distribution via Permutation

Repeat N times (default 300-1000):

1. **Shuffle** the returns array, destroying any temporal structure (and thus any real signal)
2. Run ALL parameter combos on the shuffled data
3. Record the **best** Sharpe from this shuffled pass

After N repetitions, you have N values of "best Sharpe from noise." This is the **null distribution** — what S* looks like when there is no signal.

#### Step 3: Compute P-Values

**Solo p-value** (per parameter set):
```
p_solo[i] = (1 + count(shuffled_sharpe[i] >= original_sharpe[i])) / (1 + N)
```
This asks: "For this specific parameter set, how often does noise beat it?" No multiple-testing correction.

**Unbiased p-value** (selection-bias corrected):
```
For each shuffled pass:
    Walk from worst-ranked to best-ranked param set
    Track running_max of shuffled Sharpes
    If running_max >= original Sharpe at this rank, increment count

p_unbiased[i] = count[i] / (1 + N)
```

This is the RANSAC/VarScreen algorithm. It corrects for the fact that you searched over many parameter sets and reported the best. The running-max from worst-to-best ensures that a lucky shuffled result for ANY worse-performing param set propagates upward, inflating the p-value of better-performing sets appropriately.

The "+1" in the numerator and denominator is the Phipson & Smyth (2010) correction that prevents p-values of exactly zero, which would be overconfident.

**Monotonicity enforcement:** Unbiased p-values are forced to be non-decreasing from best to worst rank. A worse-ranked parameter set can never have a smaller p-value than a better-ranked one.

#### Step 4: Probability of Overfitting

```
P(overfit) = fraction of shuffled passes where best_shuffled_Sharpe >= S*
```

If 64% of random shuffles produce a "best" Sharpe as good as yours, your result is indistinguishable from noise.

#### Step 5: Deflated Sharpe (Permutation-Based)

```
deflated_sharpe = (S* - mean(null_best_sharpes)) / std(null_best_sharpes)
```

How many standard deviations above the null your best Sharpe sits. Values > 2 suggest real signal.

### Shuffling Methods

The choice of shuffle method matters when returns have autocorrelation:

| Method | What it preserves | When to use | Implementation |
|--------|------------------|-------------|----------------|
| **Complete** | Nothing (IID) | Returns with no autocorrelation | `rng.shuffle(returns.copy())` |
| **Cyclic** | All autocorrelation | Returns with AR structure | `np.roll(returns, random_offset)` |
| **Block** | Local autocorrelation | Regime-switching data | Resample contiguous blocks of size √n |

The system auto-detects autocorrelation via the Ljung-Box test (`diagnostics.py`) and warns if `complete` shuffle is inappropriate.

### Stepwise Test (Romano-Wolf)

**Origin:** Romano & Wolf (2005), adapted by Masters. Implemented in `stepwise.py`.

Tests ALL parameter sets for significance, not just the best, while controlling the family-wise error rate (FWER).

1. Test the best-ranked param set against the full null distribution
2. If significant (p ≤ α): **reject** — this param set has real signal. Remove it from the null.
3. Recompute the null using only the remaining (non-rejected) param sets
4. Test the next-best. The null is now smaller, giving more power.
5. Repeat until a param set fails. All remaining are declared non-significant.

**Key properties:**
- Uses the SAME permuted data across all steps (same seeds, different competitor sets)
- P-values are monotonically non-decreasing (enforced)
- More powerful than Bonferroni but still controls FWER

---

## Layer 2: Analytical Corrections

**Origin:** Bailey & Lopez de Prado (2012, 2014), as implemented in the jsharpe library. Our implementation: `psr_dsr.py`, `results.py`.

### Probabilistic Sharpe Ratio (PSR)

**Question:** "What is the probability that the TRUE Sharpe exceeds a benchmark SR₀?"

Unlike a simple t-test, PSR accounts for **non-normal returns** (skewness and kurtosis), which matter enormously for real trading strategies.

**Formula:**
```
PSR = Φ[ (SR_hat - SR₀) × √(T-1) / √(1 - γ₃·SR_hat + (γ₄-1)/4 · SR_hat²) ]
```

Where:
- `SR_hat` = observed annualized Sharpe
- `SR₀` = benchmark (default: 0)
- `T` = effective sample size (autocorrelation-adjusted)
- `γ₃` = skewness of returns
- `γ₄` = raw kurtosis (normal = 3.0)
- `Φ` = standard normal CDF

**Why the denominator matters:** For leptokurtic returns (fat tails, γ₄ > 3), the denominator increases, making the z-score smaller and the PSR more conservative. Strategies with fat-tailed returns need a higher Sharpe to be considered significant — because fat tails mean more extreme outcomes by chance.

**Why not just a t-test?** A standard t-test assumes returns are normally distributed. Most trading strategies have skewed, fat-tailed returns. The PSR correction can change a "significant" t-test result into a non-significant one.

### Deflated Sharpe Ratio (DSR)

**Question:** "After accounting for ALL the strategies I tested, does the best one's Sharpe survive?"

This is PSR with SR₀ replaced by SR₀* — the expected maximum Sharpe from N independent random strategies.

**SR₀* (Expected Max Sharpe under the null):**
```
SR₀* = √(Var_SR) × [(1 - γ_EM) × Φ⁻¹(1 - 1/N) + γ_EM × Φ⁻¹(1 - 1/(N·e))]
```

Where:
- `Var_SR` = cross-sectional variance of all observed Sharpe ratios
- `γ_EM` = 0.5772... (Euler-Mascheroni constant)
- `N` = effective number of independent trials (correlation-adjusted)
- `e` = 2.71828...

This formula uses the Euler-Mascheroni approximation for E[max(Z₁,...,Z_N)] where Z_i ~ N(0, Var_SR). As N grows, SR₀* grows — making it harder for the best strategy to be "significant."

**Effective N (correlation adjustment):**
When tested strategies are correlated (e.g., overlapping parameter grids), the effective number of independent trials is less than the raw count:
```
N_eff = N / (1 + (N-1) × ρ_avg)
```
This prevents over-penalizing when many combos are essentially the same strategy.

**DSR formula:**
```
DSR = Φ[ (SR_hat - SR₀*) × √(T-1) / √(1 - γ₃·SR_hat + (γ₄-1)/4 · SR_hat²) ]
```

Interpretation:
- DSR > 0.95 → the best strategy's Sharpe is significant even after accounting for all trials
- DSR < 0.95 → the Sharpe is likely just the expected winner of a lottery

### Minimum Track Record Length (MinTRL)

**Question:** "How many observations do I need before I can trust this Sharpe?"

Solves for T in the DSR formula such that DSR = 0.95:
```
MinTRL = 1 + [1 - γ₃·SR_hat + (γ₄-1)/4 · SR_hat²] × (z₀.₉₅ / (SR_hat - SR₀*))²
```

If MinTRL = 2000 and you only have 500 observations, your Sharpe is not yet trustworthy — you need more data.

### Batch DSR

Tests multiple strategies simultaneously. Each strategy gets its own DSR computed with its own return statistics (skewness, kurtosis), but ALL strategies are penalized by the total trial count. This is the jsharpe workflow: test N strategies, see which survive the collective haircut.

---

## Layer 3: Cross-Validation

**Origin:** Bailey, Borwein, Lopez de Prado, Zhu (2015) "The Probability of Backtest Overfitting." R implementation: `pbo` package. Our implementation: `cscv.py`.

### CSCV (Combinatorially Symmetric Cross-Validation)

**Question:** "If I split my data every possible way into train/test, how often does the train-optimal strategy fail on test?"

#### Algorithm

1. **Split** T time periods into S even blocks (e.g., S=10 blocks of ~100 days each)
2. **Enumerate** all C(S, S/2) ways to pick half the blocks as in-sample (IS) and the other half as out-of-sample (OOS)
   - For S=10: C(10,5) = 252 unique IS/OOS splits
3. **For each split:**
   - Concatenate IS blocks → compute performance for ALL N strategy configurations
   - Concatenate OOS blocks → compute performance for ALL N configurations
   - Find the IS-best configuration (the one you would have picked)
   - Find the OOS rank of that IS-best configuration
4. **Compute logit:**
   ```
   ω = (rank - 0.5) / N
   logit = log(ω / (1 - ω))
   ```
   - rank=1 (best OOS) → ω small → logit very negative → this split shows no overfitting
   - rank=N (worst OOS) → ω large → logit very positive → this split shows severe overfitting
5. **PBO = P(logit > 0)** = fraction of splits where the IS-best strategy ranks below the OOS median

#### Interpretation

| PBO | Verdict |
|-----|---------|
| < 0.10 | GOOD — IS-best generalizes well across temporal splits |
| 0.10 - 0.30 | ACCEPTABLE — some temporal fragility |
| 0.30 - 0.50 | BORDERLINE — significant risk of overfitting |
| > 0.50 | LIKELY OVERFIT — IS-best consistently fails OOS |

#### Cost-Sensitivity PBO

Runs PBO at multiple transaction cost levels (0, 1, 2, 3, 5, 7, 10 bps). A strategy whose PBO jumps from 0.1 to 0.9 between 2bp and 5bp has a fragile edge that disappears under realistic costs.

---

## Layer 4: Walk-Forward Analysis

**Origin:** Standard industry practice, enhanced with purging. Implemented in `walkforward.py`.

### How It Works

1. Divide data into N folds (default 5), in time order
2. For each fold:
   - **In-sample (IS):** first 80% of the fold — optimize params here
   - **Purge gap:** remove K observations at the IS/OOS boundary (prevents lookback leakage)
   - **Out-of-sample (OOS):** remaining 20% — test the IS-winner here
3. Record IS Sharpe and OOS Sharpe per fold
4. Compute aggregate metrics

### Key Metrics

**Walk-Forward Efficiency (WFE):**
```
WFE = mean(OOS Sharpe) / mean(IS Sharpe)
```
- WFE ≥ 0.7 → EXCELLENT (strategy generalizes)
- WFE ≥ 0.5 → PASSING
- WFE ≥ 0.3 → WEAK
- WFE < 0.3 → FAILING (likely overfit)

Only computed when mean(IS Sharpe) > 0. Negative IS means no combos are profitable even in-sample.

**Degradation ratio** per fold: OOS/IS. Closer to 1.0 = better.

**Catastrophic veto:** If any fold has OOS Sharpe < -1.0, or if IS > 0.5 but OOS < -0.5 (sign flip), the strategy is vetoed regardless of other metrics.

---

## Layer 5: Robustness Checks

**Implemented in `robustness.py`.** Five independent tools, each answering a different trust question.

### 1. Bootstrap Sharpe CI

**Question:** "How precise is my Sharpe estimate?"

Resamples the returns 5,000 times with replacement, computes Sharpe on each sample, reports the 95% confidence interval. If the CI includes zero, the Sharpe is not distinguishable from a zero-skill strategy.

### 2. Monte Carlo Trade Resampling

**Question:** "Was my drawdown lucky or typical?"

Takes the actual sequence of trade PnLs, reshuffles the order 2,000 times, and builds a distribution of max drawdowns. If your actual max drawdown is at the 5th percentile of the shuffled distribution, you got unusually lucky — the next run could be much worse.

### 3. Alpha/Beta Decomposition

**Question:** "Is this just levered beta or real alpha?"

Runs OLS regression: `strategy_returns = α + β × benchmark_returns + ε`. If the t-statistic on α is < 2.0, the strategy is "just beta" — its returns are explained by market exposure, not skill.

### 4. Kelly Criterion

**Question:** "Is the edge large enough to bet on?"

From realized trade PnLs, computes:
- Win rate, average win, average loss
- Kelly fraction: f* = (p·b - q) / b
- Half-Kelly (practical bet size)
- Risk of ruin at full and half Kelly

If Kelly ≤ 0, there is no edge to exploit.

### 5. Regime-Conditional Performance

**Question:** "Does this only work in calm markets?"

Splits the data into vol regimes (low/medium/high) based on rolling realized volatility, reports Sharpe per regime. A strategy that only works in low-vol markets is fragile and will blow up when vol spikes.

---

## Layer 6: N-Dimensional Visualization

**Origin:** vectorbt volume cubes, Backtesting.py heatmaps. Implemented in `nd_visualization.py`.

The core visual insight: **overfitting = a needle (isolated spike), robustness = a broad plateau.**

### Auto-Routing by Signal Count

| Signals | Visualization | What to look for |
|---------|--------------|-----------------|
| 1 | 1D sensitivity line | Smooth curve = robust; erratic zigzag = overfit |
| 2 | 2D heatmap + 3D surface | Warm plateau = robust; single bright pixel = overfit |
| 3 | 3D volume scatter + slider surface | Green cloud = robust; isolated green dot = overfit |
| 4+ | Parallel coordinates + pairwise 3D grid | Bunched bright lines = robust; scattered lines = overfit |

### 3D Volume Scatter

Each point in 3D space is a parameter combination (x = signal1, y = signal2, z = signal3). Point size and color represent Sharpe ratio. A robust strategy appears as a cluster of large green points. An overfit strategy has one isolated green point surrounded by small red ones.

### 3D Slider Surface

Fixes one parameter to a slider value, shows the Sharpe surface across the other two. Slide to see how the landscape evolves. A robust strategy's surface stays elevated across all slider positions. An overfit strategy's surface is random and changes unpredictably.

### Parallel Coordinates

For N > 3 parameters, each vertical axis represents one parameter (plus Sharpe on the rightmost axis). Each line connects one parameter combination's values across all axes, colored by Sharpe. In a robust strategy, the bright (green) lines cluster together, passing through similar regions on each axis. In an overfit strategy, bright lines are scattered randomly.

### Pairwise 3D Grid

For N parameters, generates C(N,2) subplot surfaces — one for each pair of parameters. Shows which parameter pairs drive performance and which are noise. Clear ridges or plateaus in a subplot mean that parameter pair matters. Flat/noisy subplots mean those parameters don't influence performance.

### Surface Analysis Metrics

Computed in `results.py` `surface_analysis()`:

| Metric | What it measures | Good | Bad |
|--------|-----------------|------|-----|
| **Plateau score** | Fraction of combos with Sharpe > 70% of best | > 0.2 | < 0.05 |
| **Frac positive** | Fraction of combos with Sharpe > 0 | > 0.5 | < 0.2 |
| **Robustness ratio** | Neighbor mean / best Sharpe | > 0.8 | < 0.5 |
| **CV neighbors** | Coefficient of variation in neighborhood | < 0.3 | > 0.5 |
| **Sobol S1** | First-order sensitivity index per parameter | — | — |

**Sobol indices** tell you which parameters actually drive performance. A parameter with S1 = 0.6 explains 60% of the Sharpe variance. Parameters with S1 ≈ 0 are irrelevant — their inclusion just multiplies the number of trials, increasing the multiple-testing penalty without adding signal.

---

## Layer 7: Trial Tracking

**Origin:** VARRD platform concept. Implemented in `psr_dsr.py` `TrialTracker` class.

### The Problem

A researcher tests 10 strategies, finds nothing. Tests 10 more. Still nothing. After testing 100 strategies, one looks significant at p < 0.05. But with 100 trials, you'd expect 5 false positives at the 5% level. The researcher reports only the winner and its p-value, hiding the 99 failures.

### How the Trial Tracker Solves It

Every call to `record_trial()` logs the strategy's Sharpe and recomputes the DSR against ALL previously tested strategies. The SR₀* threshold rises with each trial:

```
Trial 1:  SR₀* = 0.00  (no penalty — first strategy tested)
Trial 10: SR₀* = 0.35  (need SR > 0.35 to be significant)
Trial 50: SR₀* = 0.58  (need SR > 0.58)
Trial 100:SR₀* = 0.72  (need SR > 0.72)
```

The `survivors()` method re-evaluates ALL recorded trials against the current (highest) SR₀* threshold. Strategies that were "significant" at trial 10 may no longer be significant at trial 100.

This makes it **nearly impossible to p-hack without the system flagging it.** Every test you run makes it harder for any result to look significant.

---

## How the Verdict Is Synthesized

The `SignalAnalyzer._synthesize_verdict()` method combines all tests via weighted voting:

| Test | Weight | Score = 1.0 if... | Score = 0.0 if... |
|------|--------|-------------------|-------------------|
| Permutation p-value | 3.0 | p < 0.05 | p ≥ 0.10 |
| Deflated Sharpe (perm) | 1.0 | DS > 2.0 | DS < 1.0 |
| DSR (analytical) | 2.0 | DSR > 0.95 | DSR ≤ 0.95 |
| PBO | 2.0 | PBO < 0.1 | PBO > 0.5 |
| Walk-Forward WFE | 2.0 | WFE ≥ 0.7 | WFE < 0.3 |
| Catastrophic veto | 3.0 | No veto | Any fold vetoed |
| Plateau score | 1.0 | > 0.2 | < 0.05 |

Weighted average produces a confidence score:

| Score | Verdict |
|-------|---------|
| ≥ 0.75 | GENUINE SIGNAL — proceed with caution |
| ≥ 0.50 | MARGINAL — needs more data or fewer parameters |
| ≥ 0.25 | LIKELY OVERFIT — high risk of curve fitting |
| < 0.25 | OVERFIT — almost certainly noise mining |

---

## Visual Signatures of Overfitting

### In the Null Distribution Plot

| Overfit | Real Edge |
|---------|-----------|
| Red line (S*) sits inside the blue histogram | Red line is far to the right of the histogram |
| p-value > 0.10 | p-value < 0.05 |
| "Your best result is typical of noise" | "Noise almost never produces results this good" |

### In the Parameter Surface

| Overfit | Real Edge |
|---------|-----------|
| Single bright pixel surrounded by dark | Broad warm region across many combos |
| Plateau score < 0.05 | Plateau score > 0.2 |
| "Only one lucky combo works" | "Most parameter choices work" |

### In the 3D Volume

| Overfit | Real Edge |
|---------|-----------|
| Scattered dots, random colors | Green cloud of clustered dots |
| No spatial pattern | Clear spatial structure |
| "Performance is random across parameter space" | "A whole region of parameter space is profitable" |

### In the Sensitivity Plot

| Overfit | Real Edge |
|---------|-----------|
| Grey lines zigzag erratically | Grey lines run parallel and smooth |
| Wide blue band (high variance) | Narrow blue band (low variance) |
| "Different threshold values disagree" | "All threshold values tell the same story" |

### In Parallel Coordinates

| Overfit | Real Edge |
|---------|-----------|
| Bright lines scattered everywhere | Bright lines bunch together |
| No common parameter region | Clear "sweet spot" on each axis |

---

## API Reference

### Quick Start

```python
from algosystemv2.overfitting import SignalAnalyzer

analyzer = SignalAnalyzer(
    backtest_fn=my_strategy,       # (params_dict, returns_array) → float
    returns=daily_returns,          # numpy array of daily returns
    signal_params={                 # parameter grid to search
        'fast_lookback': [5, 10, 15, 20],
        'slow_lookback': [30, 40, 60, 80],
        'threshold': [0.0, 0.001, 0.002],
    },
    strategy_name='dual_momentum',
    n_reps=500,                     # permutation replications
)

report = analyzer.analyze()         # runs everything
report.show()                       # prints all results
report.save('output/')              # saves plots + text report
```

### Individual Components

```python
from algosystemv2.overfitting import (
    # Core detection
    OverfitDetector,                # Permutation test engine
    # Analytical (jsharpe-style)
    probabilistic_sharpe_ratio,     # PSR
    deflated_sharpe_ratio,          # DSR
    batch_deflated_sharpe,          # Multi-strategy DSR
    TrialTracker,                   # VARRD-style trial logging
    # Cross-validation
    compute_pbo,                    # CSCV / PBO
    cost_sensitivity_pbo,           # PBO at different cost levels
    # Walk-forward
    walk_forward_analysis,          # Rolling IS/OOS
    # Robustness
    bootstrap_sharpe_ci,            # Sharpe confidence interval
    monte_carlo_trades,             # Trade sequence Monte Carlo
    alpha_beta_decomposition,       # Alpha vs beta
    kelly_criterion,                # Position sizing
    regime_conditional_performance, # Performance by vol regime
    # Visualization
    plot_null_distribution,         # Null histogram
    plot_parameter_sensitivity,     # 1D per-param
    plot_surface_2d,                # 2D heatmap
    plot_surface_3d_interactive,    # 3D Plotly slider
    plot_volume_3d,                 # 3D scatter volume
    plot_parallel_coordinates,      # N-D parallel coords
    plot_pairwise_3d_grid,          # C(N,2) pairwise surfaces
    plot_parameter_space,           # Auto-router by dim count
    plot_overfit_dashboard,         # 6-panel diagnostic
)
```

---

## Open-Source Lineage

This system draws from and extends the following open-source projects and academic papers:

### Detection & Statistical Significance

| Source | What we took | Our implementation |
|--------|-------------|-------------------|
| **jsharpe** (GitHub) | PSR and DSR formulas, multi-trial correction, MinTRL | `psr_dsr.py` — full PSR + DSR + batch + TrialTracker |
| **Probabilistic-Sharpe-Ratio** (GitHub) | Jupyter examples of simulating random strategies to show multiple-testing bias | Permutation null distribution + visualization |
| **pbo** (R package, GitHub) | CSCV algorithm for computing Probability of Backtest Overfitting | `cscv.py` — compute_pbo + cost_sensitivity_pbo |
| **backtest-engine** (GitHub) | BugGuard and CSCV modules for detecting parameter flukes | `detector.py` permutation test + `stepwise.py` Romano-Wolf |

### 3D Visualization & Math Modelers

| Source | What we took | Our implementation |
|--------|-------------|-------------------|
| **vectorbt / vectorbtpro** | Volume cube visualization, parameter sweep heatmaps | `nd_visualization.py` — plot_volume_3d, plot_surface_3d_interactive |
| **Backtesting.py** | Bokeh heatmap concept, optimization engine output | `visualization.py` plot_surface_2d + `nd_visualization.py` 3D extension |
| **Probabilistic Programming for Hackers** (PyMC) | Bayesian switchpoint analysis, distribution modeling | `robustness.py` bootstrap_sharpe_ci, regime_conditional_performance |

### Modern Platforms & Workflow

| Source | What we took | Our implementation |
|--------|-------------|-------------------|
| **VARRD** | Auto-raising significance threshold as tests accumulate | `psr_dsr.py` TrialTracker class |

### Academic Papers

| Paper | Year | Key contribution | Where used |
|-------|------|-----------------|-----------|
| Bailey & Lopez de Prado, "The Sharpe Ratio Efficient Frontier" | 2012 | PSR formula with non-normal correction | `psr_dsr.py` |
| Bailey & Lopez de Prado, "The Deflated Sharpe Ratio" | 2014 | DSR, SR₀*, MinTRL | `psr_dsr.py`, `results.py` |
| Bailey, Borwein, Lopez de Prado, Zhu, "The Probability of Backtest Overfitting" | 2015 | CSCV / PBO algorithm | `cscv.py` |
| Timothy Masters, "Permutation and Randomization Tests" | — | VarScreen/RANSAC unbiased p-values | `detector.py` |
| Romano & Wolf, "Stepwise Multiple Testing" | 2005 | Stepwise FWE control | `stepwise.py` |
| Phipson & Smyth, "Permutation P-values Should Never Be Zero" | 2010 | +1 correction for permutation p-values | `detector.py`, `stepwise.py` |
| Lo, "The Statistics of Sharpe Ratios" | 2002 | Autocorrelation adjustment for SR variance | `psr_dsr.py` n_effective |
| Politis & Romano, "The Stationary Bootstrap" | 1994 | Block bootstrap for dependent data | `shufflers.py` |
