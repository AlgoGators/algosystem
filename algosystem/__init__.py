"""AlgoSystem public API."""

from __future__ import annotations

from importlib import import_module

from algosystem.shared.errors import (
    AlgoSystemError,
    DomainError,
    MarketDataError,
    RepositoryError,
    ValidationError,
)
from algosystem.shared.metric_key import MetricKey

__version__ = "0.1.9"

_LAZY_EXPORTS = {
    "AlgoSystem": ("algosystem.interfaces.api", "AlgoSystem"),
    "Backtest": ("algosystem.backtesting.domain.backtest", "Backtest"),
    "BacktestResult": ("algosystem.backtesting.domain.backtest", "BacktestResult"),
    "DateRange": ("algosystem.shared.values", "DateRange"),
    "Engine": ("algosystem.backtesting.engine", "Engine"),
    "EquityCurve": ("algosystem.backtesting.domain.equity_curve", "EquityCurve"),
    "Money": ("algosystem.shared.values", "Money"),
    "PerformanceMetrics": (
        "algosystem.backtesting.domain.metrics",
        "PerformanceMetrics",
    ),
    "Percent": ("algosystem.shared.values", "Percent"),
    "Ratio": ("algosystem.shared.values", "Ratio"),
    "RunId": ("algosystem.shared.values", "RunId"),
    "OverfitResults": ("algosystem.validation.domain.results", "OverfitResults"),
    "ParameterGrid": ("algosystem.validation.domain.strategy", "ParameterGrid"),
    "StrategySpec": ("algosystem.validation.domain.strategy", "StrategySpec"),
    "ValidationMetricKey": (
        "algosystem.validation.domain.validation_metric",
        "ValidationMetricKey",
    ),
    "detect_overfitting": ("algosystem.interfaces.api", "detect_overfitting"),
    "quick_backtest": ("algosystem.interfaces.api", "quick_backtest"),
    "run_backtest": ("algosystem.interfaces.api", "run_backtest"),
}


def __getattr__(name: str) -> object:
    if name in _LAZY_EXPORTS:
        module_name, attribute = _LAZY_EXPORTS[name]
        module = import_module(module_name)
        value = getattr(module, attribute)
        globals()[name] = value
        return value
    raise AttributeError(f"module 'algosystem' has no attribute {name!r}")


__all__ = [
    "AlgoSystem",
    "AlgoSystemError",
    "Backtest",
    "BacktestResult",
    "DateRange",
    "DomainError",
    "Engine",
    "EquityCurve",
    "MarketDataError",
    "MetricKey",
    "Money",
    "Percent",
    "PerformanceMetrics",
    "Ratio",
    "RepositoryError",
    "RunId",
    "OverfitResults",
    "ParameterGrid",
    "StrategySpec",
    "ValidationError",
    "ValidationMetricKey",
    "__version__",
    "detect_overfitting",
    "quick_backtest",
    "run_backtest",
]
