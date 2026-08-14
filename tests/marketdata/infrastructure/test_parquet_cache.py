import pandas as pd

from algosystem.marketdata.infrastructure.parquet_cache import ParquetBenchmarkCache
from algosystem.shared.values import DateRange


def test_parquet_cache_creates_directory_only_on_write(tmp_path):
    cache_dir = tmp_path / "benchmarks"
    cache = ParquetBenchmarkCache(cache_dir)
    date_range = DateRange(pd.Timestamp("2020-01-01"), pd.Timestamp("2020-01-03"))

    assert not cache_dir.exists()
    assert cache.has("sp500", date_range) is False

    cache.put(
        "sp500",
        pd.Series([100.0, 101.0, 102.0], index=pd.date_range("2020-01-01", periods=3)),
    )

    assert cache_dir.exists()
    assert cache.has("sp500", date_range) is True
    assert cache.get("sp500", date_range).tolist() == [100.0, 101.0, 102.0]
