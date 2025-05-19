from typing import Union
from algosystem.data.connectors.base_db_manager import BaseDBManager

class DeleterManager(BaseDBManager):
    """Class for deleting data from the database."""
    
    def delete_by_run_id(self, run_id: Union[str, int]) -> bool:
        """
        Delete a backtest entry with the specified run_id.
        
        Args:
            run_id (Union[str, int]): ID of the backtest run to delete
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        self._connect_psycopg2()
        try:
            # First check if the run_id exists and get the name
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT name 
                    FROM backtest.run_metadata 
                    WHERE run_id = %s
                """, (str(run_id),))
                result = cur.fetchone()
                
                if result is None:
                    self.logger.info(f"No backtest entry found with run_id '{run_id}'")
                    return False
                    
                name = result[0]
                
                # Start a transaction
                self.conn.autocommit = False
                
                # Delete from all tables in the correct order
                cur.execute("DELETE FROM backtest.equity_curve WHERE run_id = %s", (run_id,))
                cur.execute("DELETE FROM backtest.final_positions WHERE run_id = %s", (run_id,))
                cur.execute("DELETE FROM backtest.symbol_pnl WHERE run_id = %s", (run_id,))
                cur.execute("DELETE FROM backtest.run_metadata WHERE run_id = %s", (run_id,))
                cur.execute("DELETE FROM backtest.results WHERE run_id = %s", (run_id,))
                
                # Commit the transaction
                self.conn.commit()
                self.logger.info(f"Deleted backtest '{name}' with run_id '{run_id}'")
                return True
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error deleting entry with run_id '{run_id}': {e}")
            return False
        finally:
            self.conn.autocommit = True
    
    def delete_last_entry(self) -> bool:
        """
        Delete the most recent backtest entry.
        
        Returns:
            bool: True if operation was successful, False otherwise
        """
        self._connect_psycopg2()
        try:
            # First get the latest run_id
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT run_id, name 
                    FROM backtest.run_metadata 
                    ORDER BY date_inserted DESC 
                    LIMIT 1
                """)
                result = cur.fetchone()
                
                if result is None:
                    self.logger.info("No backtest entries found to delete")
                    return False
                    
                run_id, name = result
                
                # Delete using the run_id
                return self.delete_by_run_id(run_id)
                
        except Exception as e:
            self.logger.error(f"Error deleting last entry: {e}")
            return False
    
    def delete_by_name(self, name: str) -> bool:
        """
        Delete backtest entries that match the specified name.
        
        Args:
            name (str): Name of the backtest to delete
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        self._connect_psycopg2()
        try:
            # First find the run_ids that match the name
            with self.conn.cursor() as cur:
                cur.execute("""
                    SELECT run_id, name 
                    FROM backtest.run_metadata 
                    WHERE name = %s
                    ORDER BY date_inserted DESC
                """, (name,))
                results = cur.fetchall()
                
                if not results:
                    self.logger.info(f"No backtest entries found with name '{name}'")
                    return False
                
                # Start a transaction
                self.conn.autocommit = False
                
                # Get the run_ids to delete
                run_ids = [r[0] for r in results]
                run_ids_str = ",".join([f"'{r}'" for r in run_ids])
                
                # Delete from all tables in the correct order
                cur.execute(f"DELETE FROM backtest.equity_curve WHERE run_id IN ({run_ids_str})")
                cur.execute(f"DELETE FROM backtest.final_positions WHERE run_id IN ({run_ids_str})")
                cur.execute(f"DELETE FROM backtest.symbol_pnl WHERE run_id IN ({run_ids_str})")
                cur.execute(f"DELETE FROM backtest.run_metadata WHERE run_id IN ({run_ids_str})")
                cur.execute(f"DELETE FROM backtest.results WHERE run_id IN ({run_ids_str})")
                
                # Commit the transaction
                self.conn.commit()
                self.logger.info(f"Deleted {len(results)} backtest entries with name '{name}'")
                return True
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error deleting entries with name '{name}': {e}")
            return False
        finally:
            self.conn.autocommit = True
    
    def clear_all_tables(self) -> bool:
        """
        Clear all tables in the backtest schema.
        
        Returns:
            bool: True if operation was successful, False otherwise
        """
        self._connect_psycopg2()
        try:
            with self.conn.cursor() as cur:
                # Start a transaction
                self.conn.autocommit = False
                
                # Delete from all tables in the correct order to respect foreign key constraints
                cur.execute("DELETE FROM backtest.equity_curve")
                cur.execute("DELETE FROM backtest.final_positions")
                cur.execute("DELETE FROM backtest.symbol_pnl")
                cur.execute("DELETE FROM backtest.run_metadata")
                cur.execute("DELETE FROM backtest.results")
                
                # Commit the transaction
                self.conn.commit()
                self.logger.info("All tables in backtest schema have been cleared")
                return True
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error clearing tables: {e}")
            return False
        finally:
            self.conn.autocommit = True
