"""Mean-reversion pairs / spread strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def pairs_backtest(params, returns):
    """Trade a synthetic spread built from the return series and a lagged leg."""
    lookback = params["lookback"]
    entry_z = params["entry_z"]
    exit_z = params.get("exit_z", 0.0)
    lag = params.get("lag", 1)
    n = len(returns)
    warmup = lookback + lag
    if n <= warmup + 1:
        return 0.0

    spread = returns[lag:] - 0.5 * returns[: n - lag]
    spread_length = len(spread)

    position = np.zeros(spread_length)
    pos = 0.0
    for index in range(lookback, spread_length):
        window = spread[index - lookback : index]
        mean = np.mean(window)
        std = np.std(window, ddof=1)
        zscore = 0.0 if std < 1e-12 else (spread[index] - mean) / std

        if pos == 0.0:
            if zscore < -entry_z:
                pos = 1.0
            elif zscore > entry_z:
                pos = -1.0
        elif pos == 1.0 and zscore > -exit_z:
            pos = 0.0
        elif pos == -1.0 and zscore < exit_z:
            pos = 0.0
        position[index] = pos

    strategy_returns = position[lookback:-1] * spread[lookback + 1 :]
    return sharpe(strategy_returns)


PARAM_GRID = {
    "lookback": [10, 20, 30, 40, 60],
    "entry_z": [1.0, 1.5, 2.0, 2.5],
    "exit_z": [0.0, 0.25, 0.5],
    "lag": [1, 2, 3, 5],
}
