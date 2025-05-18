import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

load_dotenv()

class Inserter:
    """
    Inserts backtesting results into Postgres database tables.
    Connection parameters are read from .env file.
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)

        # Load and validate environment variables
        self.db_name = os.getenv("DB_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_pass = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")

        missing = [k for k, v in {
            "DB_NAME": self.db_name,
            "DB_USER": self.db_user,
            "DB_PASSWORD": self.db_pass,
            "DB_HOST": self.db_host,
            "DB_PORT": self.db_port,
        }.items() if not v]
        
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

        self.conn = None  # psycopg2 connection

    def connect(self) -> None:
        """Establish a psycopg2 connection (reuses if open)."""
        if self.conn and not self.conn.closed:
            return

        self.logger.info("Opening new database connection")
        self.conn = psycopg2.connect(
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_pass,
            host=self.db_host,
            port=self.db_port,
        )

    def insert_data(
        self,
        data: List[Dict[str, Any]],
        schema: str,
        table: str
    ) -> None:
        """
        Bulk insert a list of same-shaped dictionaries into schema.table.
        
        Args:
            data: List of dictionaries with identical keys
            schema: Database schema name
            table: Database table name
        """
        if not data:
            self.logger.warning(f"No rows to insert into {schema}.{table}")
            return

        self.connect()
        full_table = f"{schema}.{table}"
        cols = list(data[0].keys())
        col_list = ", ".join(cols)
        # Template for each row: "(%s,%s,...)"
        tmpl = "(" + ",".join(["%s"] * len(cols)) + ")"
        values = [tuple(item[c] for c in cols) for item in data]

        try:
            with self.conn.cursor() as cur:
                execute_values(
                    cur,
                    f"INSERT INTO {full_table} ({col_list}) VALUES %s",
                    values,
                    template=tmpl
                )
            self.conn.commit()
            self.logger.info(f"Inserted {len(values)} rows into {full_table}")
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Failed to insert into {full_table}: {e}")
            raise

    def validate_insertion(
        self, schema: str, table: str, expected_rows: int
    ) -> bool:
        """
        Verify that at least the expected number of rows are present in the table.
        
        Args:
            schema: Database schema name
            table: Database table name
            expected_rows: Minimum number of rows expected
            
        Returns:
            True if validation passes, False otherwise
        """
        try:
            self.connect()
            full_table = f"{schema}.{table}"
            with self.conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {full_table}")
                actual = cur.fetchone()[0]
            if actual >= expected_rows:
                self.logger.info(f"Validation OK: {actual} ≥ {expected_rows} rows")
                return True
            else:
                self.logger.warning(
                    f"Validation FAILED for {full_table}: found {actual}, expected ≥{expected_rows}"
                )
                return False
        except Exception as e:
            self.logger.error(f"Validation error for {schema}.{table}: {e}")
            return False
    
    def get_next_run_id(self) -> int:
        """
        Get the next available run_id from the backtest.results table.
        
        Returns:
            The next available run_id
        """
        self.connect()
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(run_id), 0) + 1 FROM backtest.results")
                next_id = cur.fetchone()[0]
            return next_id
        except Exception as e:
            self.logger.error(f"Error getting next run_id: {e}")
            raise

    def export_backtest_results(
        self,
        run_id: int,
        equity_curve: pd.Series,
        final_positions: Optional[pd.DataFrame] = None,
        symbol_pnl: Optional[pd.DataFrame] = None,
        metrics: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Export backtest results to the database.
        
        Args:
            run_id: Unique identifier for this backtest run
            equity_curve: Series of equity values indexed by timestamp
            final_positions: DataFrame of final positions
            symbol_pnl: DataFrame of PnL by symbol
            metrics: Dictionary of backtest metrics
            config: Dictionary of backtest configuration
            
        Returns:
            The run_id used for the export
        """
        self.connect()
        
        # Export equity curve
        if equity_curve is not None and not equity_curve.empty:
            equity_data = []
            for timestamp, equity in equity_curve.items():
                equity_data.append({
                    "run_id": run_id,
                    "timestamp": timestamp,
                    "equity": float(equity)
                })
            
            self.insert_data(equity_data, "backtest", "equity_curve")
        
        # Export final positions
        if final_positions is not None and not final_positions.empty:
            positions_data = []
            for _, row in final_positions.iterrows():
                positions_data.append({
                    "run_id": run_id,
                    "symbol": row["symbol"],
                    "quantity": float(row["quantity"]),
                    "average_price": float(row["average_price"]),
                    "unrealized_pnl": float(row.get("unrealized_pnl", 0.0)),
                    "realized_pnl": float(row.get("realized_pnl", 0.0))
                })
            
            self.insert_data(positions_data, "backtest", "final_positions")
        
        # Export symbol PnL
        if symbol_pnl is not None and not symbol_pnl.empty:
            pnl_data = []
            for _, row in symbol_pnl.iterrows():
                pnl_data.append({
                    "run_id": run_id,
                    "symbol": row["symbol"],
                    "pnl": float(row["pnl"])
                })
            
            self.insert_data(pnl_data, "backtest", "symbol_pnl")
        
        # Export backtest results and metrics
        if metrics is not None:
            # Prepare metrics data
            result_data = {
                "run_id": run_id,
                "start_date": equity_curve.index[0].date() if equity_curve is not None and not equity_curve.empty else None,
                "end_date": equity_curve.index[-1].date() if equity_curve is not None and not equity_curve.empty else None,
                "config": config,
            }
            
            # Add specific metrics
            metric_fields = [
                "total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown",
                "calmar_ratio", "volatility", "total_trades", "win_rate",
                "profit_factor", "avg_win", "avg_loss", "max_win", "max_loss",
                "avg_holding_period", "var_95", "cvar_95", "beta", "correlation",
                "downside_volatility"
            ]
            
            for field in metric_fields:
                if field in metrics:
                    result_data[field] = float(metrics[field])
            
            self.insert_data([result_data], "backtest", "results")
        
        return run_id