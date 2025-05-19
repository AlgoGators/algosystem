import pandas as pd
from typing import List, Dict, Any, Optional, Union

from algosystem.data.connectors.base_db_manager import BaseDBManager
from algosystem.data.connectors.db_models import *

class LoaderManager(BaseDBManager):
    """Class for loading and querying data from the database."""
    
    def get_backtest_names(self) -> List[Dict[str, Any]]:
        """
        Retrieve all backtest names with their run ID and insertion dates.
        
        Returns:
            List[Dict[str, Any]]: List containing run_id, name, and date_inserted for each backtest.
        """
        self._connect_psycopg2()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT run_id, name, date_inserted
                    FROM backtest.run_metadata
                    ORDER BY date_inserted DESC
                """)
                
                results = cur.fetchall()
                
                if not results:
                    return []
                
                return [
                    {"run_id": run_id, "name": name, "date_inserted": date_inserted}
                    for run_id, name, date_inserted in results
                ]
        except Exception as e:
            self.logger.error(f"Error retrieving backtest names: {e}")
            raise
    
    def get_backtest_by_name(self, name: str) -> List[Dict[str, Any]]:
        """
        Retrieve metadata for backtests with the specified name.
        
        Args:
            name (str): Name of the backtest
            
        Returns:
            List[Dict[str, Any]]: List of dictionaries containing metadata for matching backtests
        """
        self._connect_psycopg2()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT rm.run_id, rm.name, rm.description, rm.hyperparameters, rm.date_inserted,
                           r.start_date, r.end_date, r.total_return, r.sharpe_ratio, r.max_drawdown
                    FROM backtest.run_metadata rm
                    LEFT JOIN backtest.results r ON rm.run_id = r.run_id
                    WHERE rm.name = %s
                    ORDER BY rm.date_inserted DESC
                """, (name,))
                
                columns = [desc[0] for desc in cur.description]
                results = cur.fetchall()
                
                if not results:
                    return []
                
                return [dict(zip(columns, row)) for row in results]
        except Exception as e:
            self.logger.error(f"Error retrieving metadata for backtest '{name}': {e}")
            raise
    
    def get_backtest_results(self, run_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Retrieve results data for a specific run_id.
        
        Args:
            run_id (Union[str, int]): ID of the backtest run
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing results data or None if not found
        """
        self._connect_psycopg2()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT *
                    FROM backtest.results
                    WHERE run_id = %s
                """, (str(run_id),))
                
                columns = [desc[0] for desc in cur.description]
                result = cur.fetchone()
                
                if not result:
                    return None
                
                return dict(zip(columns, result))
        except Exception as e:
            self.logger.error(f"Error retrieving results for run_id '{run_id}': {e}")
            return None
    
    def get_equity_curve(self, run_id: Union[str, int]) -> Optional[pd.Series]:
        """
        Retrieve equity curve data for a specific run_id.
        
        Args:
            run_id (Union[str, int]): ID of the backtest run
            
        Returns:
            Optional[pd.Series]: Pandas Series containing equity curve data or None if not found
        """
        self._connect_psycopg2()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT timestamp, equity
                    FROM backtest.equity_curve
                    WHERE run_id = %s
                    ORDER BY timestamp
                """, (str(run_id),))
                
                data = cur.fetchall()
                
                if not data:
                    return None
                
                timestamps = [row[0] for row in data]
                equity_values = [row[1] for row in data]
                return pd.Series(equity_values, index=timestamps, name="equity")
        except Exception as e:
            self.logger.error(f"Error retrieving equity curve for run_id '{run_id}': {e}")
            return None
    
    def get_final_positions(self, run_id: Union[str, int]) -> Optional[pd.DataFrame]:
        """
        Retrieve final positions data for a specific run_id.
        
        Args:
            run_id (Union[str, int]): ID of the backtest run
            
        Returns:
            Optional[pd.DataFrame]: DataFrame containing final positions or None if not found
        """
        self._connect_psycopg2()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT symbol, quantity, average_price, unrealized_pnl, realized_pnl
                    FROM backtest.final_positions
                    WHERE run_id = %s
                """, (str(run_id),))
                
                data = cur.fetchall()
                
                if not data:
                    return None
                
                columns = ["symbol", "quantity", "average_price", "unrealized_pnl", "realized_pnl"]
                return pd.DataFrame(data, columns=columns)
        except Exception as e:
            self.logger.error(f"Error retrieving final positions for run_id '{run_id}': {e}")
            return None
    
    def get_symbol_pnl(self, run_id: Union[str, int]) -> Optional[pd.DataFrame]:
        """
        Retrieve symbol PnL data for a specific run_id.
        
        Args:
            run_id (Union[str, int]): ID of the backtest run
            
        Returns:
            Optional[pd.DataFrame]: DataFrame containing symbol PnL data or None if not found
        """
        self._connect_psycopg2()
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT symbol, pnl
                    FROM backtest.symbol_pnl
                    WHERE run_id = %s
                """, (str(run_id),))
                
                data = cur.fetchall()
                
                if not data:
                    return None
                
                columns = ["symbol", "pnl"]
                return pd.DataFrame(data, columns=columns)
        except Exception as e:
            self.logger.error(f"Error retrieving symbol PnL for run_id '{run_id}': {e}")
            return None
    
    def load_complete_backtest(self, run_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Load all available data for a specific backtest run.
        
        Args:
            run_id (Union[str, int]): ID of the backtest run
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary containing all available backtest data or None if not found
        """
        self._connect_psycopg2()
        
        try:
            # First check if the run exists
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT rm.*, r.*
                    FROM backtest.run_metadata rm
                    LEFT JOIN backtest.results r ON rm.run_id = r.run_id
                    WHERE rm.run_id = %s
                """, (str(run_id),))
                
                columns = [desc[0] for desc in cur.description]
                result = cur.fetchone()
                
                if not result:
                    self.logger.warning(f"No backtest found with run_id '{run_id}'")
                    return None
                
                # Create a dictionary with metadata and results
                backtest_data = dict(zip(columns, result))
                
                # Load equity curve if available
                equity_curve = self.get_equity_curve(run_id)
                if equity_curve is not None:
                    backtest_data["equity_curve"] = equity_curve
                
                # Load final positions if available
                final_positions = self.get_final_positions(run_id)
                if final_positions is not None:
                    backtest_data["final_positions"] = final_positions
                
                # Load symbol PnL if available
                symbol_pnl = self.get_symbol_pnl(run_id)
                if symbol_pnl is not None:
                    backtest_data["symbol_pnl"] = symbol_pnl
                
                return backtest_data
        except Exception as e:
            self.logger.error(f"Error loading complete backtest for run_id '{run_id}': {e}")
            return None
