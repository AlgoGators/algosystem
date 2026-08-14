"""Market-data domain ports."""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from algosystem.shared.values import DateRange

from .benchmark import Ticker


class BenchmarkProvider(Protocol):
    """Port for fetching benchmark prices from an external data source."""

    def fetch(self, ticker: Ticker, date_range: DateRange) -> pd.Series:
        """Fetch benchmark prices for the requested date range."""
        ...


class BenchmarkCache(Protocol):
    """Port for benchmark price caching."""

    def has(self, alias: str, date_range: DateRange) -> bool:
        """Return whether the cache can satisfy the requested date range."""
        ...

    def get(self, alias: str, date_range: DateRange) -> pd.Series:
        """Return cached benchmark prices for the requested date range."""
        ...

    def put(self, alias: str, prices: pd.Series) -> None:
        """Persist benchmark prices for later reads."""
        ...


__all__ = ["BenchmarkCache", "BenchmarkProvider"]
