"""Public benchmark market-data helpers."""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

from algosystem.marketdata.domain.benchmark import DEFAULT_BENCHMARK, STANDARD_CATALOG
from algosystem.marketdata.infrastructure.parquet_cache import default_cache_dir
from algosystem.shared.errors import MarketDataError
from algosystem.shared.metric_key import MetricKey

BENCHMARK_ALIASES = STANDARD_CATALOG.ticker_lookup()
BENCHMARK_DIR = str(default_cache_dir())


def get_benchmark_list() -> list[str]:
    """Return all available benchmark aliases."""
    return STANDARD_CATALOG.aliases()


def get_benchmark_info() -> pd.DataFrame:
    """Return benchmark aliases, categories, tickers, and descriptions."""
    return STANDARD_CATALOG.info_frame()


def get_benchmark_description(alias: str) -> str:
    """Return the benchmark description for an alias."""
    return STANDARD_CATALOG.lookup(alias).description


def get_benchmark_path(alias: str) -> str:
    """Return the default cache path for a benchmark alias."""
    STANDARD_CATALOG.lookup(alias)
    return str(default_cache_dir() / f"{alias}.parquet")


def fetch_benchmark_data(
    alias: str,
    start_date: object = None,
    end_date: object = None,
    force_refresh: bool = False,
) -> pd.Series:
    """Fetch benchmark prices by alias, using the parquet cache when possible."""
    curve = _default_fetcher().execute(
        alias=alias,
        start=start_date,
        end=end_date,
        force_refresh=force_refresh,
    )
    return curve.values.copy()


def fetch_all_benchmarks(
    start_date: object = None,
    end_date: object = None,
    force_refresh: bool = False,
) -> dict[str, pd.Series]:
    """Fetch all known benchmarks and return successful price series by alias."""
    results: dict[str, pd.Series] = {}
    for alias in get_benchmark_list():
        try:
            results[alias] = fetch_benchmark_data(alias, start_date, end_date, force_refresh)
        except MarketDataError:
            continue
    return results


def get_benchmark_returns(
    alias: str,
    start_date: object = None,
    end_date: object = None,
) -> pd.Series:
    """Return benchmark simple returns by alias."""
    prices = fetch_benchmark_data(alias, start_date, end_date)
    return prices.pct_change().dropna()


def compare_benchmarks(
    benchmarks: Sequence[str],
    start_date: object = None,
    end_date: object = None,
) -> pd.DataFrame:
    """Return normalized benchmark prices for comparison."""
    if not benchmarks:
        raise MarketDataError("at least one benchmark alias is required")

    normalized = {}
    for alias in benchmarks:
        prices = fetch_benchmark_data(alias, start_date, end_date)
        if prices.empty:
            raise MarketDataError(f"no benchmark prices available for alias: {alias}")
        normalized[alias] = 100 * (prices / prices.iloc[0])
    return pd.DataFrame(normalized)


def get_benchmark_metrics(
    alias: str,
    start_date: object = None,
    end_date: object = None,
) -> dict[str, float]:
    """Calculate basic performance metrics for a benchmark price series."""
    prices = fetch_benchmark_data(alias, start_date, end_date)
    returns = prices.pct_change().dropna()
    if returns.empty:
        raise MarketDataError(f"not enough benchmark data to calculate metrics: {alias}")

    total_return = float((prices.iloc[-1] / prices.iloc[0]) - 1)
    annualized_return = float((1 + total_return) ** (252 / len(returns)) - 1)
    annualized_volatility = float(returns.std() * np.sqrt(252))
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility else 0.0
    drawdown = (prices / prices.cummax()) - 1

    return {
        MetricKey.TOTAL_RETURN.value: total_return,
        MetricKey.ANNUALIZED_RETURN.value: annualized_return,
        MetricKey.ANNUALIZED_VOLATILITY.value: annualized_volatility,
        MetricKey.SHARPE_RATIO.value: float(sharpe_ratio),
        MetricKey.MAX_DRAWDOWN.value: float(drawdown.min()),
    }


def yield_to_price_index(yield_series: pd.Series) -> pd.Series:
    """Convert a yield series to an approximate price index."""
    yield_pct = yield_series / 100
    return 100 * (1 / yield_pct) / (1 / yield_pct.iloc[0])


def _default_fetcher() -> object:
    from algosystem.marketdata.application import FetchBenchmark
    from algosystem.marketdata.infrastructure import (
        ParquetBenchmarkCache,
        YFinanceBenchmarkProvider,
    )

    return FetchBenchmark(
        provider=YFinanceBenchmarkProvider(),
        cache=ParquetBenchmarkCache(),
        catalog=STANDARD_CATALOG,
    )


__all__ = [
    "BENCHMARK_ALIASES",
    "BENCHMARK_DIR",
    "DEFAULT_BENCHMARK",
    "compare_benchmarks",
    "fetch_all_benchmarks",
    "fetch_benchmark_data",
    "get_benchmark_description",
    "get_benchmark_info",
    "get_benchmark_list",
    "get_benchmark_metrics",
    "get_benchmark_path",
    "get_benchmark_returns",
    "yield_to_price_index",
]
