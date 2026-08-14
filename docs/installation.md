# Installation Guide

## Requirements

- Python 3.9+
- Windows, macOS, or Linux

## Install

```bash
pip install algosystem
```

For development:

```bash
git clone https://github.com/algogators/algosystem.git
cd algosystem
poetry install --with dev
```

## Verify

```bash
python -c "import algosystem"
algosystem --help
```

## Optional Configuration

Benchmark fetching uses yfinance when benchmark data is requested.

Postgres persistence uses explicit database settings:

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=algosystem
DB_USER=algosystem
DB_PASSWORD=secret
```
