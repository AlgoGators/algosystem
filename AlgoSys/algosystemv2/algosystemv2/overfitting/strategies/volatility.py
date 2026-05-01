"""Volatility regime switching strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def vol_regime_backtest(params, returns):
    """
    Reduce exposure in high-vol regimes, increase in low-vol.
    Uses rolling realized vol vs a threshold.

    Parameters:
        vol_lookback : int   -- window for vol estimation
        vol_threshold: float -- above this vol, scale down exposure
        low_weight   : float -- weight when vol > threshold
        high_weight  : float -- weight when vol <= threshold
    """
    vlb = params['vol_lookback']
    vth = params['vol_threshold']
    lo_w = params.get('low_weight', 0.3)
    hi_w = params.get('high_weight', 1.0)
    n = len(returns)
    if n <= vlb:
        return 0.0

    weights = np.empty(n)
    weights[:vlb] = 1.0
    for i in range(vlb, n):
        rv = np.std(returns[i - vlb:i], ddof=1) * np.sqrt(252)
        weights[i] = lo_w if rv > vth else hi_w

    # Lag weights by 1 period for consistency with other strategies
    strat_ret = weights[vlb:-1] * returns[vlb + 1:]
    return sharpe(strat_ret)


PARAM_GRID = {
    'vol_lookback': [10, 20, 30, 40, 60],
    'vol_threshold': [0.10, 0.15, 0.20, 0.25, 0.30, 0.35],
    'low_weight': [0.1, 0.3, 0.5],
    'high_weight': [0.8, 1.0, 1.5],
}
