# Python API Reference

## Quick Start

```python
import pandas as pd
from algosystem.api import quick_backtest

# Load data and run backtest
data = pd.read_csv('strategy.csv', index_col=0, parse_dates=True)
engine = quick_backtest(data)
```

## High-Level API

### AlgoSystem Class

```python
from algosystem.api import AlgoSystem

# Run backtest
engine = AlgoSystem.run_backtest(
    data=strategy_data,
    benchmark=benchmark_data,
    start_date='2022-01-01',
    end_date='2022-12-31'
)

# Print results
AlgoSystem.print_results(engine, detailed=True)

# Generate dashboard
dashboard_path = AlgoSystem.generate_dashboard(
    engine,
    output_dir='./dashboard',
    open_browser=True
)

# Export data
csv_path = AlgoSystem.export_data(engine, 'results.csv')
chart_paths = AlgoSystem.export_charts(engine, './charts')
```

## Engine-Level API

### Basic Usage

```python
from algosystem.backtesting import Engine

# Create engine
engine = Engine(
    data=strategy_data,
    benchmark=benchmark_data,
    start_date='2022-01-01',
    end_date='2022-12-31',
    initial_capital=100000
)

# Run backtest
results = engine.run()

# Access results
print(f"Total Return: {results['returns']:.2%}")
print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
```

### Dashboard Generation

```python
# Interactive dashboard
dashboard_path = engine.generate_dashboard(
    output_dir='./dashboard',
    open_browser=True,
    config_path='my_config.json'
)

# Standalone dashboard
standalone_path = engine.generate_standalone_dashboard(
    output_path='./dashboard.html'
)
```

### Database Export

```python
# Export to database (requires PostgreSQL setup)
run_id = engine.export_db(
    name="My Strategy",
    description="Momentum strategy",
    hyperparameters={"window": 20, "threshold": 0.02}
)
```

## Configuration Management

```python
# Load configuration
config = AlgoSystem.load_config()

# Customize
config["layout"]["title"] = "Custom Dashboard"
config["metrics"].append({
    "id": "custom_metric",
    "type": "Percentage",
    "title": "Custom Return",
    "value_key": "total_return",
    "position": {"row": 0, "col": 3}
})

# Save configuration
AlgoSystem.save_config(config, "custom_config.json")

# Use in dashboard
dashboard_path = AlgoSystem.generate_dashboard(
    engine,
    config_path="custom_config.json"
)
```

## Data Handling

### Input Formats

```python
# Series input
strategy_series = pd.Series(prices, index=dates)
engine = Engine(strategy_series)

# DataFrame input (specify column)
strategy_df = pd.DataFrame({'Strategy': prices}, index=dates)
engine = Engine(strategy_df, price_column='Strategy')

# Multi-column DataFrame (auto-select first column)
single_col_df = strategy_df[['Strategy']]
engine = Engine(single_col_df)
```

### Benchmark Data

```python
from algosystem.data.benchmark import fetch_benchmark_data

# Fetch specific benchmark
sp500_data = fetch_benchmark_data('sp500')

# Custom date range
nasdaq_data = fetch_benchmark_data(
    'nasdaq',
    start_date='2022-01-01',
    end_date='2022-12-31'
)

# Force refresh
fresh_data = fetch_benchmark_data('sp500', force_refresh=True)
```

## Results Access

### Metrics

```python
results = engine.run()
metrics = results['metrics']

# Performance metrics
total_return = metrics['total_return']
sharpe_ratio = metrics['sharpe_ratio']
max_drawdown = metrics['max_drawdown']

# Benchmark metrics (if benchmark provided)
alpha = metrics.get('alpha')
beta = metrics.get('beta')
correlation = metrics.get('correlation')
```

### Time Series Data

```python
# Get plot data
plots = engine.get_plots()

# Access time series
equity_curve = plots['equity_curve']
drawdown_series = plots['drawdown_series']
rolling_sharpe = plots['rolling_sharpe']
monthly_returns = plots['monthly_returns']
```

## Advanced Usage

### Multiple Strategy Comparison

```python
strategies = {
    'Strategy A': pd.read_csv('strategy_a.csv', index_col=0, parse_dates=True),
    'Strategy B': pd.read_csv('strategy_b.csv', index_col=0, parse_dates=True),
    'Strategy C': pd.read_csv('strategy_c.csv', index_col=0, parse_dates=True),
}

results = {}
for name, data in strategies.items():
    engine = AlgoSystem.run_backtest(data)
    results[name] = engine.get_metrics()
    print(f"{name}: {results[name]['sharpe_ratio']:.2f}")
```

### Custom Analysis

```python
from algosystem.analysis.performance import calculate_returns_stats
from algosystem.analysis.risk import calculate_risk_metrics

# Get returns
returns = strategy_data.pct_change().dropna()

# Calculate custom metrics
return_stats = calculate_returns_stats(returns)
risk_metrics = calculate_risk_metrics(returns)

print(f"Skewness: {return_stats['skewness']:.2f}")
print(f"VaR 95%: {risk_metrics['var_95']:.2%}")
```

## Database Integration

```python
from algosystem.data.connectors.db_manager import DBManager

# Initialize database manager
db = DBManager()

# Create tables (first time only)
db.create_backtest_table()

# Export backtest
run_id = engine.export_db(name="Test Strategy")

# Query backtests
backtests = db.get_backtest_names()
comparison = db.compare_backtests([run_id1, run_id2])
best = db.find_best_backtest(metric="sharpe_ratio", limit=5)
```

## Example Workflows

### Complete Analysis

```python
import pandas as pd
from algosystem.api import AlgoSystem

# 1. Load data
strategy_data = pd.read_csv('strategy.csv', index_col=0, parse_dates=True)
benchmark_data = AlgoSystem.get_benchmark('sp500')

# 2. Run backtest
engine = AlgoSystem.run_backtest(
    data=strategy_data,
    benchmark=benchmark_data,
    start_date='2022-01-01'
)

# 3. Analyze results
AlgoSystem.print_results(engine, detailed=True)

# 4. Generate outputs
dashboard_path = AlgoSystem.generate_dashboard(engine)
data_path = AlgoSystem.export_data(engine, 'analysis.csv')
chart_paths = AlgoSystem.export_charts(engine, './charts')

# 5. Database storage
run_id = engine.export_db(name="Production Strategy")
```

### Custom Dashboard

```python
# Create custom configuration
config = {
    "metrics": [
        {
            "id": "total_return",
            "type": "Percentage",
            "title": "Total Return",
            "value_key": "total_return",
            "position": {"row": 0, "col": 0}
        }
    ],
    "charts": [
        {
            "id": "equity_curve",
            "type": "LineChart",
            "title": "Portfolio Value",
            "data_key": "equity_curve",
            "position": {"row": 1, "col": 0}
        }
    ],
    "layout": {
        "max_cols": 2,
        "title": "Custom Dashboard"
    }
}

# Use configuration
AlgoSystem.save_config(config, "custom.json")
dashboard_path = AlgoSystem.generate_dashboard(
    engine,
    config_path="custom.json"
)
```