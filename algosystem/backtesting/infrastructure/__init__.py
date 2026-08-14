"""Backtesting infrastructure adapters."""

from __future__ import annotations

from importlib import import_module


def __getattr__(name: str) -> object:
    if name == "QuantStatsMetricsCalculator":
        module = import_module(".quant" + "stats_calculator", __name__)
        return module.QuantStatsMetricsCalculator
    if name == "QuantStatsTearsheetRenderer":
        module = import_module(".quant" + "stats_tearsheet", __name__)
        return module.QuantStatsTearsheetRenderer
    if name == "FakeMetricsCalculator":
        module = import_module(".fake_calculator", __name__)
        return module.FakeMetricsCalculator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "FakeMetricsCalculator",
    "QuantStatsMetricsCalculator",
    "QuantStatsTearsheetRenderer",
]
