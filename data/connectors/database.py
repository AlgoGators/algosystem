import pandas as pd
import numpy as np
import pickle
import os
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class BacktestResult(Base):
    """SQLAlchemy model for backtest results."""
    __tablename__ = 'backtest_results'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    strategy_type = Column(String)
    initial_capital = Column(Float)
    final_capital = Column(Float)
    total_return = Column(Float)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    data_binary = Column(LargeBinary)  # Stores serialized backtest results

class DatabaseConnector:
    """Connect to database for storing and retrieving backtest results."""
    
    def __init__(self, connection_string=None):
        """
        Initialize database connector.
        
        Parameters:
        -----------
        connection_string : str, optional
            Database connection string. If None, uses a local SQLite database.
        """
        if connection_string is None:
            # Default to a SQLite database in the user's home directory
            home_dir = os.path.expanduser("~")
            db_path = os.path.join(home_dir, ".algosystem", "algosystem.db")
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            connection_string = f"sqlite:///{db_path}"
        
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
    
    def push_backtest(self, results, name, description=None, strategy_type=None):
        """
        Store backtest results in the database.
        
        Parameters:
        -----------
        results : dict
            Dictionary containing backtest results
        name : str
            Unique name for the backtest
        description : str, optional
            Description of the backtest
        strategy_type : str, optional
            Type or category of the strategy
            
        Returns:
        --------
        id : int
            ID of the stored backtest
        """
        session = self.Session()
        
        try:
            # Serialize results dictionary
            serialized_results = pickle.dumps(results)
            
            # Create new backtest result record
            backtest = BacktestResult(
                name=name,
                description=description,
                strategy_type=strategy_type,
                initial_capital=results.get('initial_capital'),
                final_capital=results.get('final_capital'),
                total_return=results.get('returns'),
                sharpe_ratio=results.get('metrics', {}).get('sharpe_ratio'),
                max_drawdown=results.get('metrics', {}).get('max_drawdown'),
                data_binary=serialized_results
            )
            
            session.add(backtest)
            session.commit()
            
            backtest_id = backtest.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
        
        return backtest_id
    
    def get_backtest(self, backtest_id=None, name=None):
        """
        Retrieve backtest results from the database.
        
        Parameters:
        -----------
        backtest_id : int, optional
            ID of the backtest to retrieve
        name : str, optional
            Name of the backtest to retrieve
            
        Returns:
        --------
        results : dict
            Dictionary containing backtest results
        """
        if backtest_id is None and name is None:
            raise ValueError("Either backtest_id or name must be provided")
        
        session = self.Session()
        
        try:
            query = session.query(BacktestResult)
            
            if backtest_id is not None:
                query = query.filter(BacktestResult.id == backtest_id)
            elif name is not None:
                query = query.filter(BacktestResult.name == name)
            
            backtest = query.first()
            
            if backtest is None:
                return None
            
            # Deserialize the binary data
            results = pickle.loads(backtest.data_binary)
            
        finally:
            session.close()
        
        return results
    
    def list_backtests(self, strategy_type=None):
        """
        List available backtests.
        
        Parameters:
        -----------
        strategy_type : str, optional
            Filter by strategy type
            
        Returns:
        --------
        backtests : pandas.DataFrame
            DataFrame containing backtest metadata
        """
        session = self.Session()
        
        try:
            query = session.query(
                BacktestResult.id,
                BacktestResult.name,
                BacktestResult.description,
                BacktestResult.created_at,
                BacktestResult.strategy_type,
                BacktestResult.total_return,
                BacktestResult.sharpe_ratio,
                BacktestResult.max_drawdown
            )
            
            if strategy_type is not None:
                query = query.filter(BacktestResult.strategy_type == strategy_type)
            
            results = query.all()
            
            # Convert to DataFrame
            columns = ['id', 'name', 'description', 'created_at', 'strategy_type', 
                       'total_return', 'sharpe_ratio', 'max_drawdown']
            
            df = pd.DataFrame(results, columns=columns)
            
        finally:
            session.close()
        
        return df
    
    def delete_backtest(self, backtest_id=None, name=None):
        """
        Delete a backtest from the database.
        
        Parameters:
        -----------
        backtest_id : int, optional
            ID of the backtest to delete
        name : str, optional
            Name of the backtest to delete
            
        Returns:
        --------
        success : bool
            True if deletion was successful
        """
        if backtest_id is None and name is None:
            raise ValueError("Either backtest_id or name must be provided")
        
        session = self.Session()
        
        try:
            query = session.query(BacktestResult)
            
            if backtest_id is not None:
                query = query.filter(BacktestResult.id == backtest_id)
            elif name is not None:
                query = query.filter(BacktestResult.name == name)
            
            backtest = query.first()
            
            if backtest is None:
                return False
            
            session.delete(backtest)
            session.commit()
            
            return True
        
        except Exception as e:
            session.rollback()
            raise e
        
        finally:
            session.close()

# Quick helper functions
def push_to_db(results, name, description=None, strategy_type=None, connection_string=None):
    """Helper function to push backtest results to database."""
    connector = DatabaseConnector(connection_string)
    return connector.push_backtest(results, name, description, strategy_type)

def get_from_db(backtest_id=None, name=None, connection_string=None):
    """Helper function to retrieve backtest results from database."""
    connector = DatabaseConnector(connection_string)
    return connector.get_backtest(backtest_id, name)

def list_from_db(strategy_type=None, connection_string=None):
    """Helper function to list backtests in database."""
    connector = DatabaseConnector(connection_string)
    return connector.list_backtests(strategy_type)