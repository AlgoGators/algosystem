"""Volatility regime switching strategy."""

from __future__ import annotations

import numpy as np

from ._utils import sharpe


def volatility_backtest(params, returns):
    """Scale exposure down in high-volatility regimes and up in low-volatility regimes."""
    vol_lookback = params["vol_lookback"]
    vol_threshold = params["vol_threshold"]
    low_weight = params.get("low_weight", 0.3)
    high_weight = params.get("high_weight", 1.0)
    n = len(returns)
    if n <= vol_lookback:
        return 0.0

    weights = np.empty(n)
    weights[:vol_lookback] = 1.0
    for index in range(vol_lookback, n):
        realized_vol = np.std(returns[index - vol_lookback : index], ddof=1) * np.sqrt(252)
        weights[index] = low_weight if realized_vol > vol_threshold else high_weight

    strategy_returns = weights[vol_lookback:-1] * returns[vol_lookback + 1 :]
    return sharpe(strategy_returns)


vol_regime_backtest = volatility_backtest

PARAM_GRID = {
    "vol_lookback": [10, 20, 30, 40, 60],
    "vol_threshold": [0.10, 0.15, 0.20, 0.25, 0.30, 0.35],
    "low_weight": [0.1, 0.3, 0.5],
    "high_weight": [0.8, 1.0, 1.5],
}
