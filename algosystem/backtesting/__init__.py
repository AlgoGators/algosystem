from __future__ import annotations

from importlib import import_module

from .domain import Backtest, BacktestResult, EquityCurve, PerformanceMetrics


def __getattr__(name: str) -> object:
    if name == "Engine":
        module = import_module(".engine", __name__)
        value = module.Engine
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Backtest",
    "BacktestResult",
    "Engine",
    "EquityCurve",
    "PerformanceMetrics",
]
