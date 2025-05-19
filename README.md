# 🚀 AlgoSystem

[![PyPI version](https://badge.fury.io/py/algosystem.svg)](https://badge.fury.io/py/algosystem)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-MIT-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Built with Poetry](https://img.shields.io/badge/built%20with-Poetry-purple)](https://python-poetry.org/)

**A batteries-included Python library for algorithmic trading backtesting and beautiful, interactive dashboard visualization.**

Transform your trading strategy performance analysis with professional-grade dashboards that rival institutional trading platforms.

![AlgoSystem Dashboard Preview](example/dashboard.html)

## ✨ Features

- 🔄 **Simple Backtesting**: Run backtests with just a price series
- 📊 **Interactive Dashboards**: Generate beautiful HTML dashboards with 20+ metrics and charts
- 🎨 **Visual Dashboard Editor**: Drag-and-drop interface for customizing dashboard layouts
- 📈 **Comprehensive Analytics**: Performance metrics, risk analysis, rolling statistics, and more
- 🆚 **Benchmark Comparison**: Compare strategies against market benchmarks with alpha/beta analysis
- ⚙️ **Flexible Configuration**: JSON-based system for complete dashboard customization
- 💻 **CLI Tools**: Command-line interface for quick dashboard generation
- 🌐 **Standalone Dashboards**: Export self-contained HTML files that work offline

## 📦 Installation

### Quick Install (Recommended)

```bash
pip install algosystem
```

### Requirements

- Python 3.9 or newer
- Core dependencies: pandas, numpy, matplotlib
- All other dependencies are installed automatically

## 🚀 Quick Start

### Command Line Usage

Generate a dashboard from CSV data:

```bash
algosystem dashboard strategy.csv
```

Launch the visual dashboard editor:

```bash
algosystem launch
```

### Python API

```python
import pandas as pd
from algosystem.api import quick_backtest

# Load your data (CSV with date index and price column)
data = pd.read_csv('strategy.csv', index_col=0, parse_dates=True)

# Run backtest and show results
engine = quick_backtest(data)
```

## 📚 Documentation

Full documentation is available in the `docs/` directory:

- [Installation and Getting Started](docs/installation.md)
- [CLI Documentation](docs/cli.md)
- [Python API Reference](docs/api.md)
- [Dashboard Customization Guide](docs/dashboard.md)
- [Benchmark Integration Guide](docs/benchmarks.md)
- [Data Connectors Guide](docs/data_connectors.md)

## 🔍 Key Components

### Engine Class

Core backtesting engine for running tests:

```python
from algosystem.backtesting import Engine

engine = Engine(
    data=price_series,
    benchmark=benchmark_series,  # Optional
    start_date='2022-01-01',     # Optional
    end_date='2022-12-31'        # Optional
)
results = engine.run()
```

### API Class

High-level interface with more functionality:

```python
from algosystem.api import AlgoSystem

# Run backtest
engine = AlgoSystem.run_backtest(price_series, benchmark_series)

# Print formatted results
AlgoSystem.print_results(engine, detailed=True)

# Generate dashboard
AlgoSystem.generate_dashboard(engine, open_browser=True)
```

### Dashboard Configuration

Create custom dashboards via JSON configuration:

```python
from algosystem.api import AlgoSystem

# Load and modify configuration
config = AlgoSystem.load_config()
config["layout"]["title"] = "My Custom Dashboard"

# Save configuration
AlgoSystem.save_config(config, "my_config.json")

# Use configuration for dashboard
engine.generate_dashboard(config_path="my_config.json")
```

## 🔧 Common Use Cases

### Basic Backtesting

```python
from algosystem.backtesting import Engine

# Run backtest
engine = Engine(price_series)
results = engine.run()

# Print key metrics
print(f"Total Return: {results['returns']:.2%}")
print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['metrics']['max_drawdown']:.2%}")
```

### Benchmark Comparison

```python
from algosystem.data.benchmark import fetch_benchmark_data

# Fetch S&P 500 data
sp500_data = fetch_benchmark_data('sp500')

# Run backtest with benchmark
engine = Engine(price_series, benchmark=sp500_data)
results = engine.run()

# Print benchmark comparison metrics
print(f"Alpha: {results['metrics']['alpha']:.2%}")
print(f"Beta: {results['metrics']['beta']:.2f}")
```

### Standalone Dashboard

```python
# Generate standalone HTML dashboard
dashboard_path = engine.generate_standalone_dashboard('my_dashboard.html')
```

## 🛠️ Troubleshooting

### Package Not Found

If you see `ImportError: No module named 'algosystem'`:

1. Verify installation: `pip list | grep algosystem`
2. Try reinstalling: `pip install --upgrade --force-reinstall algosystem`

### Configuration Issues

Reset to default configuration:
```bash
algosystem reset-user-config
```

### Quick Start for Contributors

```bash
# Clone repository
git clone https://github.com/yourusername/algosystem.git
cd algosystem

# Install with dev dependencies
poetry install --with dev

# Run tests
pytest
```

## 📖 License & Usage Terms

trade-ngin is licensed under the [GPL v3](https://www.gnu.org/licenses/gpl-3.0) License. See LICENSE file for details.

## 📚 Citing

If you use AlgoSystem in your research, please cite:

```bibtex
@software{algosystem,
  author = {AlgoGators Team},
  title = {AlgoSystem: A Python Library for Algorithmic Trading},
  url = {https://github.com/algogators/algosystem},
  year = {2025},
}
```
