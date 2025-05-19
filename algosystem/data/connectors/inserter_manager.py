from typing import Optional, Union, List, Any, Dict
import pandas as pd
from datetime import datetime
import time
from algosystem.data.connectors.base_db_manager import BaseDBManager

class InserterManager(BaseDBManager):
    """Class for inserting data into the database."""
    
    def insert_data(self, records: List[Dict[str, Any]], schema: str, table: str) -> bool:
        """
        Inserts data into a specified table.

        Args:
            records (List[Dict[str, Any]]): List of dictionaries with data to insert
            schema (str): Database schema name
            table (str): Database table name
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        if not records:
            self.logger.warning(f"No rows to insert into {schema}.{table}")
            return False

        self._connect_psycopg2()
        full_table = f"{schema}.{table}"
        cols = list(records[0].keys())
        col_list = ", ".join(cols)
        # Template for each row: "(%s,%s,...)"
        tmpl = "(" + ",".join(["%s"] * len(cols)) + ")"
        values = [tuple(item[c] for c in cols) for item in records]

        try:
            with self.conn.cursor() as cur:
                from psycopg2.extras import execute_values
                execute_values(
                    cur,
                    f"INSERT INTO {full_table} ({col_list}) VALUES %s",
                    values,
                    template=tmpl,
                )
            self.conn.commit()
            self.logger.info(f"Inserted {len(values)} rows into {full_table}")
            return True
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Failed to insert into {full_table}: {e}")
            return False
    
    def get_next_run_id(self) -> str:
        """
        Generate a timestamp-based run_id.
        
        Instead of incrementing the max run_id which assumes numeric IDs,
        this implementation generates a timestamp-based ID that's unique
        and compatible with text-based run_id columns.

        Returns:
            str: A unique timestamp-based run_id
        """
        try:
            # Generate timestamp-based ID - format: YYYYMMDD_HHMMSS_milliseconds
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            milliseconds = str(int(time.time() * 1000) % 1000).zfill(3)
            
            # Create a unique run_id by combining timestamp with milliseconds
            run_id = f"{timestamp}_{milliseconds}"
            
            self.logger.info(f"Generated new run_id: {run_id}")
            return run_id
            
        except Exception as e:
            self.logger.error(f"Error generating timestamp-based run_id: {e}")
            # Fallback to a simple timestamp if something goes wrong
            return str(int(time.time()))
    
    def export_backtest_results(
        self,
        run_id: Union[str, int],
        equity_curve: pd.Series,
        name: str = "Backtest",
        description: str = "",
        hyperparameters: Optional[Dict[str, Any]] = None,
        final_positions: Optional[pd.DataFrame] = None,
        symbol_pnl: Optional[pd.DataFrame] = None,
        metrics: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Union[str, int]:
        """
        Export backtest results to the database.

        Args:
            run_id (Union[str, int]): Unique identifier for this backtest run
            equity_curve (pd.Series): Series of equity values indexed by timestamp
            name (str, optional): Name of the backtest. Defaults to "Backtest".
            description (str, optional): Description of the backtest. Defaults to "".
            hyperparameters (Optional[Dict[str, Any]], optional): Dictionary of hyperparameters. Defaults to None.
            final_positions (Optional[pd.DataFrame], optional): DataFrame of final positions. Defaults to None.
            symbol_pnl (Optional[pd.DataFrame], optional): DataFrame of PnL by symbol. Defaults to None.
            metrics (Optional[Dict[str, Any]], optional): Dictionary of backtest metrics. Defaults to None.
            config (Optional[Dict[str, Any]], optional): Dictionary of backtest configuration. Defaults to None.

        Returns:
            Union[str, int]: The run_id used for the export
        """
        self._connect_psycopg2()
        
        try:
            # Convert dictionaries to JSON strings if they exist
            import json
            config_json = json.dumps(config) if config is not None else None
            hyperparameters_json = json.dumps(hyperparameters) if hyperparameters is not None else None
            
            # Convert the run_id to string if it isn't already
            run_id = str(run_id)
            
            # FIRST: Insert metadata record
            metadata_data = {
                "run_id": run_id,
                "name": name,
                "description": description,
                "hyperparameters": hyperparameters_json,
                "date_inserted": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.insert_data([metadata_data], "backtest", "run_metadata")
            
            # SECOND: Export backtest results and metrics
            if metrics is not None:
                # Prepare metrics data
                result_data = {
                    "run_id": run_id,
                    "start_date": equity_curve.index[0].date()
                    if equity_curve is not None and not equity_curve.empty
                    else None,
                    "end_date": equity_curve.index[-1].date()
                    if equity_curve is not None and not equity_curve.empty
                    else None,
                    "config": config_json,
                }

                # Add specific metrics
                metric_fields = [
                    "total_return",
                    "sharpe_ratio",
                    "sortino_ratio",
                    "max_drawdown",
                    "calmar_ratio",
                    "volatility",
                    "total_trades",
                    "win_rate",
                    "profit_factor",
                    "avg_win",
                    "avg_loss",
                    "max_win",
                    "max_loss",
                    "avg_holding_period",
                    "var_95",
                    "cvar_95",
                    "beta",
                    "correlation",
                    "downside_volatility",
                ]

                for field in metric_fields:
                    if field in metrics:
                        result_data[field] = float(metrics[field])

                self.insert_data([result_data], "backtest", "results")
            else:
                # Even without metrics, we need at least a minimal record in results table
                result_data = {
                    "run_id": run_id,
                    "start_date": equity_curve.index[0].date()
                    if equity_curve is not None and not equity_curve.empty
                    else None,
                    "end_date": equity_curve.index[-1].date()
                    if equity_curve is not None and not equity_curve.empty
                    else None,
                    "config": config_json,
                }
                    
                self.insert_data([result_data], "backtest", "results")

            # THIRD: Export equity curve
            if equity_curve is not None and not equity_curve.empty:
                equity_data = []
                for timestamp, equity in equity_curve.items():
                    equity_data.append(
                        {"run_id": run_id, "timestamp": timestamp, "equity": float(equity)}
                    )

                self.insert_data(equity_data, "backtest", "equity_curve")

            # FOURTH: Export final positions if available
            if final_positions is not None and not final_positions.empty:
                positions_data = []
                for _, row in final_positions.iterrows():
                    positions_data.append(
                        {
                            "run_id": run_id,
                            "symbol": row["symbol"],
                            "quantity": float(row["quantity"]),
                            "average_price": float(row["average_price"]),
                            "unrealized_pnl": float(row.get("unrealized_pnl", 0.0)),
                            "realized_pnl": float(row.get("realized_pnl", 0.0)),
                        }
                    )

                self.insert_data(positions_data, "backtest", "final_positions")

            # FIFTH: Export symbol PnL if available
            if symbol_pnl is not None and not symbol_pnl.empty:
                pnl_data = []
                for _, row in symbol_pnl.iterrows():
                    pnl_data.append(
                        {
                            "run_id": run_id,
                            "symbol": row["symbol"],
                            "pnl": float(row["pnl"]),
                        }
                    )

                self.insert_data(pnl_data, "backtest", "symbol_pnl")

            return run_id
            
        except Exception as e:
            self.logger.error(f"Failed to export backtest results: {e}")
            # Try to rollback if there's a transaction in progress
            try:
                if hasattr(self, 'conn') and self.conn and not self.conn.closed:
                    self.conn.rollback()
            except Exception as rollback_error:
                self.logger.error(f"Error during rollback: {rollback_error}")
            raise