# 🚀 AlgoSystem

[![PyPI version](https://badge.fury.io/py/algosystem.svg)](https://badge.fury.io/py/algosystem)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-MIT-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Built with Poetry](https://img.shields.io/badge/built%20with-Poetry-purple)](https://python-poetry.org/)

**AlgoGators professional algorithmic backtesting and dashboard visualization library.**

## 🚀 Quick Start

### Installation
```bash
pip install algosystem
```

### Command Line
```bash
# Generate dashboard from CSV
algosystem dashboard strategy.csv

# With benchmark comparison
algosystem dashboard strategy.csv --benchmark sp500

# Launch visual editor
algosystem launch
```

### Python API
```python
import pandas as pd
from algosystem.api import quick_backtest

# Load strategy data (CSV with date index and price column)
data = pd.read_csv('strategy.csv', index_col=0, parse_dates=True)

# Run backtest and show dashboard
engine = quick_backtest(data)
```

## 📊 Dashboard Features

### Available Metrics (20+)
- **Performance**: Total Return, Annualized Return, Volatility
- **Risk**: Max Drawdown, VaR, CVaR, Skewness
- **Ratios**: Sharpe, Sortino, Calmar, Information Ratio
- **Benchmark**: Alpha, Beta, Correlation, Tracking Error

### Available Charts (15+)
- **Core**: Equity Curve, Drawdown, Daily Returns
- **Rolling**: Sharpe, Sortino, Volatility, Skewness
- **Analysis**: Monthly Returns, Yearly Returns, Benchmark Comparison

### Built-in Benchmarks (40+)
- **Indices**: S&P 500, NASDAQ, DJIA, Russell 2000
- **International**: Europe, UK, Japan, China, Emerging Markets
- **Sectors**: Technology, Healthcare, Financials, Energy
- **Assets**: Gold, Real Estate, Commodities, Bonds

## 📖 Documentation

- [Installation Guide](INSTALLATION.md)
- [CLI Reference](CLI_GUIDE.md)
- [Python API](API_GUIDE.md)
- [Dashboard Customization](DASHBOARD_GUIDE.md)
- [Benchmark Integration](BENCHMARK_GUIDE.md)

## 🔧 Example Usage

### Complete Workflow
```python
from algosystem.api import AlgoSystem

# Load data and benchmark
strategy_data = pd.read_csv('strategy.csv', index_col=0, parse_dates=True)
benchmark_data = AlgoSystem.get_benchmark('sp500')

# Run backtest
engine = AlgoSystem.run_backtest(strategy_data, benchmark_data)

# Print results
AlgoSystem.print_results(engine, detailed=True)

# Generate dashboard
AlgoSystem.generate_dashboard(engine, open_browser=True)

# Export data
AlgoSystem.export_data(engine, 'results.csv')
```

### Engine-Level Control
```python
from algosystem.backtesting import Engine

engine = Engine(
    data=strategy_data,
    benchmark=benchmark_data,
    start_date='2022-01-01',
    end_date='2022-12-31'
)

results = engine.run()
dashboard_path = engine.generate_dashboard()
```

## 📋 Data Format

Your CSV should have:
- Date column as index (YYYY-MM-DD)
- Price/value column representing portfolio value

```csv
Date,Strategy
2022-01-01,100000.00
2022-01-02,100500.00
2022-01-03,99800.00
```

## 🛠️ Optional Features

### Database Export
```bash
pip install psycopg2-binary
```

## 📚 License

<<<<<<< HEAD
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

AlgoSystem is licensed under the [GPL v3](https://www.gnu.org/licenses/gpl-3.0) License. See LICENSE file for details.

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
=======
GPL v3 License. See LICENSE file for details.
>>>>>>> b65a78d (docs: 📜)
