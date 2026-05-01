"""Breakout (Donchian channel) strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def breakout_backtest(params, returns):
    """
    Go long on N-day high breakout, go short on N-day low breakout.
    Exit after hold_days.

    Parameters:
        channel  : int -- Donchian channel lookback
        hold_days: int -- holding period after breakout
    """
    channel = params['channel']
    hold_days = params['hold_days']
    n = len(returns)
    if n <= channel + hold_days:
        return 0.0

    prices = np.cumsum(returns) + 100.0
    position = np.zeros(n)
    hold_counter = 0
    pos = 0.0

    for i in range(channel, n):
        hi = np.max(prices[i - channel:i])
        lo = np.min(prices[i - channel:i])

        if hold_counter > 0:
            hold_counter -= 1
            if hold_counter == 0:
                pos = 0.0

        if pos == 0.0:
            if prices[i] > hi:
                pos = 1.0
                hold_counter = hold_days
            elif prices[i] < lo:
                pos = -1.0
                hold_counter = hold_days

        position[i] = pos

    strat_ret = position[channel:-1] * returns[channel + 1:]
    return sharpe(strat_ret)


PARAM_GRID = {
    'channel': [5, 10, 15, 20, 30, 40, 60],
    'hold_days': [3, 5, 10, 15, 20, 30],
}
