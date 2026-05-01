"""Mean-reversion pairs / spread strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def pairs_backtest(params, returns):
    """
    Simulates pairs trading on a synthetic spread.
    Constructs a "spread" by combining the return series with a lagged/
    inverted version of itself (proxy for a second correlated asset).

    Parameters:
        lookback: int   -- window for spread z-score
        entry_z : float -- z-score entry threshold
        exit_z  : float -- z-score exit threshold
        lag     : int   -- lag for synthetic second leg
    """
    lb = params['lookback']
    entry_z = params['entry_z']
    exit_z = params.get('exit_z', 0.0)
    lag = params.get('lag', 1)
    n = len(returns)
    warmup = lb + lag
    if n <= warmup + 1:
        return 0.0

    spread = returns[lag:] - 0.5 * returns[:n - lag]
    ns = len(spread)

    position = np.zeros(ns)
    pos = 0.0
    for i in range(lb, ns):
        window = spread[i - lb:i]
        m = np.mean(window)
        s = np.std(window, ddof=1)
        if s < 1e-12:
            z = 0.0
        else:
            z = (spread[i] - m) / s

        if pos == 0.0:
            if z < -entry_z:
                pos = 1.0
            elif z > entry_z:
                pos = -1.0
        elif pos == 1.0 and z > -exit_z:
            pos = 0.0
        elif pos == -1.0 and z < exit_z:
            pos = 0.0
        position[i] = pos

    strat_ret = position[lb:-1] * spread[lb + 1:]
    return sharpe(strat_ret)


PARAM_GRID = {
    'lookback': [10, 20, 30, 40, 60],
    'entry_z': [1.0, 1.5, 2.0, 2.5],
    'exit_z': [0.0, 0.25, 0.5],
    'lag': [1, 2, 3, 5],
}
