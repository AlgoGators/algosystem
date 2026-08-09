# Benchmark Guide

Benchmark aliases are declared once in the market-data domain catalog. yfinance
fetching and parquet caching live behind infrastructure ports.

## Python Usage

```python
from algosystem import AlgoSystem

sp500 = AlgoSystem.get_benchmark("sp500", start_date="2022-01-01")
aliases = AlgoSystem.list_benchmarks()
comparison = AlgoSystem.compare_benchmarks(["sp500", "nasdaq"], plot=False)
```

## CLI Usage

```bash
algosystem benchmarks
algosystem backtest strategy.csv --benchmark sp500
```

## Categories

- Stock indices: `sp500`, `nasdaq`, `djia`, `russell2000`, `vix`
- Treasury yields: `10y_treasury`, `5y_treasury`, `30y_treasury`, `13w_treasury`
- ETFs: `treasury_bonds`, `corporate_bonds`, `high_yield_bonds`, `gold`,
  `commodities`, `real_estate`
- International: `europe`, `uk`, `japan`, `china`, `emerging_markets`
- Alternative strategies: `trend_following`, `hedge_fund`, `risk_parity`,
  `momentum`, `value`, `low_vol`
- Sectors: `technology`, `healthcare`, `financials`, `energy`, `utilities`

Fetched benchmark prices are cached under the user cache directory, such as
`~/.algosystem/benchmarks` when no platform-specific cache location is available.
The package no longer ships parquet cache files.
