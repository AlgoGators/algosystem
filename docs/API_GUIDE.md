# Python API Guide

## Public Surface

```python
from algosystem import (
    AlgoSystem,
    Backtest,
    BacktestResult,
    DateRange,
    EquityCurve,
    MarketDataError,
    MetricKey,
    Money,
    OverfitResults,
    ParameterGrid,
    PerformanceMetrics,
    RegimeResult,
    RepositoryError,
    StrategySpec,
    ValidationError,
    ValidationMetricKey,
    detect_overfitting,
    run_backtest,
)
```

## Backtest

```python
import pandas as pd
from algosystem import AlgoSystem

prices = pd.read_csv("strategy.csv", index_col=0, parse_dates=True)
algo = AlgoSystem()
result = algo.backtest(prices, price_column="Strategy", initial_capital=100000)
algo.print_summary(result, detailed=True)
```

## Benchmark

```python
benchmark = AlgoSystem.get_benchmark("sp500", start_date="2022-01-01")
result = algo.backtest(prices, benchmark=benchmark, price_column="Strategy")
```

## Tearsheet

```python
output = algo.tearsheet(result, output="tearsheet.html", mode="html")
```

## Validation

```python
from algosystem.backtesting.domain.equity_curve import EquityCurve

curve = EquityCurve.from_series(prices["Strategy"])
report = algo.detect_overfitting(
    strategy="momentum",
    returns=curve,
    param_grid={"lookback": [10, 20, 50]},
    n_reps=200,
    seed=7,
)
algo.validation_report(report, output="overfit.html")
```

The validation HTML report loads Plotly from a CDN when opened.

## Regimes

```python
from algosystem.backtesting.domain.equity_curve import EquityCurve

curve = EquityCurve.from_series(prices["Strategy"])
result = algo.analyze_regimes(curve)

print("\n".join(result.summary()))
print(result.works_in_all_regimes, result.worst_regime_name)
```

Classify on a benchmark instead of the strategy's own volatility by passing
`market_returns`. Both series must cover the same dates — when they carry a
`DatetimeIndex` this is checked, because regimes are assigned positionally:

```python
result = algo.analyze_regimes(curve, market_returns=benchmark_curve)
```

Options: `n_regimes` (default 3), `vol_window` (default 21), `annualize`
(default 252), and `input_kind` / `market_input_kind` (`"returns"` or
`"levels"`) for raw array and pandas input. An `EquityCurve` always holds levels
and converts automatically.

`result.to_metrics()` returns every field keyed by `ValidationMetricKey`, which
is the serialization-friendly form.

## Persistence

```python
from algosystem.backtesting.infrastructure.persistence import (
    DatabaseConfig,
    PostgresBacktestRunRepository,
)

repository = PostgresBacktestRunRepository(DatabaseConfig.from_env())
algo = AlgoSystem(repository=repository)
run_id = algo.save(result, name="strategy-v1")
loaded = algo.load(run_id)
comparison = algo.compare([run_id])
```

The default database configuration reads `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
and `DB_PASSWORD`.
