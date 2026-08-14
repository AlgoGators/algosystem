"""SQLAlchemy schema for persisted backtest runs."""

from __future__ import annotations

import re

from sqlalchemy import Column, Date, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.schema import CreateSchema

from algosystem.shared.errors import ConfigurationError
from algosystem.shared.metric_key import MetricKey

DEFAULT_SCHEMA = "backtest"
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

Base = declarative_base()


class RunMetadata(Base):
    """Metadata for a persisted backtest run."""

    __tablename__ = "run_metadata"
    __table_args__ = {"schema": DEFAULT_SCHEMA}

    run_id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    hyperparameters = Column(JSONB)
    date_inserted = Column(DateTime, nullable=False, server_default=func.now())


class EquityCurve(Base):
    """Equity curve points for a run."""

    __tablename__ = "equity_curve"
    __table_args__ = {"schema": DEFAULT_SCHEMA}

    run_id = Column(String, primary_key=True, nullable=False)
    timestamp = Column(DateTime, primary_key=True, nullable=False)
    equity = Column(Float, nullable=False)


class Result(Base):
    """Performance metrics for a run."""

    __tablename__ = "results"
    __table_args__ = {"schema": DEFAULT_SCHEMA}

    run_id = Column(String, primary_key=True, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    config = Column(JSONB)


for metric_key in MetricKey:
    setattr(Result, metric_key.value, Column(Float))


class FinalPosition(Base):
    """Final holdings for a run."""

    __tablename__ = "final_positions"
    __table_args__ = {"schema": DEFAULT_SCHEMA}

    run_id = Column(String, primary_key=True, nullable=False)
    symbol = Column(String, primary_key=True, nullable=False)
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)


class SymbolPnl(Base):
    """Symbol-level PnL for a run."""

    __tablename__ = "symbol_pnl"
    __table_args__ = {"schema": DEFAULT_SCHEMA}

    run_id = Column(String, primary_key=True, nullable=False)
    symbol = Column(String, primary_key=True, nullable=False)
    pnl = Column(Float, nullable=False)


def create_all(engine: Engine, schema: str = DEFAULT_SCHEMA) -> None:
    """Create the persistence schema and tables if they do not already exist."""
    _validate_schema(schema)
    translated = engine.execution_options(schema_translate_map={DEFAULT_SCHEMA: schema})
    with translated.begin() as connection:
        if not connection.dialect.has_schema(connection, schema):
            connection.execute(CreateSchema(schema))
        Base.metadata.create_all(connection)


def _validate_schema(schema: str) -> None:
    if schema is None or str(schema).strip() == "":
        raise ConfigurationError("missing database config field: schema")
    if _IDENTIFIER_RE.fullmatch(str(schema)) is None:
        raise ConfigurationError("schema must be a valid SQL identifier")
