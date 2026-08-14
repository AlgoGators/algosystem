"""Canonical metric keys used by AlgoSystem."""

from __future__ import annotations

from enum import Enum


class MetricKey(str, Enum):
    """Single source of truth for performance metric names."""

    # Returns
    TOTAL_RETURN = "total_return"
    ANNUALIZED_RETURN = "annualized_return"
    ANNUALIZED_VOLATILITY = "annualized_volatility"

    # Risk
    MAX_DRAWDOWN = "max_drawdown"
    DOWNSIDE_DEVIATION = "downside_deviation"
    VAR_95 = "var_95"
    VAR_99 = "var_99"
    CVAR_95 = "cvar_95"
    SKEWNESS = "skewness"
    KURTOSIS = "kurtosis"
    JARQUE_BERA_STAT = "jarque_bera_stat"
    JARQUE_BERA_PVALUE = "jarque_bera_pvalue"

    # Ratios
    SHARPE_RATIO = "sharpe_ratio"
    SORTINO_RATIO = "sortino_ratio"
    CALMAR_RATIO = "calmar_ratio"

    # Trade statistics
    POSITIVE_DAYS = "positive_days"
    NEGATIVE_DAYS = "negative_days"
    PCT_POSITIVE_DAYS = "pct_positive_days"

    # Monthly statistics
    BEST_MONTH = "best_month"
    WORST_MONTH = "worst_month"
    AVG_MONTHLY_RETURN = "avg_monthly_return"
    MONTHLY_VOLATILITY = "monthly_volatility"
    PCT_POSITIVE_MONTHS = "pct_positive_months"

    # Benchmark-relative
    ALPHA = "alpha"
    BETA = "beta"
    CORRELATION = "correlation"
    TRACKING_ERROR = "tracking_error"
    INFORMATION_RATIO = "information_ratio"
    CAPTURE_RATIO_UP = "capture_ratio_up"
    CAPTURE_RATIO_DOWN = "capture_ratio_down"

    def label(self) -> str:
        """Return a human-readable display label."""
        special_words = {
            "avg": "Avg",
            "cvar": "CVaR",
            "pct": "Percent",
            "var": "VaR",
        }
        return " ".join(
            special_words.get(part, part.capitalize()) for part in self.value.split("_")
        )

    def is_benchmark_relative(self) -> bool:
        """Return whether this metric requires a benchmark."""
        return self in {
            MetricKey.ALPHA,
            MetricKey.BETA,
            MetricKey.CORRELATION,
            MetricKey.TRACKING_ERROR,
            MetricKey.INFORMATION_RATIO,
            MetricKey.CAPTURE_RATIO_UP,
            MetricKey.CAPTURE_RATIO_DOWN,
        }


LEGACY_ALIASES: dict[str, MetricKey] = {
    "annual_return": MetricKey.ANNUALIZED_RETURN,
    "volatility": MetricKey.ANNUALIZED_VOLATILITY,
}
