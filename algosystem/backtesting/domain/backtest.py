"""Backtest aggregate root."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from algosystem.shared.errors import InvalidCapitalError, InvalidDateRangeError
from algosystem.shared.values import DateRange, Money, Percent, RunId

from .equity_curve import EquityCurve
from .metrics import PerformanceMetrics
from .ports import MetricsCalculator


@dataclass(frozen=True)
class BacktestResult:
    """Immutable result of a completed backtest."""

    equity_curve: EquityCurve
    benchmark_curve: Optional[EquityCurve]
    metrics: PerformanceMetrics
    date_range: DateRange
    initial_capital: Money
    final_capital: Money
    total_return: Percent
    run_id: Optional[RunId] = None

    def summary(self) -> dict[str, object]:
        """Return a small display-ready summary."""
        return {
            "run_id": self.run_id.value if self.run_id is not None else None,
            "start_date": self.date_range.start,
            "end_date": self.date_range.end,
            "initial_capital": self.initial_capital.amount,
            "final_capital": self.final_capital.amount,
            "total_return": self.total_return.as_fraction,
        }

    def to_legacy_dict(self) -> dict[str, object]:
        """Return the legacy Engine.results dictionary shape."""
        equity = self.equity_curve.values
        return {
            "equity": equity,
            "initial_capital": self.initial_capital.amount,
            "final_capital": self.final_capital.amount,
            "returns": self.total_return.as_fraction,
            "data": equity,
            "start_date": self.date_range.start,
            "end_date": self.date_range.end,
            "metrics": self.metrics.to_dict(),
            "plots": {},
        }


class Backtest:
    """Pure backtest aggregate built from an equity curve and optional benchmark."""

    def __init__(
        self,
        equity_curve: EquityCurve,
        benchmark: Optional[EquityCurve] = None,
        date_range: Optional[DateRange] = None,
        initial_capital: Optional[Money] = None,
        run_id: Optional[RunId] = None,
    ) -> None:
        active_range = date_range or equity_curve.date_range
        strategy_curve = equity_curve.slice(active_range)
        benchmark_curve = self._slice_optional_benchmark(benchmark, active_range)

        if benchmark_curve is not None:
            try:
                strategy_curve, benchmark_curve = strategy_curve.align_with(benchmark_curve)
            except InvalidDateRangeError:
                benchmark_curve = None

        capital = initial_capital or strategy_curve.initial_value
        if not isinstance(capital, Money):
            raise InvalidCapitalError("initial capital must be Money")
        if capital.amount <= 0:
            raise InvalidCapitalError("initial capital must be positive")

        self.equity_curve = strategy_curve
        self.benchmark_curve = benchmark_curve
        self.date_range = strategy_curve.date_range
        self.initial_capital = capital
        self.run_id = run_id

    def run(self, calculator: MetricsCalculator) -> BacktestResult:
        """Run the pure backtest calculation."""
        rebased_curve = self.equity_curve.rebase(self.initial_capital)
        metrics = calculator.calculate(rebased_curve, self.benchmark_curve)
        final_capital = rebased_curve.final_value
        total_return = Percent(
            (final_capital.amount - self.initial_capital.amount) / self.initial_capital.amount
        )
        return BacktestResult(
            run_id=self.run_id,
            equity_curve=rebased_curve,
            benchmark_curve=self.benchmark_curve,
            metrics=metrics,
            date_range=rebased_curve.date_range,
            initial_capital=self.initial_capital,
            final_capital=final_capital,
            total_return=total_return,
        )

    @staticmethod
    def _slice_optional_benchmark(
        benchmark: Optional[EquityCurve], date_range: DateRange
    ) -> Optional[EquityCurve]:
        if benchmark is None:
            return None
        try:
            return benchmark.slice(date_range)
        except InvalidDateRangeError:
            return None
