"""Momentum / trend-following strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def momentum_backtest(params, returns):
    """
    Long when rolling mean > threshold, flat otherwise.

    Parameters:
        lookback : int   -- rolling window length
        threshold: float -- signal threshold for entry
    """
    lb = params['lookback']
    th = params['threshold']
    n = len(returns)
    if n <= lb:
        return 0.0
    cumsum = np.cumsum(returns)
    rm = np.empty(n)
    rm[:lb] = 0.0
    rm[lb:] = (cumsum[lb:] - cumsum[:n - lb]) / lb
    signal = (rm > th).astype(float)
    # Lag signal by 1 period to avoid lookahead bias:
    # decision at time i earns return at time i+1
    return sharpe(signal[lb:-1] * returns[lb + 1:])


PARAM_GRID = {
    'lookback': [3, 5, 10, 15, 20, 30, 40, 60, 80, 100],
    'threshold': [-0.001, -0.0005, 0.0, 0.0002, 0.0005, 0.001, 0.002, 0.003],
}
