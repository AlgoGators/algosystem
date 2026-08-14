"""Momentum / trend-following strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def momentum_backtest(params, returns):
    """Long when rolling mean exceeds a threshold; flat otherwise."""
    lookback = params["lookback"]
    threshold = params["threshold"]
    n = len(returns)
    if n <= lookback:
        return 0.0
    cumsum = np.cumsum(returns)
    rolling_mean = np.empty(n)
    rolling_mean[:lookback] = 0.0
    rolling_mean[lookback:] = (cumsum[lookback:] - cumsum[: n - lookback]) / lookback
    signal = (rolling_mean > threshold).astype(float)
    return sharpe(signal[lookback:-1] * returns[lookback + 1 :])


PARAM_GRID = {
    "lookback": [3, 5, 10, 15, 20, 30, 40, 60, 80, 100],
    "threshold": [-0.001, -0.0005, 0.0, 0.0002, 0.0005, 0.001, 0.002, 0.003],
}
