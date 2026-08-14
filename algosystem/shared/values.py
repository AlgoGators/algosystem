"""Immutable shared value objects."""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass
from datetime import datetime
from numbers import Real
from typing import ClassVar

import numpy as np
import pandas as pd

from algosystem.shared.errors import ConfigurationError, InvalidCapitalError, InvalidDateRangeError


def _ensure_finite_number(value: Real, field_name: str) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise InvalidCapitalError(f"{field_name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise InvalidCapitalError(f"{field_name} must be finite")
    return number


@dataclass(frozen=True)
class Money:
    """A finite monetary amount in a three-letter currency."""

    amount: float
    currency: str = "USD"

    def __post_init__(self) -> None:
        amount = _ensure_finite_number(self.amount, "amount")
        currency = self.currency.upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            raise ConfigurationError("currency must be a three-letter ISO code")
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "currency", currency)

    def __add__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        self._require_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, scalar: Real) -> "Money":
        multiplier = _ensure_finite_number(scalar, "scalar")
        return Money(self.amount * multiplier, self.currency)

    __rmul__ = __mul__

    def __str__(self) -> str:
        if self.currency == "USD":
            return f"${self.amount:,.2f}"
        return f"{self.currency} {self.amount:,.2f}"

    def _require_same_currency(self, other: "Money") -> None:
        if not isinstance(other, Money):
            raise InvalidCapitalError("money arithmetic requires another Money value")
        if self.currency != other.currency:
            raise InvalidCapitalError(
                f"cannot mix currencies: {self.currency} and {other.currency}"
            )


@dataclass(frozen=True)
class Ratio:
    """A finite dimensionless ratio."""

    value: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", _ensure_finite_number(self.value, "ratio"))


@dataclass(frozen=True)
class Percent:
    """A percent value stored internally as a fraction."""

    fraction: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "fraction", _ensure_finite_number(self.fraction, "percent fraction")
        )

    @classmethod
    def from_percent(cls, percent: Real) -> "Percent":
        """Build a Percent from display percent units, such as 5.23."""
        return cls(_ensure_finite_number(percent, "percent") / 100)

    @property
    def as_fraction(self) -> float:
        """Return the stored fractional value, such as 0.0523."""
        return self.fraction

    @property
    def as_percent(self) -> float:
        """Return the value in percent units, such as 5.23."""
        return self.fraction * 100

    def __str__(self) -> str:
        return f"{self.as_percent:.2f}%"


@dataclass(frozen=True)
class RunId:
    """Identifier for a persisted backtest run."""

    value: str

    _last_generated_ms: ClassVar[int] = 0

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ConfigurationError("run id must be a non-empty string")
        if any(char.isspace() for char in self.value):
            raise ConfigurationError("run id must not contain whitespace")

    @classmethod
    def generate(cls) -> "RunId":
        """Generate a timestamp run id in YYYYMMDD_HHMMSS_mmm format."""
        now_ms = int(time.time() * 1000)
        if now_ms <= cls._last_generated_ms:
            now_ms = cls._last_generated_ms + 1
        cls._last_generated_ms = now_ms

        timestamp = datetime.fromtimestamp(now_ms / 1000)
        prefix = timestamp.strftime("%Y%m%d_%H%M%S")
        milliseconds = str(now_ms % 1000).zfill(3)
        return cls(f"{prefix}_{milliseconds}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class DateRange:
    """Inclusive date range backed by pandas timestamps."""

    start: pd.Timestamp
    end: pd.Timestamp

    def __post_init__(self) -> None:
        start = pd.Timestamp(self.start)
        end = pd.Timestamp(self.end)
        if end < start:
            raise InvalidDateRangeError("end date must be on or after start date")
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)

    def contains(self, ts: pd.Timestamp) -> bool:
        """Return whether a timestamp falls inside the inclusive range."""
        timestamp = pd.Timestamp(ts)
        return self.start <= timestamp <= self.end

    @property
    def days(self) -> int:
        """Return the number of calendar days between start and end."""
        return int((self.end - self.start).days)

    def mask(self, index: pd.DatetimeIndex) -> np.ndarray:
        """Return a boolean mask selecting index rows inside the range."""
        if not isinstance(index, pd.DatetimeIndex):
            raise InvalidDateRangeError("mask requires a pandas DatetimeIndex")
        return (index >= self.start) & (index <= self.end)

    @classmethod
    def from_index(cls, idx: pd.DatetimeIndex) -> "DateRange":
        """Build a DateRange spanning a non-empty DatetimeIndex."""
        if not isinstance(idx, pd.DatetimeIndex):
            raise InvalidDateRangeError("DateRange.from_index requires a DatetimeIndex")
        if idx.empty:
            raise InvalidDateRangeError("cannot build a date range from an empty index")
        return cls(idx.min(), idx.max())
