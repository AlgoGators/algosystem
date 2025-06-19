# Benchmark Integration Guide

AlgoSystem provides built-in support for comparing your trading strategies against market benchmarks. This guide explains how to use the benchmark features effectively.

## Table of Contents

- [Overview](#overview)
- [Available Benchmarks](#available-benchmarks)
- [Using Benchmarks in Backtests](#using-benchmarks-in-backtests)
- [Benchmark Metrics](#benchmark-metrics)
- [Working with Benchmark Data](#working-with-benchmark-data)
- [Comparing Multiple Benchmarks](#comparing-multiple-benchmarks)
- [Performance Attribution](#performance-attribution)
- [Customizing Benchmark Visualization](#customizing-benchmark-visualization)
- [Best Practices](#best-practices)

## Overview

Benchmarks allow you to:
- Compare your strategy's performance to market indices
- Calculate relative performance metrics (alpha, beta, etc.)
- Understand if your strategy outperforms the market
- Identify periods of over/underperformance

AlgoSystem can automatically fetch benchmark data using the `yfinance` package and cache it for future use.

## Available Benchmarks

AlgoSystem includes aliases for dozens of benchmarks across different asset classes:

### Stock Indices
- `sp500`: S&P 500 Index
- `nasdaq`: NASDAQ Composite
- `djia`: Dow Jones Industrial Average
- `russell2000`: Russell 2000
- `vix`: CBOE Volatility Index

### Treasury Yields
- `10y_treasury`: 10-Year Treasury Yield
- `5y_treasury`: 5-Year Treasury Yield
- `30y_treasury`: 30-Year Treasury Yield
- `13w_treasury`: 13-Week Treasury Yield

### ETFs
- `treasury_bonds`: iShares 20+ Year Treasury Bond ETF
- `corporate_bonds`: iShares iBoxx $ Investment Grade Corporate Bond ETF
- `high_yield_bonds`: iShares iBoxx $ High Yield Corporate Bond ETF
- `gold`: SPDR Gold Shares
- `commodities`: Invesco DB Commodity Index Tracking Fund
- `real_estate`: Vanguard Real Estate ETF

### International
- `europe`: EURO STOXX 50
- `uk`: FTSE 100
- `japan`: Nikkei 225
- `china`: Shanghai Composite
- `emerging_markets`: iShares MSCI Emerging Markets ETF

### Alternative Strategies
- `trend_following`: iMGP DBi Managed Futures Strategy ETF
- `hedge_fund`: HFRX Global Hedge Fund Index
- `risk_parity`: RPAR Risk Parity ETF
- `momentum`: iShares MSCI USA Momentum Factor ETF
- `value`: iShares MSCI USA Value Factor ETF
- `low_vol`: iShares MSCI USA Min Vol Factor ETF

### Sectors
- `technology`: Technology Select Sector SPDR Fund
- `healthcare`: Health Care Select Sector SPDR Fund
- `financials`: Financial Select Sector SPDR Fund
- `energy`: Energy Select Sector SPDR Fund
- `utilities`: Utilities Select Sector SPDR Fund

## Using Benchmarks in Backtests

### Via Command Line

```bash
# With benchmark alias
algosystem dashboard strategy.csv --benchmark sp500

# With benchmark file
algosystem dashboard strategy.csv --benchmark benchmark.csv

# With date range
algosystem dashboard strategy.csv --benchmark nasdaq --start-date 2022-01-01 --end-date 2022-12-31

# Force refresh benchmark data
algosystem dashboard strategy.csv --benchmark sp500 --force-refresh
```

### Via Python API

```python
import pandas as pd
from algosystem.backtesting import Engine
from algosystem.data.benchmark import fetch_benchmark_data

# Load strategy data
strategy_data = pd.read_csv('strategy.csv', index_col=0, parse_dates=True)

# Method 1: Fetch benchmark using API
benchmark_data = fetch_benchmark_data('sp500')

# Run backtest with benchmark
engine = Engine(data=strategy_data, benchmark=benchmark_data)
results = engine.run()

# Method 2: Using AlgoSystem API
from algosystem.api import AlgoSystem

# Get benchmark data
benchmark_data = AlgoSystem.get_benchmark('sp500')

# Run backtest
engine = AlgoSystem.run_backtest(data=strategy_data, benchmark=benchmark_data)
```

## Benchmark Metrics

When a benchmark is provided, AlgoSystem calculates additional metrics:

- **Alpha**: Excess return relative to the benchmark
- **Beta**: Sensitivity to benchmark movements
- **Correlation**: Correlation with benchmark returns
- **Tracking Error**: Standard deviation of the difference between strategy and benchmark returns
- **Information Ratio**: Alpha divided by tracking error
- **Capture Ratios**: Performance in up and down markets relative to benchmark

Access these metrics:

```python
metrics = results["metrics"]

alpha = metrics["alpha"]
beta = metrics["beta"]
correlation = metrics["correlation"]
tracking_error = metrics["tracking_error"]
information_ratio = metrics["information_ratio"]
upside_capture = metrics["capture_ratio_up"]
downside_capture = metrics["capture_ratio_down"]
```

## Working with Benchmark Data

### Fetching Benchmark Data

```python
from algosystem.data.benchmark import fetch_benchmark_data

# Basic usage (fetches data for last 20 years)
sp500_data = fetch_benchmark_data('sp500')

# With date range
nasdaq_data = fetch_benchmark_data(
    'nasdaq', 
    start_date='2020-01-01', 
    end_date='2022-12-31'
)

# Force refresh cached data
refreshed_data = fetch_benchmark_data('sp500', force_refresh=True)
```

### Listing Available Benchmarks

```python
from algosystem.data.benchmark import get_benchmark_list, get_benchmark_info

# Get list of available benchmarks
benchmarks = get_benchmark_list()

# Get detailed information
info = get_benchmark_info()
```

CLI method:

```bash
# List available benchmarks
algosystem benchmarks

# Show detailed information
algosystem benchmarks --info
```

### Calculating Benchmark Metrics

```python
from algosystem.data.benchmark import get_benchmark_metrics

# Get performance metrics for a benchmark
metrics = get_benchmark_metrics('sp500', start_date='2020-01-01', end_date='2022-12-31')

print(f"Total Return: {metrics['total_return']:.2%}")
print(f"Annualized Return: {metrics['annualized_return']:.2%}")
print(f"Volatility: {metrics['volatility']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
```

## Comparing Multiple Benchmarks

### Command Line

```bash
algosystem compare-benchmarks sp500 nasdaq gold --start-date 2020-01-01 --end-date 2022-12-31
```

With performance metrics:

```bash
algosystem compare-benchmarks sp500 nasdaq gold --metrics
```

Export comparison to CSV:

```bash
algosystem compare-benchmarks sp500 nasdaq gold --output-file comparison.csv
```

### Python API

```python
from algosystem.data.benchmark import compare_benchmarks

# Compare multiple benchmarks
comparison_df = compare_benchmarks(
    ['sp500', 'nasdaq', 'gold'],
    start_date='2020-01-01',
    end_date='2022-12-31'
)

# Plot comparison
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
comparison_df.plot()
plt.title('Benchmark Comparison')
plt.ylabel('Normalized Value')
plt.grid(True)
plt.show()
```

Using AlgoSystem API:

```python
from algosystem.api import AlgoSystem

# Compare with built-in plotting
comparison_df = AlgoSystem.compare_benchmarks(
    ['sp500', 'nasdaq', 'gold'],
    start_date='2020-01-01',
    end_date='2022-12-31',
    plot=True
)
```

## Performance Attribution

Break down your strategy's performance relative to a benchmark:

```python
# Calculate performance attribution
strategy_return = results["metrics"]["total_return"]
benchmark_return = metrics["benchmark_total_return"]
alpha = results["metrics"]["alpha"]
beta = results["metrics"]["beta"]

# Market contribution
market_contribution = beta * benchmark_return

# Alpha contribution
alpha_contribution = alpha

# Calculate % of return from alpha vs market
alpha_pct = alpha_contribution / strategy_return * 100
market_pct = market_contribution / strategy_return * 100

print(f"Strategy Return: {strategy_return:.2%}")
print(f"Benchmark Return: {benchmark_return:.2%}")
print(f"Return from Alpha: {alpha_contribution:.2%} ({alpha_pct:.1f}%)")
print(f"Return from Market: {market_contribution:.2%} ({market_pct:.1f}%)")
```

## Customizing Benchmark Visualization

Add benchmark comparison charts to your dashboard configuration:

```json
{
  "charts": [
    {
      "id": "benchmark_comparison",
      "type": "LineChart",
      "title": "Strategy vs Benchmark",
      "data_key": "benchmark_comparison",
      "position": {"row": 1, "col": 0},
      "config": {
        "y_axis_label": "Value"
      }
    },
    {
      "id": "relative_performance",
      "type": "LineChart",
      "title": "Relative Performance",
      "data_key": "relative_performance",
      "position": {"row": 1, "col": 1},
      "config": {
        "y_axis_label": "Relative Value"
      }
    },
    {
      "id": "benchmark_drawdown",
      "type": "LineChart",
      "title": "Benchmark Drawdown",
      "data_key": "benchmark_drawdown_series",
      "position": {"row": 2, "col": 1},
      "config": {
        "y_axis_label": "Drawdown (%)",
        "percentage_format": true
      }
    }
  ]
}
```

## Best Practices

1. **Choose relevant benchmarks**: Compare your strategy to benchmarks that represent your investment universe
   - Equity strategies → S&P 500, NASDAQ, Russell indices
   - Fixed income → Treasury bonds, corporate bonds
   - Global strategies → International indices
   - Sector-specific → Relevant sector ETFs

2. **Use multiple benchmarks**: Don't just compare to one index - use several for a more complete picture
   - Primary market benchmark (e.g., S&P 500)
   - Secondary benchmark specific to your strategy
   - Risk-free rate (Treasury yields)

3. **Match date ranges**: Make sure your benchmark date range matches your strategy data

4. **Consider risk-adjusted metrics**: Look at alpha, beta, and Sharpe ratio, not just total return

5. **Update benchmark data regularly**: Use `--force-refresh` periodically to get the latest data

6. **Analyze relative performance in different market conditions**:
   - Bull markets (strong uptrends)
   - Bear markets (significant downtrends)
   - Sideways markets (low volatility)
   - High volatility periods

7. **Use capture ratios**: Understand how your strategy performs in up vs. down markets

## Troubleshooting

### Missing yfinance Package

If you get an error about the missing yfinance package:

```
ImportError: No module named 'yfinance'
```

Install it:

```bash
pip install yfinance
```

### Benchmark Data Not Found

If you get an error about an unknown benchmark alias:

```
Unknown benchmark alias: my_benchmark. Using sp500 instead.
```

Check the list of available benchmarks:

```bash
algosystem benchmarks
```

### No Data for Date Range

If you get an error about no data in the requested date range:

```
No data available for the specified date range
```

Try:
1. Widening your date range
2. Verifying the benchmark has data for your dates
3. Using `--force-refresh` to update cached data

### Connection Issues

If you get connection errors:

```
Error fetching benchmark data: HTTP Error 429: Too Many Requests
```

Try:
1. Waiting a few minutes and trying again
2. Using cached data instead of forcing refresh
3. Using a benchmark data file instead of live fetching