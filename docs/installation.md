# Installation Guide

## Requirements

- **Python 3.9+** (Recommended: 3.10 or 3.11)
- **Operating Systems**: Windows, macOS, Linux

## Installation

### Standard Installation
```bash
pip install algosystem
```

### With Optional Features
```bash
pip install algosystem
```

### Development Installation
```bash
git clone https://github.com/algogators/algosystem.git
cd algosystem
poetry install --with dev
```

## Verification

```bash
# Test CLI
algosystem --help

# Run demo
algosystem test

# Test Python import
python -c "import algosystem; print('Success!')"
```

## Optional Dependencies

### Benchmark Data
```bash
pip install yfinance
```
Enables automatic fetching of 40+ market benchmarks.

### Web Dashboard Editor
```bash
pip install flask
```
Enables `algosystem launch` visual editor.

### Database Export
```bash
pip install psycopg2-binary
```
Enables PostgreSQL export functionality.

## Virtual Environment (Recommended)

```bash
# Create environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install
pip install algosystem

```

## Database Setup (Optional)

Create `.env` file for database features:
```bash
DB_HOST=localhost
DB_PORT=5432
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=algosystem_db
```

## Quick Test

```python
import pandas as pd
import numpy as np
from algosystem.api import quick_backtest

# Create sample data
dates = pd.date_range('2022-01-01', periods=100, freq='D')
prices = 100 * (1 + np.random.normal(0.001, 0.02, 100)).cumprod()
data = pd.Series(prices, index=dates)

# Test
engine = quick_backtest(data)
print("Installation successful!")
```