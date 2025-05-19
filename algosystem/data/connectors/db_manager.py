"""
Enhanced DBManager with database initialization functionality.
This module extends the DBManager class with methods for creating and managing database tables.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union

from algosystem.data.connectors.base_db_manager import BaseDBManager
from algosystem.data.connectors.deleter_manager import DeleterManager
from algosystem.data.connectors.inserter_manager import InserterManager
from algosystem.data.connectors.loader_manager import LoaderManager

class DBManager(LoaderManager, DeleterManager, InserterManager):
    """
    Main database manager class that inherits from all specialized managers
    to provide a unified interface for all database operations.
    """
    
    def __init__(self) -> None:
        """Initialize the database manager."""
        # Initialize parent classes
        BaseDBManager.__init__(self)
        
        self.logger = logging.getLogger("DBManager")
        self.logger.setLevel(logging.INFO)
    
    def create_backtest_table(self) -> bool:
        """
        Create the necessary database schema and tables for backtest data if they don't exist.
        
        Returns:
            bool: True if operation was successful, False otherwise
        """
        self._connect_psycopg2()
        
        try:
            # SQL script to create all required tables
            create_tables_sql = """
            -- Create backtest schema if it doesn't exist
            CREATE SCHEMA IF NOT EXISTS backtest;

            -- Run metadata table for storing backtest metadata
            CREATE TABLE IF NOT EXISTS backtest.run_metadata (
                run_id          BIGINT PRIMARY KEY, 
                name            VARCHAR NOT NULL,
                description     TEXT,
                hyperparameters JSONB,
                date_inserted   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

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
            """
            
            # Execute the SQL script
            with self.conn.cursor() as cur:
                cur.execute(create_tables_sql)
            
            self.conn.commit()
            self.logger.info("Successfully created backtest schema and tables")
            return True
            
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error creating backtest tables: {e}")
            return False
    
    def get_backtest_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the backtest data in the database.
        
        Returns:
            Dict[str, Any]: Dictionary with statistics
        """
        self._connect_psycopg2()
        
        try:
            stats = {}
            
            with self.conn.cursor() as cur:
                # Count total backtests
                cur.execute("SELECT COUNT(*) FROM backtest.run_metadata")
                stats["total_backtests"] = cur.fetchone()[0]
                
                # Count unique backtest names
                cur.execute("SELECT COUNT(DISTINCT name) FROM backtest.run_metadata")
                stats["unique_names"] = cur.fetchone()[0]
                
                # Get date range of backtests
                cur.execute("SELECT MIN(date_inserted), MAX(date_inserted) FROM backtest.run_metadata")
                first_date, last_date = cur.fetchone()
                if first_date and last_date:
                    stats["first_backtest"] = first_date
                    stats["last_backtest"] = last_date
                    stats["days_span"] = (last_date - first_date).days
                
                # Count backtest components
                cur.execute("SELECT COUNT(*) FROM backtest.equity_curve")
                stats["equity_curve_records"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM backtest.final_positions")
                stats["position_records"] = cur.fetchone()[0]
                
                cur.execute("SELECT COUNT(*) FROM backtest.symbol_pnl")
                stats["pnl_records"] = cur.fetchone()[0]
                
                # Get performance stats if available
                cur.execute("""
                    SELECT 
                        AVG(total_return), MIN(total_return), MAX(total_return),
                        AVG(sharpe_ratio), AVG(max_drawdown)
                    FROM backtest.results
                    WHERE total_return IS NOT NULL
                """)
                
                avg_return, min_return, max_return, avg_sharpe, avg_drawdown = cur.fetchone()
                
                if avg_return is not None:
                    stats["avg_return"] = float(avg_return)
                    stats["min_return"] = float(min_return)
                    stats["max_return"] = float(max_return)
                    stats["avg_sharpe"] = float(avg_sharpe) if avg_sharpe else None
                    stats["avg_drawdown"] = float(avg_drawdown) if avg_drawdown else None
                
            return stats
                
        except Exception as e:
            self.logger.error(f"Error getting backtest stats: {e}")
            return {"error": str(e)}
    
    def compare_backtests(self, run_ids: List[Union[str, int]]) -> Dict[str, Any]:
        """
        Compare multiple backtests by their run IDs.
        
        Args:
            run_ids (List[Union[str, int]]): List of run IDs to compare
            
        Returns:
            Dict[str, Any]: Dictionary with comparison data
        """
        if not run_ids:
            return {"error": "No run IDs provided for comparison"}
        
        self._connect_psycopg2()
        
        try:
            # Convert all run_ids to strings for the SQL query
            run_ids_str = ", ".join([f"'{str(run_id)}'" for run_id in run_ids])
            
            # Get backtest metadata and metrics
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    SELECT rm.run_id, rm.name, rm.date_inserted, 
                           r.total_return, r.sharpe_ratio, r.max_drawdown, r.beta
                    FROM backtest.run_metadata rm
                    JOIN backtest.results r ON rm.run_id = r.run_id
                    WHERE rm.run_id IN ({run_ids_str})
                    ORDER BY rm.date_inserted DESC
                """)
                
                columns = [desc[0] for desc in cur.description]
                results = cur.fetchall()
                
                if not results:
                    return {"error": "No matching backtests found with the provided run IDs"}
                
                backtests = [dict(zip(columns, row)) for row in results]
                
            # Get equity curves for plotting
            equity_curves = {}
            for run_id in run_ids:
                equity_curve = self.get_equity_curve(run_id)
                if equity_curve is not None:
                    equity_curves[str(run_id)] = equity_curve
            
            return {
                "backtests": backtests,
                "equity_curves": equity_curves
            }
                
        except Exception as e:
            self.logger.error(f"Error comparing backtests: {e}")
            return {"error": str(e)}
    
    def find_best_backtest(self, metric="sharpe_ratio", limit=5) -> List[Dict[str, Any]]:
        """
        Find the best performing backtests based on a specific metric.
        
        Args:
            metric (str): Metric to sort by (default: sharpe_ratio)
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of backtest data sorted by the metric
        """
        self._connect_psycopg2()
        
        # Validate metric name for SQL injection prevention (simple version)
        valid_metrics = [
            "total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown", 
            "calmar_ratio", "volatility", "win_rate", "information_ratio"
        ]
        
        if metric not in valid_metrics:
            self.logger.warning(f"Invalid metric: {metric}. Using sharpe_ratio instead.")
            metric = "sharpe_ratio"
        
        try:
            with self.conn.cursor() as cur:
                # For drawdown and volatility, we want the lowest values (ASC)
                # For other metrics, we want the highest values (DESC)
                sort_direction = "ASC" if metric in ["max_drawdown", "volatility"] else "DESC"
                
                query = f"""
                    SELECT rm.run_id, rm.name, rm.date_inserted, 
                           r.total_return, r.sharpe_ratio, r.{metric}
                    FROM backtest.run_metadata rm
                    JOIN backtest.results r ON rm.run_id = r.run_id
                    WHERE r.{metric} IS NOT NULL
                    ORDER BY r.{metric} {sort_direction}
                    LIMIT %s
                """
                
                cur.execute(query, (limit,))
                
                columns = [desc[0] for desc in cur.description]
                results = cur.fetchall()
                
                return [dict(zip(columns, row)) for row in results]
                
        except Exception as e:
            self.logger.error(f"Error finding best backtest: {e}")
            return []
    
    def search_backtests(self, query: str, field: str = "name") -> List[Dict[str, Any]]:
        """
        Search for backtests matching a query.
        
        Args:
            query (str): Search query
            field (str, optional): Field to search in (name, description). Defaults to "name".
            
        Returns:
            List[Dict[str, Any]]: List of matching backtests
        """
        self._connect_psycopg2()
        
        # Validate field name for SQL injection prevention
        valid_fields = ["name", "description", "run_id"]
        if field not in valid_fields:
            self.logger.warning(f"Invalid field: {field}. Using name instead.")
            field = "name"
        
        try:
            with self.conn.cursor() as cur:
                if field == "run_id":
                    # Exact match for run_id
                    cur.execute("""
                        SELECT run_id, name, description, date_inserted
                        FROM backtest.run_metadata
                        WHERE run_id = %s
                        ORDER BY date_inserted DESC
                    """, (query,))
                else:
                    # Pattern match for name or description
                    search_pattern = f"%{query}%"
                    cur.execute(f"""
                        SELECT run_id, name, description, date_inserted
                        FROM backtest.run_metadata
                        WHERE {field} ILIKE %s
                        ORDER BY date_inserted DESC
                    """, (search_pattern,))
                
                columns = [desc[0] for desc in cur.description]
                results = cur.fetchall()
                
                return [dict(zip(columns, row)) for row in results]
                
        except Exception as e:
            self.logger.error(f"Error searching backtests: {e}")
            return []
    
    def get_backtest_summary(self, run_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get a comprehensive summary of a backtest.
        
        Args:
            run_id (Union[str, int]): ID of the backtest run
            
        Returns:
            Optional[Dict[str, Any]]: Dictionary with backtest summary or None if not found
        """
        self._connect_psycopg2()
        
        try:
            # Load basic metadata and results
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
                    return None
                
                summary = dict(zip(columns, result))
            
            # Add counts for related data
            with self.conn.cursor() as cur:
                # Count equity curve points
                cur.execute("SELECT COUNT(*) FROM backtest.equity_curve WHERE run_id = %s", (run_id,))
                summary["equity_points"] = cur.fetchone()[0]
                
                # Count positions
                cur.execute("SELECT COUNT(*) FROM backtest.final_positions WHERE run_id = %s", (run_id,))
                summary["position_count"] = cur.fetchone()[0]
                
                # Count symbol PnL entries
                cur.execute("SELECT COUNT(*) FROM backtest.symbol_pnl WHERE run_id = %s", (run_id,))
                summary["symbol_pnl_count"] = cur.fetchone()[0]
            
            # Parse JSON fields
            if "hyperparameters" in summary and summary["hyperparameters"]:
                try:
                    summary["hyperparameters"] = json.loads(summary["hyperparameters"])
                except:
                    pass
            
            if "config" in summary and summary["config"]:
                try:
                    summary["config"] = json.loads(summary["config"])
                except:
                    pass
            
            return summary
                
        except Exception as e:
            self.logger.error(f"Error getting backtest summary: {e}")
            return None