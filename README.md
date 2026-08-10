# AlgoSystem

AlgoSystem is a Python library for four workflows:

- backtest a strategy price or equity series
- persist backtest runs to Postgres
- render quantstats tearsheets
- validate parameter searches for overfitting

The old custom dashboard has been removed. quantstats tearsheets are the reporting surface.

## Install

```bash
pip install algosystem
```

For development:

```bash
poetry install --with dev
```

## Five-Line Backtest

```python
import pandas as pd
from algosystem import AlgoSystem
prices = pd.read_csv("strategy.csv", parse_dates=["Date"]).set_index("Date")
result = AlgoSystem().backtest(prices, price_column="Strategy")
AlgoSystem().print_summary(result)
```

## Tearsheet

```python
algo = AlgoSystem()
result = algo.backtest(prices, price_column="Strategy")
algo.tearsheet(result, output="tearsheet.html", title="Strategy Tearsheet")
```

## Validation

```python
import pandas as pd
from algosystem import AlgoSystem
from algosystem.backtesting.domain.equity_curve import EquityCurve

prices = pd.read_csv("strategy.csv", index_col=0, parse_dates=True)
curve = EquityCurve.from_series(prices["Strategy"])
report = AlgoSystem().detect_overfitting(
    strategy="momentum",
    returns=curve,
    param_grid={"lookback": [10, 20, 50]},
    n_reps=200,
    seed=7,
)
AlgoSystem().validation_report(report, output="overfit.html")
```

## Save and Load a Run

```python
from algosystem.backtesting.infrastructure.persistence import (
    DatabaseConfig,
    PostgresBacktestRunRepository,
)

repository = PostgresBacktestRunRepository(DatabaseConfig.from_env())
algo = AlgoSystem(repository=repository)
run_id = algo.save(result, name="strategy-v1")
loaded = algo.load(run_id)
```

## CLI

```bash
algosystem backtest strategy.csv --price-column Strategy --detailed
algosystem tearsheet strategy.csv --price-column Strategy --output tearsheet.html
algosystem validate strategy.csv --strategy momentum --reps 200 --seed 7 --output overfit.html
algosystem validate-strategies
algosystem benchmarks
algosystem db save strategy.csv --price-column Strategy --name strategy-v1
```

CSV input should contain a date column and one or more numeric price/equity columns.

## Documentation

- [Installation](docs/installation.md)
- [CLI](docs/CLI_GUIDE.md)
- [Python API](docs/API_GUIDE.md)
- [Benchmarks](docs/BENCHMARK_GUIDE.md)
- [Validation](docs/VALIDATION_GUIDE.md)
