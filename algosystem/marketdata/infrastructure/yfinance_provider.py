"""YFinance benchmark provider adapter."""

from __future__ import annotations

import pandas as pd
import yfinance as yf

from algosystem.marketdata.domain.benchmark import Ticker
from algosystem.shared.errors import MarketDataError
from algosystem.shared.values import DateRange


class YFinanceBenchmarkProvider:
    """Benchmark provider backed by yfinance."""

    def fetch(self, ticker: Ticker, date_range: DateRange) -> pd.Series:
        """Fetch adjusted close prices from yfinance."""
        try:
            data = yf.download(
                ticker.value,
                start=date_range.start,
                end=date_range.end + pd.Timedelta(days=1),
                progress=False,
            )
            prices = _select_price_series(data, ticker)
        except MarketDataError:
            raise
        except Exception as exc:
            raise MarketDataError(f"failed to fetch benchmark data for {ticker.value}") from exc

        prices = prices.loc[date_range.mask(prices.index)]
        if prices.empty:
            raise MarketDataError(f"no benchmark data returned for {ticker.value}")
        prices.name = ticker.value
        return prices


def _select_price_series(data: pd.DataFrame, ticker: Ticker) -> pd.Series:
    if data.empty:
        raise MarketDataError(f"no benchmark data returned for {ticker.value}")

    if isinstance(data.columns, pd.MultiIndex):
        for field in ("Adj Close", "Close"):
            if field in data.columns.get_level_values(0):
                selected = data[field]
                if isinstance(selected, pd.DataFrame):
                    return _normalize(selected.iloc[:, 0], ticker)
                return _normalize(selected, ticker)
        raise MarketDataError(f"yfinance response has no close prices for {ticker.value}")

    for field in ("Adj Close", "Close"):
        if field in data.columns:
            return _normalize(data[field], ticker)
    raise MarketDataError(f"yfinance response has no close prices for {ticker.value}")


def _normalize(prices: pd.Series, ticker: Ticker) -> pd.Series:
    series = prices.copy().sort_index()
    if not isinstance(series.index, pd.DatetimeIndex):
        raise MarketDataError(f"yfinance response index is not datetime for {ticker.value}")
    if series.index.tz is not None:
        series.index = series.index.tz_convert(None)
    try:
        series = series.astype(float)
    except (TypeError, ValueError) as exc:
        raise MarketDataError(f"yfinance returned non-numeric prices for {ticker.value}") from exc
    series = series.dropna()
    if series.empty:
        raise MarketDataError(f"no usable benchmark prices returned for {ticker.value}")
    return series


__all__ = ["YFinanceBenchmarkProvider"]
