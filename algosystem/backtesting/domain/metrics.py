"""Performance metrics value object."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from numbers import Real
from typing import Mapping, Optional, Union

from algosystem.shared.errors import CalculationError
from algosystem.shared.metric_key import LEGACY_ALIASES, MetricKey

MetricLookup = Union[MetricKey, str]


def _resolve_key(key: MetricLookup) -> MetricKey:
    if isinstance(key, MetricKey):
        return key
    if isinstance(key, str):
        if key in LEGACY_ALIASES:
            return LEGACY_ALIASES[key]
        try:
            return MetricKey(key)
        except ValueError as exc:
            raise CalculationError(f"unknown metric key: {key}") from exc
    raise CalculationError("metric key must be a MetricKey or string")


def _valid_metric_names() -> str:
    valid_names = sorted({metric_key.value for metric_key in MetricKey} | set(LEGACY_ALIASES))
    return ", ".join(valid_names)


def _resolve_supported_lookup(key: MetricLookup) -> MetricKey:
    if isinstance(key, MetricKey):
        return key
    if isinstance(key, str):
        if key in LEGACY_ALIASES:
            return LEGACY_ALIASES[key]
        try:
            return MetricKey(key)
        except ValueError as exc:
            raise KeyError(
                f"unknown metric key {key!r}; valid keys: {_valid_metric_names()}"
            ) from exc
    raise ValueError(
        f"metric key must be a MetricKey or string, got {type(key).__name__}; "
        f"valid keys: {_valid_metric_names()}"
    )


def _normalize_value(value: object, key: MetricKey) -> Optional[float]:
    if value is None:
        return None
    if not isinstance(value, Real) or isinstance(value, bool):
        raise CalculationError(f"metric {key.value} must be numeric or None")
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


@dataclass(frozen=True)
class PerformanceMetrics:
    """Static performance metrics keyed by MetricKey."""

    total_return: Optional[float] = None
    annualized_return: Optional[float] = None
    annualized_volatility: Optional[float] = None
    max_drawdown: Optional[float] = None
    downside_deviation: Optional[float] = None
    var_95: Optional[float] = None
    var_99: Optional[float] = None
    cvar_95: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[float] = None
    jarque_bera_stat: Optional[float] = None
    jarque_bera_pvalue: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    positive_days: Optional[float] = None
    negative_days: Optional[float] = None
    pct_positive_days: Optional[float] = None
    best_month: Optional[float] = None
    worst_month: Optional[float] = None
    avg_monthly_return: Optional[float] = None
    monthly_volatility: Optional[float] = None
    pct_positive_months: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    correlation: Optional[float] = None
    tracking_error: Optional[float] = None
    information_ratio: Optional[float] = None
    capture_ratio_up: Optional[float] = None
    capture_ratio_down: Optional[float] = None

    def __post_init__(self) -> None:
        for key in MetricKey:
            value = getattr(self, key.value)
            object.__setattr__(self, key.value, _normalize_value(value, key))

    def get(self, key: MetricLookup) -> Optional[float]:
        """Return a metric value by canonical key."""
        metric_key = _resolve_supported_lookup(key)
        return getattr(self, metric_key.value)

    def to_dict(self) -> dict[str, float]:
        """Return non-empty metrics keyed by MetricKey.value."""
        metrics: dict[str, float] = {}
        for key in MetricKey:
            value = self.get(key)
            if value is not None:
                metrics[key.value] = value
        return metrics

    @classmethod
    def from_dict(cls, mapping: Mapping[MetricLookup, object]) -> "PerformanceMetrics":
        """Build metrics from MetricKey or string keys."""
        values: dict[str, Optional[float]] = {}
        for raw_key, raw_value in mapping.items():
            key = _resolve_key(raw_key)
            values[key.value] = _normalize_value(raw_value, key)
        return cls(**values)

    def benchmark_relative(self) -> dict[MetricKey, Optional[float]]:
        """Return benchmark-dependent metrics only."""
        return {key: self.get(key) for key in MetricKey if key.is_benchmark_relative()}

    def __getitem__(self, key: str) -> Optional[float]:
        warnings.warn(
            "String metric lookup is deprecated; use MetricKey and PerformanceMetrics.get().",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.get(_resolve_key(key))

    def __contains__(self, key: object) -> bool:
        warnings.warn(
            "String metric membership is deprecated; use MetricKey and PerformanceMetrics.get().",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            metric_key = _resolve_key(key)  # type: ignore[arg-type]
        except CalculationError:
            return False
        return self.get(metric_key) is not None
