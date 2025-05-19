import os
import psycopg2
import getpass
from typing import Optional, List, Union, Dict, Any
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")


class Deleter:
    """
    A class for deleting data from the backtest database.
    Provides methods to clear all tables, delete specific entries or ranges of entries.
    All operations require password confirmation.
    """

    def __init__(self):
        """Initialize the Deleter class by loading database connection parameters."""
        # Load environment variables from .env file
        load_dotenv()
        
        # Set up logging
        self.logger = logging.getLogger("Deleter")
        
        # Database connection parameters
        self.db_params = {
            "dbname": os.getenv("DB_NAME"),
            "user": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST"),
            "port": os.getenv("DB_PORT"),
        }
        
        # Connection object
        self.conn = None

    def connect(self):
        """Connect to the database."""
        try:
            if self.conn is None or self.conn.closed:
                self.logger.info("Opening new database connection")
                self.conn = psycopg2.connect(**self.db_params)
            return True
        except Exception as e:
            self.logger.error(f"Error connecting to database: {e}")
            raise

    def close(self):
        """Close the database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.logger.info("Database connection closed")

    def _verify_password(self, message: str = "Enter database password to confirm deletion: ") -> bool:
        """
        Verify user password before deletion operations.
        
        Args:
            message: Custom message to display when asking for password
            
        Returns:
            bool: True if password is correct, False otherwise
        """
        try:
            entered_password = getpass.getpass(message)
            if entered_password == self.db_params["password"]:
                return True
            else:
                self.logger.error("Incorrect password. Operation aborted.")
                return False
        except Exception as e:
            self.logger.error(f"Error during password verification: {e}")
            return False

    def clear_all_tables(self, confirm: bool = True) -> bool:
        """
        Clear all tables in the backtest schema.
        
        Args:
            confirm: Whether to ask for password confirmation
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        if confirm and not self._verify_password("⚠️ WARNING: This will delete ALL backtest data! Enter password to confirm: "):
            return False
            
        self.connect()
        try:
            with self.conn.cursor() as cursor:
                # Start a transaction
                self.conn.autocommit = False
                
                # Delete from all tables in the correct order to respect foreign key constraints
                cursor.execute("DELETE FROM backtest.equity_curve")
                cursor.execute("DELETE FROM backtest.final_positions")
                cursor.execute("DELETE FROM backtest.symbol_pnl")
                cursor.execute("DELETE FROM backtest.run_metadata")
                cursor.execute("DELETE FROM backtest.results")
                
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
            self.close()

    def delete_last_entry(self, confirm: bool = True) -> bool:
        """
        Delete the most recent backtest entry.
        
        Args:
            confirm: Whether to ask for password confirmation
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        self.connect()
        try:
            # First get the latest run_id
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT run_id, name 
                    FROM backtest.run_metadata 
                    ORDER BY date_inserted DESC 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                
                if result is None:
                    self.logger.info("No backtest entries found to delete")
                    return False
                    
                run_id, name = result
                
                if confirm:
                    confirm_message = f"Are you sure you want to delete the most recent backtest '{name}' (ID: {run_id})? Enter password to confirm: "
                    if not self._verify_password(confirm_message):
                        return False
                
                # Start a transaction
                self.conn.autocommit = False
                
                # Delete from all tables in the correct order
                cursor.execute("DELETE FROM backtest.equity_curve WHERE run_id = %s", (run_id,))
                cursor.execute("DELETE FROM backtest.final_positions WHERE run_id = %s", (run_id,))
                cursor.execute("DELETE FROM backtest.symbol_pnl WHERE run_id = %s", (run_id,))
                cursor.execute("DELETE FROM backtest.run_metadata WHERE run_id = %s", (run_id,))
                cursor.execute("DELETE FROM backtest.results WHERE run_id = %s", (run_id,))
                
                # Commit the transaction
                self.conn.commit()
                self.logger.info(f"Deleted backtest '{name}' (ID: {run_id})")
                return True
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error deleting last entry: {e}")
            return False
        finally:
            self.conn.autocommit = True
            self.close()

    def delete_last_n_entries(self, n: int, confirm: bool = True) -> bool:
        """
        Delete the n most recent backtest entries.
        
        Args:
            n: Number of most recent entries to delete
            confirm: Whether to ask for password confirmation
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        if n <= 0:
            self.logger.error("Number of entries to delete must be positive")
            return False
            
        self.connect()
        try:
            # First get the latest run_ids
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT run_id, name 
                    FROM backtest.run_metadata 
                    ORDER BY date_inserted DESC 
                    LIMIT %s
                """, (n,))
                results = cursor.fetchall()
                
                if not results:
                    self.logger.info("No backtest entries found to delete")
                    return False
                
                if confirm:
                    names = [f"'{name}' (ID: {run_id})" for run_id, name in results]
                    entries_str = ", ".join(names)
                    confirm_message = f"Are you sure you want to delete the {len(results)} most recent backtests: {entries_str}? Enter password to confirm: "
                    if not self._verify_password(confirm_message):
                        return False
                
                # Start a transaction
                self.conn.autocommit = False
                
                # Get the run_ids to delete
                run_ids = [r[0] for r in results]
                run_ids_str = ",".join([f"'{r}'" for r in run_ids])
                
                # Delete from all tables in the correct order
                cursor.execute(f"DELETE FROM backtest.equity_curve WHERE run_id IN ({run_ids_str})")
                cursor.execute(f"DELETE FROM backtest.final_positions WHERE run_id IN ({run_ids_str})")
                cursor.execute(f"DELETE FROM backtest.symbol_pnl WHERE run_id IN ({run_ids_str})")
                cursor.execute(f"DELETE FROM backtest.run_metadata WHERE run_id IN ({run_ids_str})")
                cursor.execute(f"DELETE FROM backtest.results WHERE run_id IN ({run_ids_str})")
                
                # Commit the transaction
                self.conn.commit()
                self.logger.info(f"Deleted {len(results)} backtest entries")
                return True
                
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error deleting last {n} entries: {e}")
            return False
        finally:
            self.conn.autocommit = True
            self.close()

    def delete_by_name(self, name: str, confirm: bool = True) -> bool:
        """
        Delete backtest entries that match the specified name.
        
        Args:
            name: Name of the backtest to delete
            confirm: Whether to ask for password confirmation
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        self.connect()
        try:
            # First find the run_ids that match the name
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT run_id, name 
                    FROM backtest.run_metadata 
                    WHERE name = %s
                    ORDER BY date_inserted DESC
                """, (name,))
                results = cursor.fetchall()
                
                if not results:
                    self.logger.info(f"No backtest entries found with name '{name}'")
                    return False
                
                if confirm:
                    confirm_message = f"Are you sure you want to delete {len(results)} backtest entries with name '{name}'? Enter password to confirm: "
                    if not self._verify_password(confirm_message):
                        return False
                
                # Start a transaction
                self.conn.autocommit = False
                
                # Get the run_ids to delete
                run_ids = [r[0] for r in results]
                run_ids_str = ",".join([f"'{r}'" for r in run_ids])
                
                # Delete from all tables in the correct order
                cursor.execute(f"DELETE FROM backtest.equity_curve WHERE run_id IN ({run_ids_str})")
                cursor.execute(f"DELETE FROM backtest.final_positions WHERE run_id IN ({run_ids_str})")
                cursor.execute(f"DELETE FROM backtest.symbol_pnl WHERE run_id IN ({run_ids_str})")
                cursor.execute(f"DELETE FROM backtest.run_metadata WHERE run_id IN ({run_ids_str})")
                cursor.execute(f"DELETE FROM backtest.results WHERE run_id IN ({run_ids_str})")
                
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
            self.close()
            
    def delete_by_run_id(self, run_id: Union[str, int], confirm: bool = True) -> bool:
        """
        Delete a backtest entry with the specified run_id.
        
        Args:
            run_id: ID of the backtest run to delete
            confirm: Whether to ask for password confirmation
            
        Returns:
            bool: True if operation was successful, False otherwise
        """
        self.connect()
        try:
            # First check if the run_id exists and get the name
            with self.conn.cursor() as cursor:
                cursor.execute("""
                    SELECT name 
                    FROM backtest.run_metadata 
                    WHERE run_id = %s
                """, (str(run_id),))
                result = cursor.fetchone()
                
                if result is None:
                    self.logger.info(f"No backtest entry found with run_id '{run_id}'")
                    return False
                    
                name = result[0]
                
                if confirm:
                    confirm_message = f"Are you sure you want to delete backtest '{name}' with run_id '{run_id}'? Enter password to confirm: "
                    if not self._verify_password(confirm_message):
                        return False
                
                # Start a transaction
                self.conn.autocommit = False
                
                # Delete from all tables in the correct order
                cursor.execute("DELETE FROM backtest.equity_curve WHERE run_id = %s", (run_id,))
                cursor.execute("DELETE FROM backtest.final_positions WHERE run_id = %s", (run_id,))
                cursor.execute("DELETE FROM backtest.symbol_pnl WHERE run_id = %s", (run_id,))
                cursor.execute("DELETE FROM backtest.run_metadata WHERE run_id = %s", (run_id,))
                cursor.execute("DELETE FROM backtest.results WHERE run_id = %s", (run_id,))
                
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
            self.close()


if __name__ == "__main__":
    # Example usage
    deleter = Deleter()
    
    # List all operations
    print("\nBacktest Database Cleanup Utility")
    print("================================")
    print("1. Delete last backtest entry")
    print("2. Delete last N backtest entries")
    print("3. Delete backtest by name")
    print("4. Delete backtest by run_id")
    print("5. Clear all tables (DANGER!)")
    print("0. Exit")
    
    choice = input("\nEnter option number: ")
    
    if choice == "1":
        deleter.delete_last_entry()
    elif choice == "2":
        n = int(input("Enter number of entries to delete: "))
        deleter.delete_last_n_entries(n)
    elif choice == "3":
        name = input("Enter backtest name to delete: ")
        deleter.delete_by_name(name)
    elif choice == "4":
        run_id = input("Enter run_id to delete: ")
        deleter.delete_by_run_id(run_id)
    elif choice == "5":
        print("\n⚠️ WARNING: This will delete ALL backtest data! ⚠️")
        confirm = input("Type 'DELETE ALL' to confirm: ")
        if confirm == "DELETE ALL":
            deleter.clear_all_tables()
        else:
            print("Operation cancelled.")
    elif choice == "0":
        print("Exiting.")
    else:
        print("Invalid option.")