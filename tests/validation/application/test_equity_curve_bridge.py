"""Tests for pandas/numpy validation bridge conversions."""

import numpy as np
import pandas as pd
import pytest

from algosystem.backtesting import EquityCurve
from algosystem.shared.errors import ValidationError
from algosystem.validation.application.equity_curve_bridge import levels_from_returns, returns_from


def test_returns_from_equity_curve_converts_levels_to_returns():
    dates = pd.date_range("2026-01-01", periods=4)
    curve = EquityCurve.from_series(pd.Series([100.0, 101.0, 99.99, 102.0], index=dates))

    returns = returns_from(curve)

    assert np.allclose(returns, np.array([0.01, -0.01, 0.02010201020102011]))


def test_returns_from_series_uses_explicit_input_kind():
    levels = pd.Series([100.0, 110.0, 99.0])
    returns = pd.Series([0.10, -0.10])

    assert np.allclose(returns_from(levels, input_kind="levels"), np.array([0.10, -0.10]))
    assert np.allclose(returns_from(returns, input_kind="returns"), np.array([0.10, -0.10]))


def test_levels_from_returns_reverses_return_conversion():
    returns = np.array([0.10, -0.10, 0.05])

    levels = levels_from_returns(returns, initial_value=100.0)

    assert np.allclose(levels, np.array([100.0, 110.0, 99.0, 103.95]))


@pytest.mark.parametrize(
    "source, message",
    [
        ([], "must not be empty"),
        ([0.01], "at least two observations"),
        ([0.01, np.nan], "finite"),
    ],
)
def test_returns_from_rejects_invalid_series(source, message):
    with pytest.raises(ValidationError, match=message):
        returns_from(source, input_kind="returns")


def test_returns_from_rejects_multicolumn_frame():
    frame = pd.DataFrame({"a": [0.01, 0.02], "b": [0.02, 0.03]})

    with pytest.raises(ValidationError, match="exactly one column"):
        returns_from(frame, input_kind="returns")
