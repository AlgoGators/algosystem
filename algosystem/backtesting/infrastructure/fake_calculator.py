"""Deterministic metrics calculator for tests."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.domain.metrics import PerformanceMetrics
from algosystem.backtesting.domain.ports import MetricsCalculator
from algosystem.shared.metric_key import MetricKey


class FakeMetricsCalculator(MetricsCalculator):
    """A deterministic calculator that never imports vendor analytics."""

    def __init__(self, metrics: Optional[PerformanceMetrics] = None) -> None:
        self.metrics = metrics or PerformanceMetrics.from_dict(
            {
                MetricKey.TOTAL_RETURN: 0.23,
                MetricKey.ANNUALIZED_RETURN: 0.12,
                MetricKey.ANNUALIZED_VOLATILITY: 0.08,
                MetricKey.SHARPE_RATIO: 1.5,
                MetricKey.MAX_DRAWDOWN: -0.1,
            }
        )

    def calculate(
        self, equity: EquityCurve, benchmark: Optional[EquityCurve]
    ) -> PerformanceMetrics:
        """Return fixed metrics."""
        return self.metrics

    def time_series(
        self, equity: EquityCurve, benchmark: Optional[EquityCurve], window: int
    ) -> dict[str, pd.Series]:
        """Return deterministic raw series for callers that need the port."""
        return {
            "daily_returns": equity.returns(),
            "equity_curve": equity.values / equity.values.iloc[0],
        }
