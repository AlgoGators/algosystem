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
