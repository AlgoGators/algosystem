"""Backtesting domain ports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Mapping, Optional, Protocol

import pandas as pd

from algosystem.shared.metric_key import MetricKey
from algosystem.shared.values import DateRange, Money, Percent, RunId

from .equity_curve import EquityCurve
from .metrics import PerformanceMetrics

if TYPE_CHECKING:
    from .backtest import BacktestResult


@dataclass(frozen=True)
class RunSummary:
    """Small persisted-run summary for repository listings."""

    run_id: RunId
    date_range: DateRange
    initial_capital: Money
    final_capital: Money
    total_return: Percent
    metrics: PerformanceMetrics


class MetricsCalculator(Protocol):
    """Port for static metrics and non-aggregate time-series analytics."""

    def calculate(
        self, equity: EquityCurve, benchmark: Optional[EquityCurve]
    ) -> PerformanceMetrics:
        """Calculate static performance metrics."""
        ...

    def time_series(
        self, equity: EquityCurve, benchmark: Optional[EquityCurve], window: int
    ) -> dict[str, pd.Series]:
        """Calculate rolling and period analytics."""
        ...


class BacktestRunRepository(Protocol):
    """Port for persisting and loading backtest runs."""

    def save(
        self,
        result: "BacktestResult",
        overwrite: bool = False,
        name: Optional[str] = None,
        description: str = "",
        hyperparameters: Optional[Mapping[str, object]] = None,
    ) -> RunId:
        """Persist a backtest result and return its run id."""
        ...

    def get(self, run_id: RunId) -> "BacktestResult":
        """Load a backtest result."""
        ...

    def delete(self, run_id: RunId) -> None:
        """Delete a backtest result."""
        ...

    def list_runs(self, limit: int, offset: int) -> list[RunSummary]:
        """List saved runs."""
        ...

    def find_best(self, metric: MetricKey, limit: int) -> list[RunSummary]:
        """Find top runs by a metric."""
        ...

    def search(self, query: str, field: str) -> list[RunSummary]:
        """Search saved runs."""
        ...


class TearsheetRenderer(Protocol):
    """Port for rendering vendor tearsheets."""

    def render(
        self,
        result: "BacktestResult",
        output_path: Path,
        title: str,
        mode: str = "html",
        rf: float = 0.0,
        periods_per_year: int = 252,
    ) -> Path:
        """Render a tearsheet to a path."""
        ...
