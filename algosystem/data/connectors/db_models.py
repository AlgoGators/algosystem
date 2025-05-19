import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine.base import Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

# Base class for SQLAlchemy models
Base = declarative_base()


class EquityCurve(Base):
    __tablename__ = "equity_curve"
    __table_args__ = {"schema": "backtest"}

    run_id = Column(BigInteger, primary_key=True, nullable=False)
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    equity = Column(Float, nullable=False)


class FinalPosition(Base):
    __tablename__ = "final_positions"
    __table_args__ = {"schema": "backtest"}

    run_id = Column(BigInteger, primary_key=True, nullable=False)
    symbol = Column(String, primary_key=True, nullable=False)
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)


class Result(Base):
    __tablename__ = "results"
    __table_args__ = {"schema": "backtest"}

    run_id = Column(BigInteger, primary_key=True, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_return = Column(Float)
    sharpe_ratio = Column(Float)
    sortino_ratio = Column(Float)
    max_drawdown = Column(Float)
    calmar_ratio = Column(Float)
    volatility = Column(Float)
    total_trades = Column(Integer)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    avg_win = Column(Float)
    avg_loss = Column(Float)
    max_win = Column(Float)
    max_loss = Column(Float)
    avg_holding_period = Column(Float)
    var_95 = Column(Float)
    cvar_95 = Column(Float)
    beta = Column(Float)
    correlation = Column(Float)
    downside_volatility = Column(Float)
    config = Column(JSONB)


class SymbolPnl(Base):
    __tablename__ = "symbol_pnl"
    __table_args__ = {"schema": "backtest"}

    run_id = Column(BigInteger, primary_key=True, nullable=False)
    symbol = Column(String, primary_key=True, nullable=False)
    pnl = Column(Float, nullable=False)


def get_engine() -> Engine:
    """
    Create and configure a SQLAlchemy Engine to connect to the TimescaleDB database.
    Database credentials are loaded from a `.env` file.

    Environment Variables:
        - DB_USER (str): The username for database authentication.
        - DB_PASSWORD (str): The password for database authentication.
        - DB_HOST (str): The database server hostname or IP.
        - DB_PORT (str): The port number for database access.
        - DB_NAME (str): The name of the database.

    Returns:
        Engine: A SQLAlchemy Engine object for database interactions.

    Raises:
        ValueError: If any required environment variable is missing.
    """
    # Load environment variables from .env file
    load_dotenv()

    # Retrieve database connection parameters from environment variables
    db_user: Optional[str] = os.getenv("DB_USER")
    db_password: Optional[str] = os.getenv("DB_PASSWORD")
    db_host: Optional[str] = os.getenv("DB_HOST")
    db_port: Optional[str] = os.getenv("DB_PORT")
    db_name: Optional[str] = os.getenv("DB_NAME")

    # Validate that all required parameters are present
    if not all([db_user, db_password, db_host, db_port, db_name]):
        raise ValueError(
            "One or more required environment variables are missing. "
            "Ensure DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, and DB_NAME are set in the .env file."
        )

    # Build the connection string
    connection_string: str = (
        f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    )

    # Create and return the SQLAlchemy Engine
    return create_engine(connection_string)


def get_session(engine: Engine) -> Session:
    """
    Create a new SQLAlchemy session for database interactions.

    Args:
        engine (Engine): A SQLAlchemy Engine object connected to the database.

    Returns:
        Session: A SQLAlchemy Session object for executing database queries.
    """
    SessionFactory = sessionmaker(bind=engine)
    return SessionFactory()
