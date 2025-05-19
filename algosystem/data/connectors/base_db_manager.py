import os
import logging
from typing import Optional
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from algosystem.data.connectors.db_models import get_engine


class BaseDBManager:
    """Base class for database operations with shared functionality."""
    
    def __init__(self) -> None:
        """Initialize the database manager with connection parameters."""
        # Set up logging
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.INFO)
        
        # Load and validate environment variables
        self.db_name = os.getenv("DB_NAME")
        self.db_user = os.getenv("DB_USER")
        self.db_pass = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")

        missing = [
            k
            for k, v in {
                "DB_NAME": self.db_name,
                "DB_USER": self.db_user,
                "DB_PASSWORD": self.db_pass,
                "DB_HOST": self.db_host,
                "DB_PORT": self.db_port,
            }.items()
            if not v
        ]

        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
        
        # Initialize SQLAlchemy engine
        self.engine: Optional[Engine] = None
        self.Session: Optional[sessionmaker] = None
        
        # Initialize psycopg2 connection for lower-level operations
        self.conn = None  # Will be initialized when needed
    
    def _init_sqlalchemy(self) -> None:
        """Initialize SQLAlchemy engine and session."""
        if self.engine is None:
            self.engine = get_engine()
            self.Session = sessionmaker(bind=self.engine)
    
    def _connect_psycopg2(self) -> None:
        """Establish a connection to the database using psycopg2."""
        try:
            import psycopg2
            if self.conn is None or self.conn.closed:
                self.logger.info("Opening new database connection")
                self.conn = psycopg2.connect(
                    dbname=self.db_name,
                    user=self.db_user,
                    password=self.db_pass,
                    host=self.db_host,
                    port=self.db_port,
                )
        except ImportError:
            raise ImportError("Required module 'psycopg2' not found. Install it with: pip install psycopg2-binary")
        except Exception as e:
            self.logger.error(f"Error connecting to database: {e}")
            raise
    
    def close(self) -> None:
        """Close database connections."""
        if self.conn and not self.conn.closed:
            self.conn.close()
            self.logger.info("Database connection closed")
