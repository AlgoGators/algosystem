"""Quantstats-backed tearsheet renderer adapter."""

from __future__ import annotations

import contextlib
import importlib
import io
import logging
import warnings
from pathlib import Path
from typing import Optional

import matplotlib
import pandas as pd

from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.backtesting.domain.ports import TearsheetRenderer
from algosystem.shared.errors import CalculationError

logger = logging.getLogger(__name__)


class QuantStatsTearsheetRenderer(TearsheetRenderer):
    """TearsheetRenderer implementation backed by quantstats reports."""

    def render(
        self,
        result: BacktestResult,
        output_path: Path,
        title: str,
        mode: str = "html",
        rf: float = 0.0,
        periods_per_year: int = 252,
    ) -> Path:
        """Render a quantstats report and return the requested output path."""
        normalized_mode = mode.lower()
        if normalized_mode not in {"html", "full", "basic"}:
            raise CalculationError(f"unsupported tearsheet mode: {mode}")

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        original_backend = matplotlib.get_backend()
        report_error: Optional[Exception] = None

        try:
            matplotlib.use("Agg", force=True)
            with warnings.catch_warnings(), _patched_resampler_sum_axis():
                warnings.simplefilter("ignore", FutureWarning)
                qs = importlib.import_module("quantstats")
                strategy_returns = _returns(result)
                benchmark_returns = _benchmark_returns(result)
                if normalized_mode == "html":
                    with contextlib.redirect_stdout(io.StringIO()):
                        qs.reports.html(
                            strategy_returns,
                            benchmark=benchmark_returns,
                            title=title,
                            output=str(output),
                            rf=rf,
                            periods_per_year=periods_per_year,
                        )
                elif normalized_mode == "full":
                    qs.reports.full(
                        strategy_returns,
                        benchmark=benchmark_returns,
                        rf=rf,
                        periods_per_year=periods_per_year,
                    )
                else:
                    qs.reports.basic(
                        strategy_returns,
                        benchmark=benchmark_returns,
                        rf=rf,
                        periods_per_year=periods_per_year,
                    )
        except Exception as exc:
            report_error = exc
        finally:
            try:
                matplotlib.use(original_backend, force=True)
            except (ImportError, ValueError):
                logger.debug("could not restore matplotlib backend", exc_info=True)

        if report_error is not None:
            raise CalculationError("failed to render quantstats tearsheet") from report_error
        return output


def _returns(result: BacktestResult) -> pd.Series:
    returns = result.equity_curve.returns()
    returns.name = returns.name or "strategy"
    return returns


def _benchmark_returns(result: BacktestResult) -> Optional[pd.Series]:
    if result.benchmark_curve is None:
        return None
    benchmark_returns = result.benchmark_curve.returns()
    benchmark_returns.name = benchmark_returns.name or "benchmark"
    return benchmark_returns


@contextlib.contextmanager
def _patched_resampler_sum_axis():
    """Temporarily accept quantstats' deprecated Resampler.sum(axis=0) call."""
    from pandas.core.resample import Resampler

    original_sum = Resampler.sum

    def sum_without_axis(self, *args, **kwargs):
        kwargs.pop("axis", None)
        return original_sum(self, *args, **kwargs)

    Resampler.sum = sum_without_axis
    try:
        yield
    finally:
        Resampler.sum = original_sum
