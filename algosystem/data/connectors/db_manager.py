import logging
from typing import Any, Dict

from dotenv import load_dotenv

from algosystem.data.connectors.base_db_manager import BaseDBManager
from algosystem.data.connectors.loader_manager import LoaderManager
from algosystem.data.connectors.deleter_manager import DeleterManager
from algosystem.data.connectors.inserter_manager import InserterManager

# Load environment variables
load_dotenv()

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