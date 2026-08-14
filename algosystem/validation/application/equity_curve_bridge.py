"""Pandas/numpy anti-corruption layer for validation returns."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

import numpy as np
import pandas as pd

from algosystem.shared.errors import ValidationError

SeriesKind = Literal["returns", "levels"]


def returns_from(source: object, *, input_kind: SeriesKind = "returns") -> np.ndarray:
    """
    Convert supported inputs into a finite 1-D returns array.

    ``EquityCurve``-like inputs always hold levels and are converted with
    ``pct_change``. For raw arrays and pandas objects, callers must make the
    intent explicit with ``input_kind="returns"`` or ``input_kind="levels"``.
    """
    if input_kind not in {"returns", "levels"}:
        raise ValidationError("input_kind must be 'returns' or 'levels'")

    if _is_equity_curve(source):
        values = source.returns().to_numpy(dtype=np.float64)  # type: ignore[union-attr]
        return _validated_returns(values)

    values = _to_1d_float_array(source)
    if input_kind == "levels":
        _validate_series_shape_and_finiteness(values, label="level series")
        previous = values[:-1]
        if np.any(previous == 0.0):
            raise ValidationError("level series cannot contain zero before a return step")
        values = (values[1:] / previous) - 1.0
    return _validated_returns(values)


def levels_from_returns(
    returns: object,
    *,
    initial_value: float = 1.0,
) -> np.ndarray:
    """Convert a returns series back into levels for later rendering layers."""
    if not np.isfinite(initial_value):
        raise ValidationError("initial_value must be finite")
    if initial_value <= 0:
        raise ValidationError("initial_value must be positive")

    returns_array = returns_from(returns, input_kind="returns")
    levels = np.empty(len(returns_array) + 1, dtype=np.float64)
    levels[0] = initial_value
    levels[1:] = initial_value * np.cumprod(1.0 + returns_array)
    if not np.isfinite(levels).all():
        raise ValidationError("returns produce non-finite levels")
    return levels


def _is_equity_curve(source: object) -> bool:
    return (
        source.__class__.__name__ == "EquityCurve"
        and callable(getattr(source, "returns", None))
        and hasattr(source, "values")
    )


def _to_1d_float_array(source: object) -> np.ndarray:
    if isinstance(source, pd.DataFrame):
        if source.shape[1] != 1:
            raise ValidationError("DataFrame input must have exactly one column")
        values = source.iloc[:, 0].to_numpy(dtype=np.float64)
    elif isinstance(source, pd.Series):
        values = source.to_numpy(dtype=np.float64)
    elif isinstance(source, np.ndarray):
        values = source.astype(np.float64, copy=False)
    elif isinstance(source, Sequence) and not isinstance(source, (str, bytes)):
        values = np.asarray(source, dtype=np.float64)
    else:
        raise ValidationError(
            "source must be an EquityCurve, pandas Series/DataFrame, numpy array, or sequence"
        )

    if values.ndim != 1:
        raise ValidationError("series must be one-dimensional")
    return values


def _validated_returns(values: np.ndarray) -> np.ndarray:
    _validate_series_shape_and_finiteness(values, label="returns series")
    return np.asarray(values, dtype=np.float64)


def _validate_series_shape_and_finiteness(values: np.ndarray, *, label: str) -> None:
    if values.size == 0:
        raise ValidationError(f"{label} must not be empty")
    if values.size == 1:
        raise ValidationError(f"{label} must contain at least two observations")
    if not np.isfinite(values).all():
        raise ValidationError(f"{label} must contain only finite values")
