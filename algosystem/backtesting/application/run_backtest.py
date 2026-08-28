"""Run-backtest use case."""

from __future__ import annotations

from typing import Optional

import pandas as pd

from algosystem.backtesting.domain.backtest import Backtest
from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.domain.ports import MetricsCalculator
from algosystem.shared.errors import InvalidPriceSeriesError
from algosystem.shared.values import DateRange, Money

from .dto import RunBacktestRequest, RunBacktestResponse


class RunBacktest:
    """Use case for running a pure backtest calculation."""

    def __init__(self, calculator: MetricsCalculator) -> None:
        self._calculator = calculator

    def execute(self, request: RunBacktestRequest) -> RunBacktestResponse:
        """Run a backtest and return caller-friendly result data."""
        equity_curve = coerce_equity_curve(request.data, request.price_column)
        benchmark_curve = (
            coerce_equity_curve(request.benchmark, None) if request.benchmark is not None else None
        )
        date_range = coerce_date_range(request.start, request.end, equity_curve)
        capital = coerce_capital(request.initial_capital)

        result = Backtest(
            equity_curve=equity_curve,
            benchmark=benchmark_curve,
            date_range=date_range,
            initial_capital=capital,
        ).run(self._calculator)

        return RunBacktestResponse(
            run_id=result.run_id,
            metrics=result.metrics.to_dict(),
            equity=result.equity_curve.values.copy(),
            benchmark=(
                result.benchmark_curve.values.copy() if result.benchmark_curve is not None else None
            ),
            date_range=result.date_range,
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            total_return=result.total_return,
            summary=result.summary(),
        )


def coerce_equity_curve(data: object, column: Optional[str]) -> EquityCurve:
    """Coerce caller price data into a validated EquityCurve."""
    if isinstance(data, pd.DataFrame):
        return EquityCurve.from_frame(data, column)
    if isinstance(data, pd.Series):
        return EquityCurve.from_series(data)
    raise InvalidPriceSeriesError("data must be a pandas DataFrame or Series")


def coerce_date_range(
    start: object,
    end: object,
    equity_curve: EquityCurve,
) -> Optional[DateRange]:
    """Coerce optional caller dates into a DateRange."""
    if start is None and end is None:
        return None
    return DateRange(
        pd.to_datetime(start) if start is not None else equity_curve.start,
        pd.to_datetime(end) if end is not None else equity_curve.end,
    )


def coerce_capital(initial_capital: object) -> Optional[Money]:
    """Coerce optional caller capital into Money."""
    if initial_capital is None:
        return None
    if isinstance(initial_capital, Money):
        return initial_capital
    return Money(initial_capital)  # type: ignore[arg-type]
