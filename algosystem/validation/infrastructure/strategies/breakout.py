"""Breakout (Donchian channel) strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def breakout_backtest(params, returns):
    """Go long on channel highs, short on channel lows, and exit after a hold."""
    channel = params["channel"]
    hold_days = params["hold_days"]
    n = len(returns)
    if n <= channel + hold_days:
        return 0.0

    prices = np.cumsum(returns) + 100.0
    position = np.zeros(n)
    hold_counter = 0
    pos = 0.0

    for index in range(channel, n):
        high = np.max(prices[index - channel : index])
        low = np.min(prices[index - channel : index])

        if hold_counter > 0:
            hold_counter -= 1
            if hold_counter == 0:
                pos = 0.0

        if pos == 0.0:
            if prices[index] > high:
                pos = 1.0
                hold_counter = hold_days
            elif prices[index] < low:
                pos = -1.0
                hold_counter = hold_days

        position[index] = pos

    strategy_returns = position[channel:-1] * returns[channel + 1 :]
    return sharpe(strategy_returns)


PARAM_GRID = {
    "channel": [5, 10, 15, 20, 30, 40, 60],
    "hold_days": [3, 5, 10, 15, 20, 30],
}
