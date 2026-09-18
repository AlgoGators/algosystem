"""Regime-conditional performance use case."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from algosystem.shared.errors import ValidationError
from algosystem.validation.application.equity_curve_bridge import SeriesKind, returns_from
from algosystem.validation.domain.statistics.robustness import (
    RegimeResult,
    regime_conditional_performance,
)

MIN_OBSERVATIONS_PER_REGIME = 5
"""Below this, the domain scores a bucket 0.0 rather than computing a Sharpe."""


class AnalyzeRegimes:
    """
    Split realized strategy performance by volatility regime.

    Answers "does this strategy only work in calm markets?" by classifying each
    observation into a rolling-volatility bucket and reporting the Sharpe ratio
    earned inside each one. This use case needs no parameter grid and no pass
    runner: it describes a single realized return series rather than searching a
    strategy's parameter space.
    """

    def execute(
        self,
        returns: object,
        *,
        market_returns: object | None = None,
        n_regimes: int = 3,
        vol_window: int = 21,
        annualize: float = 252.0,
        input_kind: SeriesKind = "returns",
        market_input_kind: SeriesKind | None = None,
    ) -> RegimeResult:
        """
        Classify observations into volatility regimes and report Sharpe per regime.

        Args:
            returns: Strategy series as an ``EquityCurve``, pandas Series/DataFrame,
                numpy array, or sequence.
            market_returns: Optional reference series used to define the regimes.
                When omitted, the strategy's own volatility defines them.
            n_regimes: Number of volatility buckets. Three yields low/med/high vol.
            vol_window: Rolling window, in observations, for the volatility estimate.
            annualize: Periods per year used to annualize each regime Sharpe.
            input_kind: Whether raw array and pandas ``returns`` input holds
                ``"returns"`` or ``"levels"``. ``EquityCurve`` always holds levels.
            market_input_kind: The same choice for ``market_returns``. Defaults to
                ``input_kind``; set it explicitly when the two series differ.

        Returns:
            A ``RegimeResult`` holding per-regime Sharpe, observation counts and
            time fractions, plus the worst regime and a works-everywhere flag.

        Raises:
            ValidationError: If a parameter is out of range, a series cannot be
                coerced to finite returns, the series is too short to classify,
                or the two series cover different dates.
        """
        n_regimes = _positive_int(n_regimes, name="n_regimes", minimum=2)
        vol_window = _positive_int(vol_window, name="vol_window", minimum=2)
        if not isinstance(annualize, (int, float)) or isinstance(annualize, bool):
            raise ValidationError("annualize must be a number")
        if not math.isfinite(annualize):
            raise ValidationError("annualize must be finite")
        if annualize <= 0:
            raise ValidationError("annualize must be positive")

        strategy_array = _coerce(returns, input_kind, label="returns")
        market_array = (
            None
            if market_returns is None
            else _coerce(
                market_returns,
                input_kind if market_input_kind is None else market_input_kind,
                label="market_returns",
            )
        )

        if market_array is not None:
            if len(market_array) != len(strategy_array):
                raise ValidationError(
                    "market_returns must be the same length as returns "
                    f"({len(market_array)} != {len(strategy_array)})"
                )
            _require_matching_dates(
                returns,
                market_returns,
                input_kind=input_kind,
                market_input_kind=input_kind if market_input_kind is None else market_input_kind,
            )

        _require_classifiable(
            n_observations=len(strategy_array),
            n_regimes=n_regimes,
            vol_window=vol_window,
        )

        return regime_conditional_performance(
            strategy_returns=strategy_array,
            market_returns=market_array,
            n_regimes=n_regimes,
            vol_window=vol_window,
            annualize=annualize,
        )


def _positive_int(value: object, *, name: str, minimum: int) -> int:
    """Accept only a true integer, so a float does not escape as a raw TypeError."""
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValidationError(f"{name} must be an integer")
    coerced = int(value)
    if coerced < minimum:
        raise ValidationError(f"{name} must be at least {minimum}")
    return coerced


def _coerce(source: object, input_kind: SeriesKind, *, label: str) -> np.ndarray:
    """Convert one series, naming the offending argument if conversion fails."""
    try:
        return returns_from(source, input_kind=input_kind)
    except ValidationError as exc:
        raise ValidationError(f"{label}: {exc}") from exc


def _require_classifiable(*, n_observations: int, n_regimes: int, vol_window: int) -> None:
    """
    Reject series the classifier cannot describe.

    The domain degrades quietly rather than raising: a series no longer than
    ``vol_window`` collapses to a single ``"all"`` regime, and any bucket holding
    fewer than five observations scores 0.0. Both produce output that reads like
    a finding ("Sharpe 0.0, regime-dependent") when it only means "not enough
    data", so this use case refuses the input instead.
    """
    classified = n_observations - vol_window
    if classified <= 0:
        raise ValidationError(
            f"need more than vol_window={vol_window} observations to classify regimes, "
            f"got {n_observations}"
        )
    if classified < n_regimes * MIN_OBSERVATIONS_PER_REGIME:
        raise ValidationError(
            f"need at least {n_regimes * MIN_OBSERVATIONS_PER_REGIME} observations after the "
            f"{vol_window}-observation warmup to fill {n_regimes} regimes, got {classified}; "
            "reduce n_regimes or vol_window, or supply a longer series"
        )


def _require_matching_dates(
    returns: object,
    market_returns: object,
    *,
    input_kind: SeriesKind,
    market_input_kind: SeriesKind,
) -> None:
    """
    Reject two dated series that describe different dates.

    Regimes are assigned positionally, so equal-length series drawn from
    different date ranges would be silently misaligned.
    """
    strategy_index = _returns_index(returns, input_kind)
    market_index = _returns_index(market_returns, market_input_kind)
    if strategy_index is None or market_index is None:
        return
    if not strategy_index.equals(market_index):
        raise ValidationError(
            "returns and market_returns must cover the same dates; "
            "align the two series before analyzing regimes"
        )


def _returns_index(source: object, input_kind: SeriesKind) -> pd.Index | None:
    """Return the index the converted returns will carry, or None if undated."""
    if _is_equity_curve(source):
        return source.values.index[1:]  # type: ignore[union-attr]
    if isinstance(source, (pd.Series, pd.DataFrame)):
        return source.index[1:] if input_kind == "levels" else source.index
    return None


def _is_equity_curve(source: object) -> bool:
    return (
        source.__class__.__name__ == "EquityCurve"
        and callable(getattr(source, "returns", None))
        and hasattr(source, "values")
    )


__all__ = ["MIN_OBSERVATIONS_PER_REGIME", "AnalyzeRegimes"]
