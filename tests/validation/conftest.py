"""Shared fixtures for overfitting tests."""

import numpy as np
import pytest


def backtest_noise(params, returns):
    """Momentum on arbitrary returns — standard test backtest."""
    lb = params["lookback"]
    th = params["threshold"]
    n = len(returns)
    if n <= lb:
        return 0.0
    cumsum = np.cumsum(returns)
    rm = np.empty(n)
    rm[:lb] = 0.0
    rm[lb:] = (cumsum[lb:] - cumsum[: n - lb]) / lb
    sig = (rm > th).astype(float)
    sr = sig * returns
    sr = sr[lb:]
    if len(sr) == 0:
        return 0.0
    m = np.mean(sr)
    s = np.std(sr, ddof=1)
    if s < 1e-12:
        return 0.0
    return (m / s) * np.sqrt(252)


def backtest_constant(params, returns):
    """Always returns a fixed Sharpe regardless of data."""
    return 1.0


@pytest.fixture
def noise_returns():
    return np.random.default_rng(42).normal(0, 0.01, size=500)


@pytest.fixture
def small_grid():
    return {"lookback": [5, 10, 20], "threshold": [0.0, 0.001]}


@pytest.fixture
def medium_grid():
    return {
        "lookback": [5, 10, 20, 40],
        "threshold": [0.0, 0.0005, 0.001, 0.002],
    }


@pytest.fixture
def quick_detector(noise_returns, small_grid):
    """A fast detector for structural tests."""
    from algosystem.validation import OverfitDetector

    return OverfitDetector(
        backtest_fn=backtest_noise,
        returns=noise_returns,
        param_grid=small_grid,
        n_reps=50,
        n_workers=1,
        seed=42,
    )
