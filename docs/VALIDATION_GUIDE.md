# Validation Guide

AlgoSystem validation checks whether the best result from a parameter search is
likely to be real or just the winner of a noisy grid search. The validation
context uses John Riley's permutation overfitting detector, shipped strategy
archetypes, matplotlib diagnostics, and a self-contained HTML report.

The HTML report includes a CDN script tag for Plotly charts. The file is local,
but the charts need network access when you open it.

## CLI Example

```bash
algosystem validate strategy.csv --strategy momentum --reps 200 --seed 7 --output report.html
```

List shipped archetypes and their default grids:

```bash
algosystem validate-strategies
```

## Python API Example

```python
import pandas as pd
from algosystem import AlgoSystem
from algosystem.backtesting.domain.equity_curve import EquityCurve

prices = pd.read_csv("strategy.csv", index_col=0, parse_dates=True)
curve = EquityCurve.from_series(prices["Strategy"])

algo = AlgoSystem()
report = algo.detect_overfitting(
    strategy="momentum",
    returns=curve,
    param_grid={"lookback": [10, 20, 50]},
    n_reps=200,
    seed=7,
)
algo.validation_report(report, output="report.html")
```

`strategy` can be a shipped name, a `StrategySpec`, or a module-level callable.
Custom callables must have the signature `(params, returns) -> float`, where the
float is the score to maximize, usually annualized Sharpe. For multiprocessing,
the callable must be picklable: a module-level function or a picklable
module-level callable class instance.

## Shipped Strategies

The shipped archetypes are:

- `momentum`
- `mean_reversion`
- `breakout`
- `dual_momentum`
- `pairs`
- `volatility`

Each archetype has a default `ParameterGrid` in
`algosystem.validation.infrastructure.strategies.STRATEGY_REGISTRY`. The legacy
name `vol_regime` is accepted as an alias for `volatility`.

## Regime-Conditional Performance

Overfitting tests ask whether an edge is real. Regime analysis asks a different
question: *does the edge survive everywhere, or only in calm markets?*

`AnalyzeRegimes` classifies every observation into a volatility bucket using a
rolling standard deviation, then reports the Sharpe ratio earned inside each
one. It takes a realized return series, so it needs no parameter grid and no
pass runner.

```python
from algosystem import AlgoSystem
from algosystem.backtesting.domain.equity_curve import EquityCurve

curve = EquityCurve.from_series(prices["Strategy"])
result = AlgoSystem().analyze_regimes(curve)

print("\n".join(result.summary()))
print(result.works_in_all_regimes)
```

Regimes default to terciles of the strategy's own volatility (`low_vol`,
`med_vol`, `high_vol`). Pass `market_returns` to classify on a benchmark
instead, which is usually what you want when asking whether a strategy depends
on the *market's* state rather than its own:

```python
result = AlgoSystem().analyze_regimes(curve, market_returns=benchmark_curve)
```

Regimes are assigned **positionally**, so the two series must describe the same
observations. When both carry a `DatetimeIndex` this is verified and a mismatch
raises `ValidationError`; align the series yourself before calling if they sit
on different calendars. Undated input (plain arrays) can only be length-checked.

Fields on `RegimeResult`:

- `regime_names`, `regime_sharpes`, `regime_counts`, `regime_frac`: the
  per-regime breakdown, index-aligned.
- `overall_sharpe`: Sharpe across every classified observation.
- `worst_regime_name` / `worst_regime_sharpe`: where the strategy is weakest.
- `works_in_all_regimes`: `True` only when Sharpe is positive in every regime.
- `summary()`: the report as a list of lines.
- `to_metrics()`: every field keyed by `ValidationMetricKey`, losslessly.

Only the three-bucket default is named `low_vol`/`med_vol`/`high_vol`; any
other `n_regimes` names the buckets `regime_0` … `regime_N-1`.

Options: `n_regimes` (default 3), `vol_window` (default 21 observations),
`annualize` (default 252), and `input_kind` / `market_input_kind` (`"returns"`
or `"levels"`) for raw array and pandas input. An `EquityCurve` always holds
levels and is converted automatically.

### Insufficient data

The statistics degrade quietly: a bucket holding fewer than five observations is
scored `0.0` rather than skipped, which makes a data shortage read like a
finding ("Sharpe 0.0, regime-dependent"). `AnalyzeRegimes` therefore refuses
input it cannot describe — a series no longer than `vol_window`, or one too
short to fill the requested number of regimes — and raises `ValidationError`
naming the offending parameter.

That guard is necessary but not sufficient: percentile thresholds can still
leave one bucket thin. Check `regime_counts` (also carried by `to_metrics()`)
to tell an empty or thin bucket apart from a genuine loss.

From the CLI:

```bash
algosystem regimes strategy.csv --price-column Strategy
algosystem regimes strategy.csv --price-column Strategy --benchmark sp500
algosystem regimes strategy.csv --price-column Strategy --regimes 4 --vol-window 63
```

## Reading Results

Important fields on `OverfitResults`:

- `unbiased_pvalue`: selection-bias-corrected p-value for the best parameter set.
- `prob_overfit`: fraction of shuffled runs where the best shuffled Sharpe beats
  the real best Sharpe.
- `deflated_sharpe`: distance between the best real Sharpe and the permutation
  null distribution.
- `surface_analysis()`: robustness, plateau, and per-parameter sensitivity data.

Lower p-values and lower `prob_overfit` are better. A broad parameter plateau is
more trustworthy than one isolated best point.
