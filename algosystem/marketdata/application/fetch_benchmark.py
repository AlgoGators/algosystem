"""Fetch-benchmark use case."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from algosystem.backtesting import EquityCurve
from algosystem.marketdata.domain.benchmark import STANDARD_CATALOG, BenchmarkCatalog
from algosystem.marketdata.domain.ports import BenchmarkCache, BenchmarkProvider
from algosystem.shared.errors import MarketDataError
from algosystem.shared.values import DateRange


class FetchBenchmark:
    """Use case for loading benchmark prices through a cache and provider."""

    def __init__(
        self,
        provider: BenchmarkProvider,
        cache: BenchmarkCache,
        catalog: Optional[BenchmarkCatalog] = None,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._catalog = catalog or STANDARD_CATALOG

    def execute(
        self,
        alias: str,
        start: object = None,
        end: object = None,
        force_refresh: bool = False,
    ) -> EquityCurve:
        """Return a benchmark equity curve for the requested alias and dates."""
        benchmark = self._catalog.lookup(alias)
        date_range = _coerce_date_range(start, end)

        if not force_refresh and self._cache.has(benchmark.alias, date_range):
            return EquityCurve.from_series(self._cache.get(benchmark.alias, date_range))

        prices = self._provider.fetch(benchmark.ticker, date_range)
        self._cache.put(benchmark.alias, prices)
        return EquityCurve.from_series(_slice_prices(prices, date_range))


def _coerce_date_range(start: object = None, end: object = None) -> DateRange:
    parsed_end = _coerce_timestamp(end) if end is not None else pd.Timestamp.now().normalize()
    parsed_start = (
        _coerce_timestamp(start) if start is not None else parsed_end - pd.Timedelta(days=365 * 20)
    )
    return DateRange(parsed_start, parsed_end)


def _coerce_timestamp(value: object) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(None)
    return timestamp


def _slice_prices(prices: pd.Series, date_range: DateRange) -> pd.Series:
    if not isinstance(prices, pd.Series):
        raise MarketDataError("benchmark provider returned a non-Series result")
    series = prices.copy().sort_index()
    if not isinstance(series.index, pd.DatetimeIndex):
        raise MarketDataError("benchmark prices must use a DatetimeIndex")
    if series.index.tz is not None:
        series.index = series.index.tz_convert(None)
    sliced = series.loc[date_range.mask(series.index)].dropna()
    if sliced.empty:
        raise MarketDataError("benchmark provider returned no prices for the requested range")
    return sliced


__all__ = ["FetchBenchmark"]
