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

## Regimes

```bash
algosystem regimes strategy.csv --price-column Strategy
algosystem regimes strategy.csv --price-column Strategy --benchmark sp500
algosystem regimes strategy.csv --price-column Strategy --regimes 4 --vol-window 63
```

Breaks realized performance down by volatility regime and prints the Sharpe
earned in each. `--benchmark` classifies on a reference series instead of the
strategy's own volatility; the two series are restricted to the dates they
share, so a trading-day benchmark works against a calendar-day CSV.

`--regimes 3` (the default) names the buckets `low_vol`/`med_vol`/`high_vol`;
any other count names them `regime_0` … `regime_N-1`.

Because the two series are restricted to shared dates, a calendar mismatch
drops observations and widens the gaps between the survivors, so returns
span more elapsed time than before. `vol_window` counts observations, not
days, and the Sharpe annualization stays at 252 — treat a benchmarked run
on mismatched calendars as comparable within itself, not against an
unbenchmarked run.

The command refuses a series too short to classify rather than printing an
all-zero breakdown that would read like a real finding.

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
