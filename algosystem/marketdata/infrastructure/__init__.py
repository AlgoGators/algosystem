"""Market-data infrastructure adapters."""

from __future__ import annotations

from importlib import import_module


def __getattr__(name: str) -> object:
    if name == "ParquetBenchmarkCache":
        module = import_module(".parquet_cache", __name__)
        return module.ParquetBenchmarkCache
    if name == "YFinanceBenchmarkProvider":
        module = import_module(".yfinance_provider", __name__)
        return module.YFinanceBenchmarkProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ParquetBenchmarkCache", "YFinanceBenchmarkProvider"]
