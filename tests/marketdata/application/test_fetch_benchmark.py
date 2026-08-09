import pandas as pd

from algosystem.marketdata.application import FetchBenchmark
from algosystem.marketdata.domain.benchmark import STANDARD_CATALOG, Ticker
from algosystem.shared.values import DateRange


class FakeProvider:
    def __init__(self, prices):
        self.prices = prices
        self.calls = []

    def fetch(self, ticker: Ticker, date_range: DateRange):
        self.calls.append((ticker, date_range))
        return self.prices


class FakeCache:
    def __init__(self, prices=None):
        self.prices = prices
        self.writes = []

    def has(self, alias: str, date_range: DateRange):
        return self.prices is not None

    def get(self, alias: str, date_range: DateRange):
        return self.prices

    def put(self, alias: str, prices: pd.Series):
        self.writes.append((alias, prices.copy()))
        self.prices = prices.copy()


def prices():
    return pd.Series(
        [100.0, 101.0, 102.0],
        index=pd.date_range("2020-01-01", periods=3, freq="D"),
        name="prices",
    )


def test_fetch_benchmark_returns_cached_equity_curve_without_fetching():
    provider = FakeProvider(prices())
    cache = FakeCache(prices())

    curve = FetchBenchmark(provider, cache, STANDARD_CATALOG).execute(
        "sp500", start="2020-01-01", end="2020-01-03"
    )

    assert curve.values.iloc[-1] == 102.0
    assert provider.calls == []
    assert cache.writes == []


def test_fetch_benchmark_fetches_and_writes_on_cache_miss():
    provider = FakeProvider(prices())
    cache = FakeCache()

    curve = FetchBenchmark(provider, cache, STANDARD_CATALOG).execute(
        "sp500", start="2020-01-01", end="2020-01-03"
    )

    assert curve.values.iloc[0] == 100.0
    assert provider.calls[0][0] == STANDARD_CATALOG.lookup("sp500").ticker
    assert cache.writes[0][0] == "sp500"
