"""Equity curve value object."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from algosystem.shared.errors import (
    InvalidCapitalError,
    InvalidDateRangeError,
    InvalidPriceSeriesError,
)
from algosystem.shared.values import DateRange, Money


@dataclass(frozen=True)
class EquityCurve:
    """A validated positive price/equity series indexed by date."""

    _values: pd.Series

    def __post_init__(self) -> None:
        if not isinstance(self._values, pd.Series):
            raise InvalidPriceSeriesError("equity curve must be a pandas Series")

        series = self._values.copy()
        if not isinstance(series.index, pd.DatetimeIndex):
            raise InvalidPriceSeriesError("equity curve index must be a DatetimeIndex")
        if len(series) < 2:
            raise InvalidPriceSeriesError("equity curve requires at least two points")
        if not series.index.is_monotonic_increasing:
            raise InvalidPriceSeriesError("equity curve index must be monotonically increasing")
        if not series.index.is_unique:
            raise InvalidPriceSeriesError("equity curve index must be unique")

        try:
            series = series.astype(float)
        except (TypeError, ValueError) as exc:
            raise InvalidPriceSeriesError("equity curve values must be numeric") from exc

        if series.isna().any():
            raise InvalidPriceSeriesError("equity curve values must not contain NaN")
        values = series.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise InvalidPriceSeriesError("equity curve values must be finite")
        if not (values > 0).all():
            raise InvalidPriceSeriesError("equity curve values must be strictly positive")

        object.__setattr__(self, "_values", series)

    @classmethod
    def from_series(cls, series: pd.Series) -> "EquityCurve":
        """Build an EquityCurve from a pandas Series."""
        return cls(series.copy())

    @classmethod
    def from_frame(cls, frame: pd.DataFrame, column: Optional[str] = None) -> "EquityCurve":
        """Build an EquityCurve from a DataFrame column."""
        if not isinstance(frame, pd.DataFrame):
            raise InvalidPriceSeriesError("equity curve frame must be a pandas DataFrame")
        if column is not None:
            if column not in frame.columns:
                raise InvalidPriceSeriesError(f"column not found: {column}")
            return cls.from_series(frame[column])
        if frame.shape[1] != 1:
            raise InvalidPriceSeriesError("DataFrame has multiple columns; specify a column")
        return cls.from_series(frame.iloc[:, 0])

    @property
    def values(self) -> pd.Series:
        """Return the underlying pandas Series."""
        return self._values

    def returns(self) -> pd.Series:
        """Return simple percentage returns."""
        return self.values.pct_change().dropna()

    def log_returns(self) -> pd.Series:
        """Return log returns."""
        return np.log(self.values / self.values.shift(1)).dropna()

    @property
    def start(self) -> pd.Timestamp:
        """Return the first timestamp."""
        return self.values.index[0]

    @property
    def end(self) -> pd.Timestamp:
        """Return the final timestamp."""
        return self.values.index[-1]

    @property
    def initial_value(self) -> Money:
        """Return the first value as Money."""
        return Money(float(self.values.iloc[0]))

    @property
    def final_value(self) -> Money:
        """Return the final value as Money."""
        return Money(float(self.values.iloc[-1]))

    @property
    def date_range(self) -> DateRange:
        """Return the inclusive date range covered by the curve."""
        return DateRange(self.start, self.end)

    def slice(self, date_range: DateRange) -> "EquityCurve":
        """Return a curve limited to an inclusive date range."""
        sliced = self.values.loc[date_range.mask(self.values.index)]
        if sliced.empty:
            raise InvalidDateRangeError("date range does not overlap the equity curve")
        return EquityCurve.from_series(sliced)

    def rebase(self, to: Money) -> "EquityCurve":
        """Return a new curve normalized so the first value equals the target capital."""
        if not isinstance(to, Money):
            raise InvalidCapitalError("rebase target must be Money")
        if to.amount <= 0:
            raise InvalidCapitalError("rebase target must be positive")

        rebased = self.values * (to.amount / float(self.values.iloc[0]))
        rebased.name = self.values.name
        return EquityCurve.from_series(rebased)

    def align_with(self, other: "EquityCurve") -> tuple["EquityCurve", "EquityCurve"]:
        """Return both curves aligned to their shared timestamps."""
        if not isinstance(other, EquityCurve):
            raise InvalidPriceSeriesError("can only align with another EquityCurve")

        shared_index = self.values.index.intersection(other.values.index)
        if len(shared_index) < 2:
            raise InvalidDateRangeError("equity curves require at least two overlapping points")

        return (
            EquityCurve.from_series(self.values.loc[shared_index]),
            EquityCurve.from_series(other.values.loc[shared_index]),
        )

    def __len__(self) -> int:
        return len(self.values)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EquityCurve):
            return False
        return self.values.equals(other.values)
