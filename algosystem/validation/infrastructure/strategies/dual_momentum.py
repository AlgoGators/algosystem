"""Dual momentum strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def dual_momentum_backtest(params, returns):
    """Combine fast and slow momentum signals."""
    fast_lookback = params["fast_lookback"]
    slow_lookback = params["slow_lookback"]
    threshold = params.get("threshold", 0.0)
    n = len(returns)
    warmup = max(fast_lookback, slow_lookback)
    if n <= warmup:
        return 0.0

    cumsum = np.cumsum(returns)
    fast_ma = np.zeros(n)
    slow_ma = np.zeros(n)
    fast_ma[fast_lookback:] = (cumsum[fast_lookback:] - cumsum[: n - fast_lookback]) / fast_lookback
    slow_ma[slow_lookback:] = (cumsum[slow_lookback:] - cumsum[: n - slow_lookback]) / slow_lookback

    signal = np.zeros(n)
    for index in range(warmup, n):
        if fast_ma[index] > threshold and slow_ma[index] > threshold:
            signal[index] = 1.0
        elif fast_ma[index] < -threshold and slow_ma[index] < -threshold:
            signal[index] = -1.0

    strategy_returns = signal[warmup:-1] * returns[warmup + 1 :]
    return sharpe(strategy_returns)


PARAM_GRID = {
    "fast_lookback": [3, 5, 10, 15],
    "slow_lookback": [20, 40, 60, 80, 100],
    "threshold": [0.0, 0.0003, 0.0005, 0.001],
}
