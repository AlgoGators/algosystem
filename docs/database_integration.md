# Database Integration

AlgoSystem supports exporting backtest results to a PostgreSQL database for persistent storage and analysis. This functionality is built into the Engine class via the `export_db` method.

## Setting Up the Database

Before using the database export functionality, you need:

1. A PostgreSQL database server
2. Database credentials in your .env file
3. The required schema and tables created in your database

### Environment Variables

Add the following to your `.env` file:

```
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
```

### Creating the Required Schema and Tables

Execute the following SQL script to create the necessary schema and tables:

```sql
-- Create backtest schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS backtest;

-- Equity curve table for storing time series data
CREATE TABLE IF NOT EXISTS backtest.equity_curve (
    run_id    BIGINT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    equity    FLOAT NOT NULL,
    PRIMARY KEY (run_id, timestamp)
);

-- Final positions table for storing end-of-backtest positions
CREATE TABLE IF NOT EXISTS backtest.final_positions (
    run_id         BIGINT NOT NULL,
    symbol         VARCHAR NOT NULL,
    quantity       FLOAT NOT NULL,
    average_price  FLOAT NOT NULL,
    unrealized_pnl FLOAT NOT NULL,
    realized_pnl   FLOAT NOT NULL,
    PRIMARY KEY (run_id, symbol)
);

-- Results table for storing performance metrics
CREATE TABLE IF NOT EXISTS backtest.results (
    run_id              BIGINT PRIMARY KEY,
    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    total_return        FLOAT,
    sharpe_ratio        FLOAT,
    sortino_ratio       FLOAT,
    max_drawdown        FLOAT,
    calmar_ratio        FLOAT,
    volatility          FLOAT,
    total_trades        INT,
    win_rate            FLOAT,
    profit_factor       FLOAT,
    avg_win             FLOAT,
    avg_loss            FLOAT,
    max_win             FLOAT,
    max_loss            FLOAT,
    avg_holding_period  FLOAT,
    var_95              FLOAT,
    cvar_95             FLOAT,
    beta                FLOAT,
    correlation         FLOAT,
    downside_volatility FLOAT,
    config              JSONB
);

-- Symbol PnL table for storing performance by symbol
CREATE TABLE IF NOT EXISTS backtest.symbol_pnl (
    run_id BIGINT NOT NULL,
    symbol VARCHAR NOT NULL,
    pnl    FLOAT NOT NULL,
    PRIMARY KEY (run_id, symbol)
);
```

## Exporting Backtest Results

After running a backtest, you can export the results to the database:

```python
from algosystem.backtesting import Engine

# Run backtest
engine = Engine(price_series)
results = engine.run()

# Export to database with auto-generated run_id
run_id = engine.export_db()
print(f"Exported with run_id: {run_id}")

# Or specify a custom run_id
custom_run_id = 12345
engine.export_db(run_id=custom_run_id)
```

## Required Dependencies

The database export functionality requires the `psycopg2` package. Install it with:

```bash
pip install psycopg2-binary
```

## Querying Backtest Results

You can query your backtest results using standard SQL:

```sql
-- Get all backtest runs
SELECT run_id, start_date, end_date, total_return, sharpe_ratio
FROM backtest.results
ORDER BY run_id DESC;

-- Get equity curve for a specific run
SELECT timestamp, equity
FROM backtest.equity_curve
WHERE run_id = 123
ORDER BY timestamp;

-- Get symbol performance for a specific run
SELECT symbol, pnl
FROM backtest.symbol_pnl
WHERE run_id = 123
ORDER BY pnl DESC;

-- Get top performing strategies by Sharpe ratio
SELECT run_id, start_date, end_date, total_return, sharpe_ratio
FROM backtest.results
ORDER BY sharpe_ratio DESC
LIMIT 10;
```