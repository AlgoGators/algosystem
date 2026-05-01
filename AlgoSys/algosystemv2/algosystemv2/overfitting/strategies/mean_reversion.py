"""Mean reversion (Bollinger z-score) strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def mean_reversion_backtest(params, returns):
    """
    Go long when z-score < -entry_z, exit when z-score crosses exit_z.
    Go short when z-score > entry_z, exit at -exit_z.

    Parameters:
        lookback: int   -- window for rolling mean/std
        entry_z : float -- z-score threshold to enter (positive)
        exit_z  : float -- z-score threshold to exit (positive, smaller)
    """
    lb = params['lookback']
    entry_z = params['entry_z']
    exit_z = params.get('exit_z', 0.0)
    n = len(returns)
    if n <= lb + 1:
        return 0.0

    prices = np.cumsum(returns) + 100.0
    position = np.zeros(n)
    pos = 0.0

    rm = np.empty(n)
    rs = np.empty(n)
    rm[:lb] = rs[:lb] = 0.0
    for i in range(lb, n):
        window = prices[i - lb:i]
        rm[i] = np.mean(window)
        rs[i] = np.std(window, ddof=1)

    for i in range(lb, n):
        if rs[i] < 1e-12:
            z = 0.0
        else:
            z = (prices[i] - rm[i]) / rs[i]

        if pos == 0.0:
            if z < -entry_z:
                pos = 1.0
            elif z > entry_z:
                pos = -1.0
        elif pos == 1.0:
            if z > -exit_z:
                pos = 0.0
        elif pos == -1.0:
            if z < exit_z:
                pos = 0.0
        position[i] = pos

    strat_ret = position[lb:-1] * returns[lb + 1:]
    return sharpe(strat_ret)


PARAM_GRID = {
    'lookback': [10, 15, 20, 30, 40, 60],
    'entry_z': [1.0, 1.5, 2.0, 2.5, 3.0],
    'exit_z': [0.0, 0.25, 0.5],
}
