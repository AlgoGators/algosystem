"""Mean reversion (Bollinger z-score) strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def mean_reversion_backtest(params, returns):
    """Trade price z-score excursions back toward the rolling mean."""
    lookback = params["lookback"]
    entry_z = params["entry_z"]
    exit_z = params.get("exit_z", 0.0)
    n = len(returns)
    if n <= lookback + 1:
        return 0.0

    prices = np.cumsum(returns) + 100.0
    position = np.zeros(n)
    pos = 0.0

    rolling_mean = np.empty(n)
    rolling_std = np.empty(n)
    rolling_mean[:lookback] = rolling_std[:lookback] = 0.0
    for index in range(lookback, n):
        window = prices[index - lookback : index]
        rolling_mean[index] = np.mean(window)
        rolling_std[index] = np.std(window, ddof=1)

    for index in range(lookback, n):
        if rolling_std[index] < 1e-12:
            zscore = 0.0
        else:
            zscore = (prices[index] - rolling_mean[index]) / rolling_std[index]

        if pos == 0.0:
            if zscore < -entry_z:
                pos = 1.0
            elif zscore > entry_z:
                pos = -1.0
        elif pos == 1.0:
            if zscore > -exit_z:
                pos = 0.0
        elif pos == -1.0 and zscore < exit_z:
            pos = 0.0
        position[index] = pos

    strategy_returns = position[lookback:-1] * returns[lookback + 1 :]
    return sharpe(strategy_returns)


PARAM_GRID = {
    "lookback": [10, 15, 20, 30, 40, 60],
    "entry_z": [1.0, 1.5, 2.0, 2.5, 3.0],
    "exit_z": [0.0, 0.25, 0.5],
}
