# AlgoSystem CLI Benchmark Integration Guide

This guide covers how to use the updated AlgoSystem CLI with integrated benchmark support. The new features allow you to:

1. Use standard benchmark aliases instead of having to download benchmark data files
2. Automatically download and cache benchmark data for future use
3. Compare multiple benchmarks
4. Generate reports with benchmark comparisons

## Available Benchmarks

The system now includes a wide range of benchmark aliases representing different asset classes:

- **Stock indices**: `sp500`, `nasdaq`, `djia`, `russell2000`, `vix`
- **Treasury yields**: `10y_treasury`, `5y_treasury`, `30y_treasury`, `13w_treasury`
- **ETFs**: `treasury_bonds`, `corporate_bonds`, `high_yield_bonds`, `gold`, `commodities`, `real_estate`
- **International**: `europe`, `uk`, `japan`, `china`, `emerging_markets`
- **Alternative strategies**: `trend_following`, `hedge_fund`, `risk_parity`, `momentum`, `value`, `low_vol`
- **Sectors**: `technology`, `healthcare`, `financials`, `energy`, `utilities`

## Command Reference

### Listing Available Benchmarks

```bash
# List all available benchmarks
algosystem benchmarks

# Show detailed information about all benchmarks
algosystem benchmarks --info
```

### Fetching Benchmark Data

```bash
# Fetch data for a specific benchmark
algosystem benchmarks sp500

# Fetch data for a specific benchmark with date range
algosystem benchmarks sp500 --start-date 2020-01-01 --end-date 2023-12-31

# Force refresh of cached data
algosystem benchmarks sp500 --force-refresh

# Fetch all available benchmarks
algosystem benchmarks --fetch-all
```

### Comparing Benchmarks

```bash
# Compare multiple benchmarks
algosystem compare-benchmarks sp500 nasdaq gold

# Compare with date range
algosystem compare-benchmarks sp500 nasdaq gold --start-date 2020-01-01 --end-date 2023-12-31

# Compare with detailed metrics
algosystem compare-benchmarks sp500 nasdaq gold --metrics

# Export comparison data to CSV
algosystem compare-benchmarks sp500 nasdaq gold --output-file comparison.csv
```

### Using Benchmarks in Dashboard Generation

```bash
# Generate dashboard with specific benchmark
algosystem dashboard strategy.csv --benchmark sp500

# Generate dashboard with date range
algosystem dashboard strategy.csv --benchmark sp500 --start-date 2020-01-01 --end-date 2023-12-31

# Generate standalone dashboard with benchmark
algosystem dashboard strategy.csv --benchmark nasdaq --output-file standalone.html

# Force refresh benchmark data when generating dashboard
algosystem dashboard strategy.csv --benchmark sp500 --force-refresh
```

The same options also work with the `render` command:

```bash
algosystem render strategy.csv --benchmark gold --output-dir ./my_dashboard
```

### Running Test with Simulated Data

```bash
# Quick test with simulated data and S&P 500 benchmark
algosystem test

# Test with custom settings
algosystem test --periods 500 --benchmark nasdaq --output-dir ./test_results --open-browser
```

## Behind the Scenes

The benchmark functionality works by:

1. Downloading benchmark data using the yfinance package
2. Storing the data in parquet format in a cache directory
3. Reading from cache on subsequent runs, unless --force-refresh is used

Benchmark data is automatically aligned with your strategy data by date, so you don't need to worry about date matching.

## Installation Requirements

To use the benchmark functionality, you need to install the `yfinance` package:

```bash
pip install yfinance
```

## Default Behavior

If you don't specify a benchmark, the system will automatically use the S&P 500 (`sp500`) as the default benchmark.

## Tips for Effective Benchmarking

1. **Choose relevant benchmarks**: Compare your strategy to benchmarks that represent your investment universe
2. **Use multiple benchmarks**: Don't just compare to one index - use several to get a more complete picture
3. **Match date ranges**: Make sure your benchmark date range matches your strategy data
4. **Consider risk-adjusted metrics**: Look at alpha, beta, and Sharpe ratio, not just total return
5. **Update benchmark data regularly**: Use --force-refresh periodically to get the latest data