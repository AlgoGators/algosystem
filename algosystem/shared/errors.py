"""Typed exceptions shared across AlgoSystem contexts."""

from __future__ import annotations


class AlgoSystemError(Exception):
    """Base exception for all AlgoSystem failures."""


class DomainError(AlgoSystemError, ValueError):
    """Raised when a domain invariant is violated."""


class ValidationError(DomainError):
    """Raised when validation-domain input or state is invalid."""


class InvalidPriceSeriesError(DomainError):
    """Raised when a price series is empty, invalid, or not usable."""


class InvalidDateRangeError(DomainError):
    """Raised when a requested date range is invalid or empty."""


class InsufficientDataError(DomainError):
    """Raised when there is not enough data to perform a calculation."""


class InvalidCapitalError(DomainError):
    """Raised when capital or money input is invalid."""


class CalculationError(AlgoSystemError):
    """Raised when a metric or derived value cannot be computed."""


class RepositoryError(AlgoSystemError):
    """Raised when persistence fails."""


class RunNotFoundError(RepositoryError):
    """Raised when a persisted run cannot be found."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Backtest run not found: {run_id}")


class DuplicateRunError(RepositoryError):
    """Raised when a run id already exists."""

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"Backtest run already exists: {run_id}")


class MarketDataError(AlgoSystemError):
    """Raised when benchmark fetch or cache operations fail."""


class UnknownBenchmarkError(MarketDataError):
    """Raised when a benchmark alias is not known."""


class ConfigurationError(AlgoSystemError):
    """Raised when required configuration is missing or invalid."""
