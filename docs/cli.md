# AlgoSystem CLI Guide

AlgoSystem provides a powerful command-line interface for running backtests, generating dashboards, and managing configurations. This guide covers the available CLI commands and their options.

## Installation

The CLI is automatically installed when you install AlgoSystem:

```bash
pip install algosystem
```

## Basic Commands

### Display Help

Get information about all available commands:

```bash
algosystem --help
```

Get help for a specific command:

```bash
algosystem <command> --help
```

## Dashboard Generation

### Generate a Dashboard from CSV

```bash
algosystem dashboard input_file.csv [options]
```

#### Options:

- `--output-file, -o <path>`: Path to save standalone HTML dashboard (default: `./dashboard.html`)
- `--benchmark, -b <benchmark>`: Benchmark to use (file path or alias like 'sp500', 'nasdaq')
- `--start-date <YYYY-MM-DD>`: Start date for backtest
- `--end-date <YYYY-MM-DD>`: End date for backtest
- `--config, -c <path>`: Path to custom dashboard configuration
- `--default`: Use library default configuration
- `--open-browser`: Open dashboard in browser when done
- `--force-refresh`: Force refresh of benchmark data

### Examples:

```bash
# Basic usage
algosystem dashboard strategy.csv

# With benchmark comparison
algosystem dashboard strategy.csv --benchmark sp500

# Custom date range
algosystem dashboard strategy.csv --start-date 2022-01-01 --end-date 2022-12-31

# Specifying output file
algosystem dashboard strategy.csv --output-file my_dashboard.html

# With custom configuration
algosystem dashboard strategy.csv --config my_config.json
```

## Dashboard Editor

### Launch the Interactive Dashboard Editor

```bash
algosystem launch [options]
```

#### Options:

- `--config, -c <path>`: Path to configuration file to load
- `--host <host>`: Host to run server on (default: 127.0.0.1)
- `--port <port>`: Port to run server on (default: 5000)
- `--debug`: Run server in debug mode
- `--save-config <path>`: Path to save edited configuration
- `--default`: Use default configuration

### Examples:

```bash
# Basic usage
algosystem launch

# Custom port
algosystem launch --port 8080

# With configuration file
algosystem launch --config my_config.json

# Save changes to specific location
algosystem launch --save-config ./configs/dashboard_config.json
```

## Configuration Management

### Create a New Configuration

```bash
algosystem create-config output_path.json [options]
```

#### Options:

- `--based-on, -b <path>`: Base on existing configuration
- `--default`: Create based on library default
- `--user`: Create based on user configuration

### Examples:

```bash
# Create new config
algosystem create-config my_config.json

# Based on existing config
algosystem create-config new_config.json --based-on existing_config.json
```

### Show Configuration Contents

```bash
algosystem show-config config_file.json
```

### List Available Configurations

```bash
algosystem list-configs [options]
```

#### Options:

- `--show-user`: Show full path of user configuration
- `--show-default`: Show full path of default configuration

### Reset User Configuration

```bash
algosystem reset-user-config [options]
```

#### Options:

- `--backup`: Create backup of existing configuration (default)
- `--no-backup`: Skip backup creation

## Benchmark Support

### List and Fetch Benchmarks

```bash
algosystem benchmarks [benchmark] [options]
```

#### Options:

- `--fetch-all`: Fetch all available benchmarks
- `--force-refresh`: Force refresh of cached data
- `--info`: Show detailed benchmark information
- `--start-date <YYYY-MM-DD>`: Start date for benchmark data
- `--end-date <YYYY-MM-DD>`: End date for benchmark data

### Examples:

```bash
# List all benchmarks
algosystem benchmarks

# Show detailed benchmark info
algosystem benchmarks --info

# Fetch specific benchmark
algosystem benchmarks sp500

# Fetch all benchmarks
algosystem benchmarks --fetch-all
```

### Compare Benchmarks

```bash
algosystem compare-benchmarks [benchmarks...] [options]
```

#### Options:

- `--output-file, -o <path>`: Save comparison to CSV
- `--start-date <YYYY-MM-DD>`: Start date for comparison
- `--end-date <YYYY-MM-DD>`: End date for comparison
- `--metrics`: Show performance metrics
- `--force-refresh`: Force refresh of benchmark data

### Examples:

```bash
# Compare multiple benchmarks
algosystem compare-benchmarks sp500 nasdaq gold

# With date range and metrics
algosystem compare-benchmarks sp500 nasdaq --start-date 2020-01-01 --metrics
```

## Quick Test

Run a test with simulated data:

```bash
algosystem test [options]
```

#### Options:

- `--output-dir, -o <path>`: Directory for test output
- `--periods, -p <number>`: Number of trading days to simulate
- `--benchmark, -b <benchmark>`: Benchmark to use
- `--open-browser`: Open dashboard in browser

### Examples:

```bash
# Quick test with defaults
algosystem test

# Longer test period with specific benchmark
algosystem test --periods 500 --benchmark nasdaq
```

## Environment Variables

The CLI respects the following environment variables:

- `ALGO_DASHBOARD_CONFIG`: Path to configuration file
- `ALGO_DASHBOARD_SAVE_CONFIG`: Path to save configuration
- `ALGO_DASHBOARD_DATA_DIR`: Directory containing data files

## Available Benchmarks

AlgoSystem supports many benchmark aliases:

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

## Troubleshooting

### "No module named 'yfinance'"

If you see this error when using benchmark features, install the required package:

```bash
pip install yfinance
```

### "No module named 'flask'"

When trying to use the dashboard editor:

```bash
pip install flask
```

### Configuration Errors

If you encounter configuration-related errors, reset to defaults:

```bash
algosystem reset-user-config
```