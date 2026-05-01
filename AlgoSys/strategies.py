"""
Quant strategy backtest functions for use with OverfitDetector.

Each function has the signature:
    backtest(params: dict, returns: np.ndarray) -> float  (annualized Sharpe)

Strategy archetypes covered:
    1. Momentum / trend-following
    2. Mean reversion (Bollinger / z-score)
    3. Breakout (Donchian channel)
    4. Volatility regime switching
    5. Dual momentum (absolute + relative)
    6. Mean-reversion pairs (spread z-score)
"""

from __future__ import annotations

import numpy as np


def _sharpe(returns: np.ndarray, annualize: float = 252.0) -> float:
    """Annualized Sharpe from a daily returns array."""
    if len(returns) < 2:
        return 0.0
    m = np.mean(returns)
    s = np.std(returns, ddof=1)
    if s < 1e-12:
        return 0.0
    return (m / s) * np.sqrt(annualize)


# -----------------------------------------------------------------------
# 1. Momentum / trend-following
# -----------------------------------------------------------------------

def momentum_backtest(params, returns):
    """
    Long when rolling mean > threshold, flat otherwise.

    Parameters:
        lookback : int   — rolling window length
        threshold: float — signal threshold for entry
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
    return _sharpe(signal[lb:-1] * returns[lb + 1:])


# -----------------------------------------------------------------------
# 2. Mean reversion (Bollinger z-score)
# -----------------------------------------------------------------------

def mean_reversion_backtest(params, returns):
    """
    Go long when z-score < -entry_z, exit when z-score crosses exit_z.
    Go short when z-score > entry_z, exit at -exit_z.

    Parameters:
        lookback: int   — window for rolling mean/std
        entry_z : float — z-score threshold to enter (positive)
        exit_z  : float — z-score threshold to exit (positive, smaller)
    """
    lb = params['lookback']
    entry_z = params['entry_z']
    exit_z = params.get('exit_z', 0.0)
    n = len(returns)
    if n <= lb + 1:
        return 0.0

    prices = np.cumsum(returns) + 100.0  # synthetic price level
    position = np.zeros(n)
    pos = 0.0

    # Precompute rolling mean and std
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
    return _sharpe(strat_ret)


# -----------------------------------------------------------------------
# 3. Breakout (Donchian channel)
# -----------------------------------------------------------------------

def breakout_backtest(params, returns):
    """
    Go long on N-day high breakout, go short on N-day low breakout.
    Exit after hold_days.

    Parameters:
        channel  : int   — Donchian channel lookback
        hold_days: int   — holding period after breakout
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
    return _sharpe(strat_ret)


# -----------------------------------------------------------------------
# 4. Volatility regime switching
# -----------------------------------------------------------------------

def vol_regime_backtest(params, returns):
    """
    Reduce exposure in high-vol regimes, increase in low-vol.
    Uses rolling realized vol vs a threshold.

    Parameters:
        vol_lookback : int   — window for vol estimation
        vol_threshold: float — above this vol, scale down exposure
        low_weight   : float — weight when vol > threshold
        high_weight  : float — weight when vol <= threshold
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

    strat_ret = weights[vlb:-1] * returns[vlb + 1:]
    return _sharpe(strat_ret)


# -----------------------------------------------------------------------
# 5. Dual momentum (absolute + relative via two lookbacks)
# -----------------------------------------------------------------------

def dual_momentum_backtest(params, returns):
    """
    Combines a fast and slow momentum signal.
    Long when both are positive, short when both negative, flat otherwise.

    Parameters:
        fast_lookback: int — short lookback
        slow_lookback: int — long lookback
        threshold    : float — minimum signal magnitude
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

    strat_ret = signal[warmup:-1] * returns[warmup + 1:]
    return _sharpe(strat_ret)


# -----------------------------------------------------------------------
# 6. Mean-reversion pairs / spread
# -----------------------------------------------------------------------

