# AlgoSystem Python API Guide

AlgoSystem provides a comprehensive Python API for algorithmic trading backtesting and visualization. This guide covers the key components and usage patterns.

## Table of Contents

- [Installation](#installation)
- [Core Classes](#core-classes)
  - [Engine](#engine-class)
  - [AlgoSystem API](#algosystem-api-class)
- [Basic Usage](#basic-usage)
- [Backtesting](#backtesting)
- [Dashboard Generation](#dashboard-generation)
- [Working with Benchmarks](#working-with-benchmarks)
- [Exporting Results](#exporting-results)
- [Advanced Usage](#advanced-usage)
- [Use Cases](#use-cases)

## Installation

```bash
pip install algosystem
```

## Core Classes

### Engine Class

The `Engine` class is the core of AlgoSystem, handling backtesting for price-based strategies:

```python
from algosystem.backtesting import Engine

# Initialize with a price series
engine = Engine(
    data=price_series,                # pandas Series or DataFrame
    benchmark=benchmark_series,       # Optional benchmark
    start_date="2022-01-01",          # Optional date range
    end_date="2022-12-31",
    initial_capital=100000,           # Optional starting capital
    price_column="strategy"           # If using DataFrame with multiple columns
)

# Run the backtest
results = engine.run()

# Access results
print(f"Total Return: {results['returns']:.2%}")
print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
```

### AlgoSystem API Class

The `AlgoSystem` class provides a higher-level interface with more functionality:

```python
from algosystem.api import AlgoSystem, quick_backtest

# Run a backtest
engine = AlgoSystem.run_backtest(
    data=price_series,
    benchmark=benchmark_series,
    start_date="2022-01-01",
    end_date="2022-12-31"
)

# Print formatted results
AlgoSystem.print_results(engine)

# Generate dashboard
dashboard_path = AlgoSystem.generate_dashboard(
    engine,
    output_dir="./dashboard",
    open_browser=True
)
```

## Basic Usage

### Quick Backtest

The simplest way to run a backtest and see results:

```python
import pandas as pd
from algosystem.api import quick_backtest

# Load your price series data
data = pd.read_csv('strategy_prices.csv', index_col=0, parse_dates=True)

# Run backtest and print results
engine = quick_backtest(data)
```

### Loading Data

AlgoSystem works with price series data (portfolio value over time):

```python
import pandas as pd

# From CSV file
data = pd.read_csv('strategy.csv', index_col=0, parse_dates=True)

# From pandas Series
dates = pd.date_range('2022-01-01', periods=252, freq='B')
prices = pd.Series([100 * (1 + i*0.001) for i in range(252)], index=dates)

# From multi-column DataFrame
df = pd.read_csv('multi_strategy.csv', index_col=0, parse_dates=True)
strategy_data = df['Strategy1']  # Select specific column
```

## Backtesting

### Running a Backtest

```python
from algosystem.backtesting import Engine

# Initialize engine with price series
engine = Engine(data=price_series)

# Run backtest
results = engine.run()

# Access results dictionary
metrics = results["metrics"]
equity_curve = results["equity"]
drawdown = results["plots"]["drawdown_series"]

# Print key metrics
print(f"Total Return: {metrics['total_return']:.2%}")
print(f"Annualized Return: {metrics['annualized_return']:.2%}")
print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
```

### Benchmark Comparison

```python
# Load benchmark data (e.g., S&P 500)
benchmark_data = pd.read_csv('sp500.csv', index_col=0, parse_dates=True)

# Initialize engine with benchmark
engine = Engine(
    data=price_series,
    benchmark=benchmark_data
)

# Run backtest
results = engine.run()

# Access benchmark-specific metrics
alpha = results["metrics"]["alpha"]
beta = results["metrics"]["beta"]
correlation = results["metrics"]["correlation"]
information_ratio = results["metrics"]["information_ratio"]

print(f"Alpha: {alpha:.2%}")
print(f"Beta: {beta:.2f}")
```

### Date Range Filtering

```python
# Filter to specific date range
engine = Engine(
    data=price_series,
    start_date="2020-01-01",
    end_date="2020-12-31"
)
```

## Dashboard Generation

### Generating an Interactive Dashboard

```python
# Generate dashboard with default settings
dashboard_path = engine.generate_dashboard(
    output_dir="./dashboard",
    open_browser=True
)

# Or use the AlgoSystem class
from algosystem.api import AlgoSystem

dashboard_path = AlgoSystem.generate_dashboard(
    engine,
    output_dir="./dashboard",
    open_browser=True
)
```

### Generating a Standalone Dashboard

```python
# Generate a self-contained HTML file
standalone_path = engine.generate_standalone_dashboard(
    output_path="./standalone_dashboard.html"
)

# Or use the AlgoSystem class
standalone_path = AlgoSystem.generate_standalone_dashboard(
    engine,
    output_path="./standalone_dashboard.html"
)
```

### Custom Dashboard Configuration

```python
# Generate with custom configuration
dashboard_path = engine.generate_dashboard(
    output_dir="./dashboard",
    config_path="./custom_config.json"
)
```

## Working with Benchmarks

### Loading a Built-in Benchmark

```python
from algosystem.api import AlgoSystem

# Get S&P 500 benchmark
sp500_data = AlgoSystem.get_benchmark("sp500")

# Get NASDAQ benchmark for specific dates
nasdaq_data = AlgoSystem.get_benchmark(
    "nasdaq",
    start_date="2022-01-01",
    end_date="2022-12-31"
)
```

### Listing Available Benchmarks

```python
# List all available benchmark aliases
benchmarks = AlgoSystem.list_benchmarks()
```

### Comparing Multiple Benchmarks

```python
# Compare S&P 500, NASDAQ, and Gold
comparison_df = AlgoSystem.compare_benchmarks(
    ["sp500", "nasdaq", "gold"],
    start_date="2020-01-01",
    end_date="2022-12-31",
    plot=True  # Show comparison plot
)
```

## Exporting Results

### Exporting Data

```python
# Export data to CSV
csv_path = AlgoSystem.export_data(
    engine,
    output_path="./exports/backtest_data.csv",
    format="csv"
)

# Export data to Excel
excel_path = AlgoSystem.export_data(
    engine,
    output_path="./exports/backtest_data.xlsx",
    format="excel"
)
```

### Exporting Charts

```python
# Export all charts as images
chart_paths = AlgoSystem.export_charts(
    engine,
    output_dir="./plots",
    dpi=300  # Higher resolution
)
```

## Advanced Usage

### Configuration Management

```python
# Load configuration
config = AlgoSystem.load_config()

# Modify configuration
config["layout"]["title"] = "Custom Dashboard Title"
config["metrics"].append({
    "id": "custom_metric",
    "type": "Value",
    "title": "Custom Metric",
    "value_key": "sharpe_ratio",
    "position": {"row": 0, "col": 3}
})

# Save modified configuration
AlgoSystem.save_config(config, output_path="./custom_config.json")
```

### Working with Rolling Metrics

```python
# Get time series results
plots = engine.get_plots()

# Access rolling metrics
rolling_sharpe = plots["rolling_sharpe"]
rolling_sortino = plots["rolling_sortino"]
rolling_volatility = plots["rolling_volatility"]
drawdown_series = plots["drawdown_series"]

# Plot with matplotlib
import matplotlib.pyplot as plt

plt.figure(figsize=(12, 6))
plt.plot(rolling_sharpe)
plt.title("Rolling Sharpe Ratio (252 days)")
plt.show()
```

### Performance and Risk Metrics

```python
# Access computed metrics
metrics = engine.get_metrics()

# Comprehensive metrics list
performance_metrics = {
    "total_return": metrics["total_return"],
    "annualized_return": metrics["annualized_return"],
    "annualized_volatility": metrics["annualized_volatility"],
    "sharpe_ratio": metrics["sharpe_ratio"],
    "sortino_ratio": metrics["sortino_ratio"],
    "calmar_ratio": metrics["calmar_ratio"],
    "max_drawdown": metrics["max_drawdown"],
    "var_95": metrics["var_95"],  # Value at Risk
    "cvar_95": metrics["cvar_95"],  # Conditional Value at Risk
    "skewness": metrics["skewness"],
    "positive_days": metrics["positive_days"],
    "negative_days": metrics["negative_days"],
    "pct_positive_days": metrics["pct_positive_days"],
    "best_month": metrics["best_month"],
    "worst_month": metrics["worst_month"]
}

# Benchmark-specific metrics (if benchmark provided)
benchmark_metrics = {
    "alpha": metrics.get("alpha"),
    "beta": metrics.get("beta"),
    "correlation": metrics.get("correlation"),
    "tracking_error": metrics.get("tracking_error"),
    "information_ratio": metrics.get("information_ratio"),
    "capture_ratio_up": metrics.get("capture_ratio_up"),
    "capture_ratio_down": metrics.get("capture_ratio_down")
}
```

## Use Cases

### Strategy Evaluation

```python
import pandas as pd
from algosystem.api import AlgoSystem

# Load strategy data
strategy = pd.read_csv('strategy.csv', index_col=0, parse_dates=True)

# Load benchmark for comparison
benchmark = AlgoSystem.get_benchmark("sp500")

# Run backtest with benchmark comparison
engine = AlgoSystem.run_backtest(strategy, benchmark)

# Print detailed results
AlgoSystem.print_results(engine, detailed=True)

# Generate dashboard and export charts
AlgoSystem.generate_dashboard(engine)
AlgoSystem.export_charts(engine, output_dir="./strategy_analysis")
```

### Multi-Strategy Comparison

```python
import pandas as pd
from algosystem.analysis.performance import compare_strategies

# Load multiple strategy data
strategy1 = pd.read_csv('strategy1.csv', index_col=0, parse_dates=True)
strategy2 = pd.read_csv('strategy2.csv', index_col=0, parse_dates=True)
strategy3 = pd.read_csv('strategy3.csv', index_col=0, parse_dates=True)

# Run backtests
engine1 = AlgoSystem.run_backtest(strategy1)
engine2 = AlgoSystem.run_backtest(strategy2)
engine3 = AlgoSystem.run_backtest(strategy3)

# Compare strategies
comparison = compare_strategies({
    "Strategy 1": engine1.results,
    "Strategy 2": engine2.results,
    "Strategy 3": engine3.results
})

# Access comparison results
metrics_comparison = comparison["metrics"]
correlation_matrix = comparison["correlation"]
```

### Portfolio Analysis

```python
import pandas as pd
import numpy as np
from algosystem.api import AlgoSystem
from algosystem.analysis.portfolio import calculate_efficient_frontier

# Load asset price data
assets = pd.read_csv('assets.csv', index_col=0, parse_dates=True)

# Calculate returns
returns = assets.pct_change().dropna()

# Calculate efficient frontier
frontier_returns, frontier_volatilities, frontier_weights = calculate_efficient_frontier(
    returns, num_points=50
)

# Plot efficient frontier
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.scatter(frontier_volatilities, frontier_returns, c=frontier_returns/frontier_volatilities)
plt.colorbar(label='Sharpe ratio')
plt.xlabel('Volatility')
plt.ylabel('Expected Return')
plt.title('Efficient Frontier')
plt.show()
```