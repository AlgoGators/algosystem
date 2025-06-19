# CLI Reference Guide

## Core Commands

### Dashboard Generation

```bash
# Basic dashboard
algosystem dashboard strategy.csv

# With benchmark
algosystem dashboard strategy.csv --benchmark sp500

# Custom output
algosystem dashboard strategy.csv --output-file my_dashboard.html

# Date range
algosystem dashboard strategy.csv --start-date 2022-01-01 --end-date 2022-12-31

# Interactive dashboard
algosystem render strategy.csv --output-dir ./dashboard/
```

**Options:**
- `--output-file, -o`: Output HTML file
- `--benchmark, -b`: Benchmark alias or file
- `--start-date/--end-date`: Date range (YYYY-MM-DD)
- `--config, -c`: Custom configuration
- `--open-browser`: Open in browser
- `--force-refresh`: Refresh benchmark data

### Visual Dashboard Editor

```bash
# Launch editor
algosystem launch

# Custom host/port
algosystem launch --host 0.0.0.0 --port 8080

# Load configuration
algosystem launch --config my_config.json

# Save changes
algosystem launch --save-config updated_config.json
```

### Configuration Management

```bash
# Create configuration
algosystem create-config my_config.json

# View configuration
algosystem show-config my_config.json

# List configurations
algosystem list-configs

# Reset to defaults
algosystem reset-user-config
```

### Benchmark Management

```bash
# List benchmarks
algosystem benchmarks

# Show details
algosystem benchmarks --info

# Fetch specific benchmark
algosystem benchmarks sp500

# Compare benchmarks
algosystem compare-benchmarks sp500 nasdaq gold

# Export comparison
algosystem compare-benchmarks sp500 nasdaq --output-file comparison.csv
```

### Testing

```bash
# Quick test
algosystem test

# Custom test
algosystem test --periods 500 --benchmark nasdaq --open-browser
```

## Available Benchmarks

### Stock Indices
- `sp500` - S&P 500
- `nasdaq` - NASDAQ Composite
- `djia` - Dow Jones
- `russell2000` - Russell 2000
- `vix` - Volatility Index

### International
- `europe` - EURO STOXX 50
- `uk` - FTSE 100
- `japan` - Nikkei 225
- `china` - Shanghai Composite
- `emerging_markets` - MSCI Emerging Markets

### Sectors
- `technology` - Technology Sector
- `healthcare` - Healthcare Sector
- `financials` - Financial Sector
- `energy` - Energy Sector
- `utilities` - Utilities Sector

### Asset Classes
- `gold` - Gold ETF
- `treasury_bonds` - Treasury Bonds
- `corporate_bonds` - Corporate Bonds
- `real_estate` - Real Estate ETF
- `commodities` - Commodities Index

## Command Examples

### Complete Workflow
```bash
# 1. Create configuration
algosystem create-config my_config.json

# 2. Generate dashboard with benchmark
algosystem dashboard strategy.csv \
  --benchmark sp500 \
  --config my_config.json \
  --output-file results.html \
  --open-browser

# 3. Compare multiple benchmarks
algosystem compare-benchmarks sp500 nasdaq gold \
  --start-date 2022-01-01 \
  --metrics \
  --output-file benchmark_comparison.csv
```

### Interactive Development
```bash
# 1. Launch editor
algosystem launch --port 8080

# 2. Edit configuration in browser
# (Visit http://localhost:8080)

# 3. Save configuration
# (Use editor's save functionality)

# 4. Generate final dashboard
algosystem dashboard strategy.csv --config edited_config.json
```

## Data Format Requirements

CSV format:
```csv
Date,Strategy
2022-01-01,100000.00
2022-01-02,100500.00
2022-01-03,99800.00
```

- Date column as index (YYYY-MM-DD)
- Price/value column representing portfolio value
- No missing values in the price column