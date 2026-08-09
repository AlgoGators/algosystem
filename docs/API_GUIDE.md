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
    PerformanceMetrics,
    RepositoryError,
    run_backtest,
)
```

## Backtest

```python
import pandas as pd
from algosystem import AlgoSystem

prices = pd.read_csv("strategy.csv", parse_dates=["Date"]).set_index("Date")
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
