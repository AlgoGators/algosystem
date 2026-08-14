"""QuantStats-backed metrics calculator adapter."""

from __future__ import annotations

import logging
from typing import Callable, Optional

import numpy as np
import pandas as pd
import quantstats as qs
from scipy import stats

from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.domain.metrics import PerformanceMetrics
from algosystem.backtesting.domain.ports import MetricsCalculator
from algosystem.shared.errors import (
    CalculationError,
    InsufficientDataError,
    InvalidPriceSeriesError,
)
from algosystem.shared.metric_key import MetricKey

logger = logging.getLogger(__name__)


class QuantStatsMetricsCalculator(MetricsCalculator):
    """MetricsCalculator implementation backed by QuantStats."""

    def calculate(
        self, equity: EquityCurve, benchmark: Optional[EquityCurve]
    ) -> PerformanceMetrics:
        """Calculate static performance metrics."""
        strategy_returns = self._returns_for_calculation(equity)
        benchmark_returns = self._benchmark_returns(benchmark)
        benchmark_strategy_returns = strategy_returns
        if benchmark_returns is not None:
            benchmark_strategy_returns, benchmark_returns = strategy_returns.align(
                benchmark_returns, join="inner"
            )
            if benchmark_strategy_returns.empty or benchmark_returns.empty:
                benchmark_returns = None

        metrics: dict[MetricKey, Optional[float]] = {
            MetricKey.TOTAL_RETURN: self._finite_or_none(
                (equity.values.iloc[-1] / equity.values.iloc[0]) - 1
            ),
            MetricKey.ANNUALIZED_RETURN: self._annualized_return(strategy_returns, equity),
            MetricKey.ANNUALIZED_VOLATILITY: self._finite_or_none(
                strategy_returns.std() * np.sqrt(252)
            ),
            MetricKey.DOWNSIDE_DEVIATION: self._downside_deviation(strategy_returns),
            MetricKey.MAX_DRAWDOWN: self._compute(
                MetricKey.MAX_DRAWDOWN, lambda: qs.stats.max_drawdown(strategy_returns)
            ),
            MetricKey.VAR_95: self._compute(
                MetricKey.VAR_95,
                lambda: _value_at_risk(strategy_returns, confidence=0.95),
            ),
            MetricKey.VAR_99: self._compute(
                MetricKey.VAR_99,
                lambda: _value_at_risk(strategy_returns, confidence=0.99),
            ),
            MetricKey.CVAR_95: self._compute(
                MetricKey.CVAR_95,
                lambda: _conditional_value_at_risk(strategy_returns, confidence=0.95),
            ),
            MetricKey.SKEWNESS: self._finite_or_none(strategy_returns.skew()),
            MetricKey.KURTOSIS: self._finite_or_none(strategy_returns.kurtosis()),
            MetricKey.SHARPE_RATIO: self._compute(
                MetricKey.SHARPE_RATIO, lambda: qs.stats.sharpe(strategy_returns)
            ),
            MetricKey.SORTINO_RATIO: self._compute(
                MetricKey.SORTINO_RATIO, lambda: qs.stats.sortino(strategy_returns)
            ),
            MetricKey.CALMAR_RATIO: self._compute(
                MetricKey.CALMAR_RATIO, lambda: qs.stats.calmar(strategy_returns)
            ),
            MetricKey.POSITIVE_DAYS: float((strategy_returns > 0).sum()),
            MetricKey.NEGATIVE_DAYS: float((strategy_returns < 0).sum()),
            MetricKey.PCT_POSITIVE_DAYS: self._finite_or_none((strategy_returns > 0).mean()),
        }

        metrics.update(self._jarque_bera(strategy_returns))
        metrics.update(self._monthly_metrics(strategy_returns))
        if benchmark_returns is not None:
            metrics.update(self._benchmark_metrics(benchmark_strategy_returns, benchmark_returns))

        return PerformanceMetrics.from_dict(metrics)

    def time_series(
        self, equity: EquityCurve, benchmark: Optional[EquityCurve], window: int = 30
    ) -> dict[str, pd.Series]:
        """Calculate rolling and period analytics as raw pandas Series."""
        if window < 1:
            raise CalculationError("rolling window must be positive")

        strategy_returns = self._returns_for_calculation(equity)
        benchmark_returns = self._benchmark_returns(benchmark)
        if benchmark_returns is not None:
            aligned_strategy, aligned_benchmark = strategy_returns.align(
                benchmark_returns, join="inner"
            )
            if aligned_strategy.empty or aligned_benchmark.empty:
                benchmark_returns = None
            else:
                strategy_returns = aligned_strategy
                benchmark_returns = aligned_benchmark

        time_series = {
            "equity_curve": _equity_curve(strategy_returns),
            "drawdown_series": _drawdown_series(strategy_returns),
            "rolling_sharpe": self._series(
                "rolling_sharpe",
                lambda: qs.stats.rolling_sharpe(strategy_returns, window),
                strategy_returns.index,
            ),
            "rolling_sortino": self._series(
                "rolling_sortino",
                lambda: qs.stats.rolling_sortino(strategy_returns, window),
                strategy_returns.index,
            ),
            "rolling_volatility": strategy_returns.rolling(window).std() * np.sqrt(252),
            "rolling_return": strategy_returns.rolling(window).mean() * 252,
            "rolling_skew": strategy_returns.rolling(window).skew(),
            "rolling_var": strategy_returns.rolling(window).quantile(0.05),
            "rolling_drawdown_duration": _rolling_drawdown_duration(strategy_returns, window),
            "rolling_max_drawdown": _rolling_max_drawdown(strategy_returns, window),
            "daily_returns": strategy_returns,
            "monthly_returns": _period_returns(strategy_returns, "ME"),
            "quarterly_returns": _period_returns(strategy_returns, "QE"),
            "yearly_returns": _period_returns(strategy_returns, "YE"),
            "rolling_3m_returns": _rolling_period_return(strategy_returns, 63),
            "rolling_6m_returns": _rolling_period_return(strategy_returns, 126),
            "rolling_1y_returns": _rolling_period_return(strategy_returns, 252),
        }

        if benchmark_returns is not None:
            benchmark_equity = _equity_curve(benchmark_returns)
            time_series.update(
                {
                    "benchmark_daily_returns": benchmark_returns,
                    "benchmark_equity_curve": benchmark_equity,
                    "benchmark_drawdown_series": _drawdown_series(benchmark_returns),
                    "benchmark_rolling_volatility": benchmark_returns.rolling(window).std()
                    * np.sqrt(252),
                    "relative_performance": time_series["equity_curve"] / benchmark_equity,
                    "excess_returns": strategy_returns - benchmark_returns,
                    "rolling_correlation": strategy_returns.rolling(window).corr(benchmark_returns),
                    "rolling_tracking_error": (strategy_returns - benchmark_returns)
                    .rolling(window)
                    .std()
                    * np.sqrt(252),
                    "rolling_beta": _rolling_beta(strategy_returns, benchmark_returns, window),
                }
            )

        return time_series

    @staticmethod
    def _returns_for_calculation(equity: EquityCurve) -> pd.Series:
        returns = equity.returns()
        if returns.empty:
            raise InsufficientDataError("insufficient data points to calculate returns")
        max_abs_return = abs(returns).max()
        if not np.isfinite(max_abs_return):
            raise InvalidPriceSeriesError("returns must be finite")
        if max_abs_return > 10:
            raise InvalidPriceSeriesError(f"unrealistic return detected: {max_abs_return:.2f}")
        return returns

    @staticmethod
    def _benchmark_returns(benchmark: Optional[EquityCurve]) -> Optional[pd.Series]:
        if benchmark is None:
            return None
        benchmark_returns = benchmark.returns()
        if benchmark_returns.empty:
            return None
        return benchmark_returns

    @staticmethod
    def _finite_or_none(value: object) -> Optional[float]:
        if value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not np.isfinite(number):
            return None
        return number

    def _compute(self, key: MetricKey, calculation: Callable[[], object]) -> Optional[float]:
        try:
            return self._finite_or_none(calculation())
        except Exception:
            logger.debug("could not compute %s", key.value, exc_info=True)
            return None

    def _series(
        self, name: str, calculation: Callable[[], pd.Series], index: pd.Index
    ) -> pd.Series:
        try:
            result = calculation()
        except Exception:
            logger.debug("could not compute %s", name, exc_info=True)
            return pd.Series(index=index, dtype=float)
        if isinstance(result, pd.Series):
            return result
        return pd.Series(result, index=index, dtype=float)

    def _annualized_return(
        self, strategy_returns: pd.Series, equity: EquityCurve
    ) -> Optional[float]:
        total_return = self._finite_or_none((equity.values.iloc[-1] / equity.values.iloc[0]) - 1)
        if total_return is None:
            return None
        return self._finite_or_none((1 + total_return) ** (252 / len(strategy_returns)) - 1)

    def _downside_deviation(self, strategy_returns: pd.Series) -> Optional[float]:
        downside_returns = strategy_returns[strategy_returns < 0]
        if downside_returns.empty:
            return 0.0
        return self._finite_or_none(downside_returns.std() * np.sqrt(252))

    def _jarque_bera(self, strategy_returns: pd.Series) -> dict[MetricKey, Optional[float]]:
        try:
            jarque_bera = stats.jarque_bera(strategy_returns.dropna())
        except Exception:
            logger.debug("could not compute jarque-bera statistics", exc_info=True)
            return {
                MetricKey.JARQUE_BERA_STAT: None,
                MetricKey.JARQUE_BERA_PVALUE: None,
            }
        return {
            MetricKey.JARQUE_BERA_STAT: self._finite_or_none(jarque_bera.statistic),
            MetricKey.JARQUE_BERA_PVALUE: self._finite_or_none(jarque_bera.pvalue),
        }

    def _monthly_metrics(self, strategy_returns: pd.Series) -> dict[MetricKey, Optional[float]]:
        try:
            monthly_returns = _period_returns(strategy_returns, "ME")
        except Exception:
            logger.debug("could not compute monthly metrics", exc_info=True)
            return {
                MetricKey.BEST_MONTH: None,
                MetricKey.WORST_MONTH: None,
                MetricKey.AVG_MONTHLY_RETURN: None,
                MetricKey.MONTHLY_VOLATILITY: None,
                MetricKey.PCT_POSITIVE_MONTHS: None,
            }
        return {
            MetricKey.BEST_MONTH: self._finite_or_none(monthly_returns.max()),
            MetricKey.WORST_MONTH: self._finite_or_none(monthly_returns.min()),
            MetricKey.AVG_MONTHLY_RETURN: self._finite_or_none(monthly_returns.mean()),
            MetricKey.MONTHLY_VOLATILITY: self._finite_or_none(monthly_returns.std()),
            MetricKey.PCT_POSITIVE_MONTHS: self._finite_or_none((monthly_returns > 0).mean()),
        }

    def _benchmark_metrics(
        self, strategy_returns: pd.Series, benchmark_returns: pd.Series
    ) -> dict[MetricKey, Optional[float]]:
        metrics: dict[MetricKey, Optional[float]] = {
            MetricKey.CORRELATION: self._finite_or_none(strategy_returns.corr(benchmark_returns)),
            MetricKey.INFORMATION_RATIO: self._compute(
                MetricKey.INFORMATION_RATIO,
                lambda: qs.stats.information_ratio(strategy_returns, benchmark_returns),
            ),
            MetricKey.CAPTURE_RATIO_UP: self._capture_ratio(
                strategy_returns, benchmark_returns, up_market=True
            ),
            MetricKey.CAPTURE_RATIO_DOWN: self._capture_ratio(
                strategy_returns, benchmark_returns, up_market=False
            ),
        }

        try:
            greeks = qs.stats.greeks(strategy_returns, benchmark_returns)
        except Exception:
            logger.debug("could not compute benchmark greeks", exc_info=True)
            metrics.update(
                {
                    MetricKey.ALPHA: None,
                    MetricKey.BETA: None,
                    MetricKey.TRACKING_ERROR: None,
                }
            )
            return metrics

        metrics.update(
            {
                MetricKey.ALPHA: self._finite_or_none(greeks.get(MetricKey.ALPHA.value)),
                MetricKey.BETA: self._finite_or_none(greeks.get(MetricKey.BETA.value)),
                MetricKey.TRACKING_ERROR: self._finite_or_none(greeks.get("risk")),
            }
        )
        return metrics

    def _capture_ratio(
        self, strategy_returns: pd.Series, benchmark_returns: pd.Series, up_market: bool
    ) -> Optional[float]:
        if hasattr(qs.stats, "capture"):
            key = MetricKey.CAPTURE_RATIO_UP if up_market else MetricKey.CAPTURE_RATIO_DOWN
            return self._compute(
                key,
                lambda: qs.stats.capture(strategy_returns, benchmark_returns, up=up_market),
            )

        market = benchmark_returns > 0 if up_market else benchmark_returns < 0
        if market.sum() == 0:
            return None
        benchmark_mean = benchmark_returns[market].mean()
        if benchmark_mean == 0:
            return None
        return self._finite_or_none(strategy_returns[market].mean() / benchmark_mean)


