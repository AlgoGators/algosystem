"""Dual momentum (absolute + relative via two lookbacks) strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def dual_momentum_backtest(params, returns):
    """
    Combines a fast and slow momentum signal.
    Long when both are positive, short when both negative, flat otherwise.

    Parameters:
        fast_lookback: int   -- short lookback
        slow_lookback: int   -- long lookback
        threshold    : float -- minimum signal magnitude
    """
    flb = params['fast_lookback']
    slb = params['slow_lookback']
    th = params.get('threshold', 0.0)
    n = len(returns)
    warmup = max(flb, slb)
    if n <= warmup:
        return 0.0

    cumsum = np.cumsum(returns)
    fast_ma = np.zeros(n)
    slow_ma = np.zeros(n)
    fast_ma[flb:] = (cumsum[flb:] - cumsum[:n - flb]) / flb
    slow_ma[slb:] = (cumsum[slb:] - cumsum[:n - slb]) / slb

    signal = np.zeros(n)
    for i in range(warmup, n):
        if fast_ma[i] > th and slow_ma[i] > th:
            signal[i] = 1.0
        elif fast_ma[i] < -th and slow_ma[i] < -th:
            signal[i] = -1.0

    # Lag signal by 1 period to avoid lookahead bias
    strat_ret = signal[warmup:-1] * returns[warmup + 1:]
    return sharpe(strat_ret)


PARAM_GRID = {
    'fast_lookback': [3, 5, 10, 15],
    'slow_lookback': [20, 40, 60, 80, 100],
    'threshold': [0.0, 0.0003, 0.0005, 0.001],
}
