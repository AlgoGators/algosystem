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