def _equity_curve(returns: pd.Series) -> pd.Series:
    curve = (1 + returns).cumprod()
    if curve.empty:
        return curve
    return curve / curve.iloc[0]


def _value_at_risk(returns: pd.Series, confidence: float) -> object:
    try:
        return qs.stats.value_at_risk(returns, confidence=confidence)
    except TypeError:
        return qs.stats.value_at_risk(returns, cutoff=1 - confidence)


def _conditional_value_at_risk(returns: pd.Series, confidence: float) -> object:
    try:
        return qs.stats.conditional_value_at_risk(returns, confidence=confidence)
    except TypeError:
        return qs.stats.conditional_value_at_risk(returns, cutoff=1 - confidence)


def _drawdown_series(returns: pd.Series) -> pd.Series:
    equity = _equity_curve(returns)
    high = equity.cummax()
    return (equity / high) - 1


def _rolling_drawdown_duration(returns: pd.Series, window: int) -> pd.Series:
    equity = (1 + returns).cumprod()
    peak = equity.cummax()
    underwater = (equity < peak).astype(int)
    group_id = (underwater == 0).cumsum()
    streak = underwater.groupby(group_id).cumcount() + 1
    streak = streak.where(underwater == 1, 0)
    return streak.rolling(window).max()


def _rolling_max_drawdown(returns: pd.Series, window: int) -> pd.Series:
    cumulative = (1 + returns).cumprod()
    rolling_max_drawdown = pd.Series(index=returns.index, dtype=float)
    for index in range(window, len(cumulative)):
        window_cumulative = cumulative.iloc[index - window : index + 1]
        window_peak = window_cumulative.cummax()
        window_drawdown = (window_cumulative / window_peak) - 1
        rolling_max_drawdown.iloc[index] = window_drawdown.min()
    return rolling_max_drawdown


def _period_returns(returns: pd.Series, rule: str) -> pd.Series:
    return returns.resample(rule).apply(lambda period: (1 + period).prod() - 1)


def _rolling_period_return(returns: pd.Series, window: int) -> pd.Series:
    return (1 + returns).rolling(window).apply(lambda values: values.prod() - 1, raw=True)


def _rolling_beta(
    strategy_returns: pd.Series, benchmark_returns: pd.Series, window: int
) -> pd.Series:
    covariance = strategy_returns.rolling(window).cov(benchmark_returns)
    variance = benchmark_returns.rolling(window).var()
    return covariance / variance