def pairs_backtest(params, returns):
    """
    Simulates pairs trading on a synthetic spread.
    Constructs a "spread" by combining the return series with a lagged/
    inverted version of itself (proxy for a second correlated asset).

    Parameters:
        lookback: int   — window for spread z-score
        entry_z : float — z-score entry threshold
        exit_z  : float — z-score exit threshold
        lag     : int   — lag for synthetic second leg
    """
    lb = params['lookback']
    entry_z = params['entry_z']
    exit_z = params.get('exit_z', 0.0)
    lag = params.get('lag', 1)
    n = len(returns)
    warmup = lb + lag
    if n <= warmup + 1:
        return 0.0

    # Synthetic spread: returns minus lagged returns (mean-reverting by construction)
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
    return _sharpe(strat_ret)


# -----------------------------------------------------------------------
# Data generators
# -----------------------------------------------------------------------

def generate_noise(n=3000, seed=42):
    """Pure IID noise — no exploitable structure."""
    return np.random.default_rng(seed).normal(0.00005, 0.01, size=n)


def generate_trending(n=3000, seed=42):
    """Regime-switching trending data (momentum-exploitable)."""
    rng = np.random.default_rng(seed)
    returns = np.empty(n)
    regime = 1.0
    for i in range(n):
        if rng.random() < 0.005:
            regime *= -1
        returns[i] = regime * 0.0015 + rng.normal(0, 0.01)
    return returns


def generate_mean_reverting(n=3000, seed=42):
    """AR(1) mean-reverting returns (mean-reversion exploitable)."""
    rng = np.random.default_rng(seed)
    returns = np.empty(n)
    returns[0] = rng.normal(0, 0.01)
    for i in range(1, n):
        returns[i] = -0.15 * returns[i - 1] + rng.normal(0.0002, 0.01)
    return returns


def generate_volatile_regimes(n=3000, seed=42):
    """Alternating high/low vol regimes (vol-strategy exploitable)."""
    rng = np.random.default_rng(seed)
    returns = np.empty(n)
    high_vol = False
    for i in range(n):
        if rng.random() < 0.003:
            high_vol = not high_vol
        vol = 0.025 if high_vol else 0.008
        returns[i] = rng.normal(0.0003, vol)
    return returns


# -----------------------------------------------------------------------
# Standard parameter grids per strategy
# -----------------------------------------------------------------------

PARAM_GRIDS = {
    'momentum': {
        'lookback': [3, 5, 10, 15, 20, 30, 40, 60, 80, 100],
        'threshold': [-0.001, -0.0005, 0.0, 0.0002, 0.0005, 0.001, 0.002, 0.003],
    },
    'mean_reversion': {
        'lookback': [10, 15, 20, 30, 40, 60],
        'entry_z': [1.0, 1.5, 2.0, 2.5, 3.0],
        'exit_z': [0.0, 0.25, 0.5],
    },
    'breakout': {
        'channel': [5, 10, 15, 20, 30, 40, 60],
        'hold_days': [3, 5, 10, 15, 20, 30],
    },
    'vol_regime': {
        'vol_lookback': [10, 20, 30, 40, 60],
        'vol_threshold': [0.10, 0.15, 0.20, 0.25, 0.30, 0.35],
        'low_weight': [0.1, 0.3, 0.5],
        'high_weight': [0.8, 1.0, 1.5],
    },
    'dual_momentum': {
        'fast_lookback': [3, 5, 10, 15],
        'slow_lookback': [20, 40, 60, 80, 100],
        'threshold': [0.0, 0.0003, 0.0005, 0.001],
    },
    'pairs': {
        'lookback': [10, 20, 30, 40, 60],
        'entry_z': [1.0, 1.5, 2.0, 2.5],
        'exit_z': [0.0, 0.25, 0.5],
        'lag': [1, 2, 3, 5],
    },
}

BACKTEST_FNS = {
    'momentum': momentum_backtest,
    'mean_reversion': mean_reversion_backtest,
    'breakout': breakout_backtest,
    'vol_regime': vol_regime_backtest,
    'dual_momentum': dual_momentum_backtest,
    'pairs': pairs_backtest,
}
