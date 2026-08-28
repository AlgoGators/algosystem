"""Legacy Engine shim."""

from __future__ import annotations

import warnings
from typing import Optional

import pandas as pd

from algosystem.backtesting.application.run_backtest import (
    coerce_capital,
    coerce_date_range,
    coerce_equity_curve,
)
from algosystem.backtesting.domain import Backtest
from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.shared.logging import get_logger

from . import infrastructure

logger = get_logger(__name__)


class Engine:
    """Deprecated compatibility wrapper around Backtest."""

    def __init__(
        self,
        data: object,
        benchmark: object = None,
        start_date: object = None,
        end_date: object = None,
        initial_capital: object = None,
        price_column: Optional[str] = None,
    ) -> None:
        warnings.warn(
            "Engine is deprecated and will be removed in a future release; use Backtest.",
            DeprecationWarning,
            stacklevel=2,
        )

        equity_curve = coerce_equity_curve(data, price_column)
        benchmark_curve = coerce_equity_curve(benchmark, None) if benchmark is not None else None
        date_range = coerce_date_range(start_date, end_date, equity_curve)
        capital = coerce_capital(initial_capital)

        self._backtest = Backtest(
            equity_curve=equity_curve,
            benchmark=benchmark_curve,
            date_range=date_range,
            initial_capital=capital,
        )
        self.price_series = self._backtest.equity_curve.values
        self.benchmark_series = (
            self._backtest.benchmark_curve.values
            if self._backtest.benchmark_curve is not None
            else None
        )
        self.start_date = self._backtest.date_range.start
        self.end_date = self._backtest.date_range.end
        self.initial_capital = self._backtest.initial_capital.amount
        self.results = None
        self.metrics_data = None
        self.plots = None
        self.backtest_result: Optional[BacktestResult] = None

        logger.info("Initialized backtest from %s to %s", self.start_date, self.end_date)

    def run(self) -> dict[str, object]:
        """Run the backtest through the new domain model."""
        logger.info("Starting backtest simulation")
        calculator = infrastructure.QuantStatsMetricsCalculator()
        result = self._backtest.run(calculator)
        legacy = result.to_legacy_dict()
        legacy["data"] = self.price_series

        self.backtest_result = result
        self.results = legacy
        self.metrics_data = legacy["metrics"]
        self.plots = legacy["plots"]
        logger.info("Backtest completed. Final return: %.2f%%", legacy["returns"] * 100)
        return legacy

    def get_results(self) -> dict[str, object]:
        """Get the full results dictionary."""
        if self.results is None:
            logger.warning("No results available. Run the backtest first.")
            return {}
        return self.results

    def get_metrics(self) -> dict[str, float]:
        """Get the metrics dictionary."""
        if self.metrics_data is None:
            logger.warning("No metrics available. Run the backtest first.")
            return {}
        return self.metrics_data

    def print_metrics(self) -> None:
        """Print performance metrics to the logger."""
        metrics = self.get_metrics()
        if not metrics:
            logger.warning("No metrics available. Run the backtest first.")
            return

        logger.info("Performance Metrics:")
        for key, value in metrics.items():
            logger.info("%s: %s", key, value)

    def get_plots(self, show_charts: bool = False) -> dict[str, pd.Series]:
        """Return legacy plot data."""
        if self.plots is None:
            logger.warning("No plots available. Run the backtest first.")
            return {}
        if show_charts:
            logger.warning("Inline chart display is no longer available.")
        return self.plots
