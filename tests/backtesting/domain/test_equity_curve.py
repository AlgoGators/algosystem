import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.shared.errors import (
    InvalidCapitalError,
    InvalidDateRangeError,
    InvalidPriceSeriesError,
)
from algosystem.shared.values import DateRange, Money


def valid_series() -> pd.Series:
    return pd.Series(
        [100.0, 102.0, 101.0, 105.0],
        index=pd.date_range("2020-01-01", periods=4, freq="D"),
        name="strategy",
    )


def test_package_import_does_not_load_heavy_adapters():
    code = """
import sys
import algosystem

forbidden = {"quantstats", "yfinance", "sqlalchemy", "matplotlib", "multiprocessing"}
loaded = sorted(forbidden.intersection(sys.modules))
if loaded:
    raise SystemExit(f"heavy adapters imported: {loaded}")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_from_series_validates_and_exposes_values():
    series = valid_series()
    curve = EquityCurve.from_series(series)

    assert curve.values.equals(series)
    assert len(curve) == 4
    assert curve.start == pd.Timestamp("2020-01-01")
    assert curve.end == pd.Timestamp("2020-01-04")
    assert curve.initial_value == Money(100)
    assert curve.final_value == Money(105)
    assert curve.date_range == DateRange("2020-01-01", "2020-01-04")
    assert curve.returns().tolist() == pytest.approx(
        [0.02, -0.009803921568627416, 0.03960396039603964]
    )
    assert curve.log_returns().tolist() == pytest.approx(
        np.log(series / series.shift(1)).dropna().tolist()
    )


def test_from_frame_uses_named_or_only_column():
    frame = pd.DataFrame({"price": valid_series()})

    assert EquityCurve.from_frame(frame, "price").values.equals(frame["price"])
    assert EquityCurve.from_frame(frame[["price"]]).values.equals(frame["price"])

    with pytest.raises(InvalidPriceSeriesError):
        EquityCurve.from_frame(pd.DataFrame({"a": valid_series(), "b": valid_series()}))
    with pytest.raises(InvalidPriceSeriesError):
        EquityCurve.from_frame(frame, "missing")


@pytest.mark.parametrize(
    "series",
    [
        pd.Series([100.0, 101.0], index=[1, 2]),
        pd.Series([100.0], index=pd.date_range("2020-01-01", periods=1)),
        pd.Series(
            [100.0, 101.0],
            index=pd.to_datetime(["2020-01-02", "2020-01-01"]),
        ),
        pd.Series(
            [100.0, 101.0],
            index=pd.to_datetime(["2020-01-01", "2020-01-01"]),
        ),
        pd.Series([100.0, np.nan], index=pd.date_range("2020-01-01", periods=2)),
        pd.Series([100.0, np.inf], index=pd.date_range("2020-01-01", periods=2)),
        pd.Series([100.0, 0.0], index=pd.date_range("2020-01-01", periods=2)),
        pd.Series([100.0, -1.0], index=pd.date_range("2020-01-01", periods=2)),
    ],
)
def test_invalid_series_invariants_raise_typed_errors(series):
    with pytest.raises(InvalidPriceSeriesError):
        EquityCurve.from_series(series)


def test_slice_returns_new_curve_and_empty_slice_raises():
    curve = EquityCurve.from_series(valid_series())

    sliced = curve.slice(DateRange("2020-01-02", "2020-01-03"))

    assert isinstance(sliced, EquityCurve)
    assert sliced.values.index.tolist() == list(pd.date_range("2020-01-02", periods=2))
    with pytest.raises(InvalidDateRangeError):
        curve.slice(DateRange("2021-01-01", "2021-01-02"))


def test_rebase_preserves_returns_exactly():
    curve = EquityCurve.from_series(valid_series())

    rebased = curve.rebase(Money(1000))

    assert rebased.initial_value == Money(1000)
    assert rebased.final_value == Money(1050)
    np.testing.assert_allclose(rebased.returns().to_numpy(), curve.returns().to_numpy())
    with pytest.raises(InvalidCapitalError):
        curve.rebase(Money(0))


def test_align_with_intersects_indices():
    curve = EquityCurve.from_series(valid_series())
    other = EquityCurve.from_series(
        pd.Series(
            [200.0, 202.0, 203.0],
            index=pd.date_range("2020-01-03", periods=3, freq="D"),
        )
    )

    left, right = curve.align_with(other)

    assert left.values.index.tolist() == list(pd.date_range("2020-01-03", periods=2))
    assert right.values.index.tolist() == left.values.index.tolist()


def test_align_with_requires_at_least_two_overlapping_points():
    curve = EquityCurve.from_series(valid_series())
    other = EquityCurve.from_series(
        pd.Series(
            [200.0, 202.0],
            index=pd.date_range("2020-01-04", periods=2, freq="D"),
        )
    )

    with pytest.raises(InvalidDateRangeError):
        curve.align_with(other)
