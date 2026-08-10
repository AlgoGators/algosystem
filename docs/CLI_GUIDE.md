# CLI Guide

The CLI is a thin adapter over the same backtesting, tearsheet, validation,
benchmark, and repository use cases exposed by the Python API.

## Backtest

```bash
algosystem backtest strategy.csv --price-column Strategy --detailed
algosystem backtest strategy.csv --benchmark sp500 --start 2022-01-01 --end 2023-01-01
```

## Tearsheet

```bash
algosystem tearsheet strategy.csv --price-column Strategy --output tearsheet.html
algosystem tearsheet strategy.csv --mode basic --open
```

## Validation

```bash
algosystem validate strategy.csv --strategy momentum --reps 200 --seed 7 --output overfit.html
algosystem validate-strategies
```

Validation reports are local HTML files, but the charts load Plotly from a CDN
when opened in a browser.

## Benchmarks

```bash
algosystem benchmarks
```

## Database

```bash
algosystem db init
algosystem db save strategy.csv --price-column Strategy --name strategy-v1
algosystem db list
algosystem db show RUN_ID
algosystem db compare RUN_ID RUN_ID
algosystem db delete RUN_ID
```

Database commands read connection settings from `DB_HOST`, `DB_PORT`, `DB_NAME`,
`DB_USER`, and `DB_PASSWORD`. A local `.env` file is loaded by the CLI entry point.
