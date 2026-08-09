# AlgoSystem

AlgoSystem is a Python library for three workflows:

- backtest a strategy price or equity series
- persist backtest runs to Postgres
- render quantstats tearsheets

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
algosystem benchmarks
algosystem db save strategy.csv --price-column Strategy --name strategy-v1
```

CSV input should contain a date column and one or more numeric price/equity columns.

## Documentation

- [Installation](docs/installation.md)
- [CLI](docs/CLI_GUIDE.md)
- [Python API](docs/API_GUIDE.md)
- [Benchmarks](docs/BENCHMARK_GUIDE.md)
