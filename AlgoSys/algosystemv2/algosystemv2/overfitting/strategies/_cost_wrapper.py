"""
Cost-aware wrappers for strategy backtest functions.

Wraps any strategy function to compute net-of-cost Sharpe by:
1. Running the original strategy to get gross positions/returns
2. Computing turnover from position changes
3. Subtracting transaction costs proportional to turnover
4. Returning net-of-cost Sharpe

Usage:
    from algosystemv2.overfitting.costs import CostModel, RETAIL_EQUITY
    from algosystemv2.overfitting.strategies._cost_wrapper import make_cost_aware

    net_backtest = make_cost_aware(momentum_backtest, RETAIL_EQUITY)
    sharpe = net_backtest(params, returns)  # net-of-cost Sharpe
"""

from __future__ import annotations

from typing import Callable

import numpy as np

from ._utils import sharpe


def _get_positions_and_returns(backtest_fn_name: str, params: dict,
                                returns: np.ndarray):
    """
    Re-implement the core signal logic of each built-in strategy to extract
    the position array. Returns (positions, strategy_returns, warmup).
    """
    n = len(returns)

    if backtest_fn_name == 'momentum':
        lb = params['lookback']
        th = params['threshold']
        if n <= lb:
            return np.zeros(n), np.zeros(n), n
        cumsum = np.cumsum(returns)
        rm = np.empty(n)
        rm[:lb] = 0.0
        rm[lb:] = (cumsum[lb:] - cumsum[:n - lb]) / lb
        positions = (rm > th).astype(float)
        # Lag by 1 period to match corrected momentum_backtest
        strat_ret = np.zeros(n)
        strat_ret[lb + 1:] = positions[lb:-1] * returns[lb + 1:]
        return positions, strat_ret, lb

    elif backtest_fn_name == 'breakout':
        channel = params['channel']
        hold_days = params['hold_days']
        if n <= channel + hold_days:
            return np.zeros(n), np.zeros(n), n
        prices = np.cumsum(returns) + 100.0
        positions = np.zeros(n)
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
            positions[i] = pos
        strat_ret = np.zeros(n)
        strat_ret[channel + 1:] = positions[channel:-1] * returns[channel + 1:]
        return positions, strat_ret, channel

    elif backtest_fn_name == 'vol_regime':
        vlb = params['vol_lookback']
        vth = params['vol_threshold']
        lo_w = params.get('low_weight', 0.3)
        hi_w = params.get('high_weight', 1.0)
        if n <= vlb:
            return np.zeros(n), np.zeros(n), n
        weights = np.empty(n)
        weights[:vlb] = 1.0
        for i in range(vlb, n):
            rv = np.std(returns[i - vlb:i], ddof=1) * np.sqrt(252)
            weights[i] = lo_w if rv > vth else hi_w
        strat_ret = np.zeros(n)
        # Lag by 1 period to match corrected vol_regime_backtest
        strat_ret[vlb + 1:] = weights[vlb:-1] * returns[vlb + 1:]
        return weights, strat_ret, vlb

    else:
        # Fallback: can't extract positions, estimate turnover from scratch
        return None, None, 0


def make_cost_aware(
    backtest_fn: Callable,
    cost_model,
    strategy_name: str | None = None,
) -> Callable:
    """
    Wrap a backtest function to return net-of-cost Sharpe.

    Parameters
    ----------
    backtest_fn : callable
        Original (params, returns) -> float backtest function.
    cost_model : CostModel
        Transaction cost model.
    strategy_name : str or None
        Name of the built-in strategy (e.g., 'momentum', 'breakout').
        If provided, positions are extracted for exact cost computation.
        If None, costs are estimated from turnover heuristic.

    Returns
    -------
    callable with same signature: (params, returns) -> float
    """
    cost_per_trade = cost_model.total_cost_per_trade_decimal

    def cost_aware_backtest(params, returns):
        n = len(returns)

        if strategy_name is not None:
            positions, strat_ret, warmup = _get_positions_and_returns(
                strategy_name, params, returns
            )
            if positions is not None:
                # Compute turnover from position changes
                turnover = np.empty(n)
                turnover[0] = abs(positions[0])
                turnover[1:] = np.abs(np.diff(positions))

                # Net returns = gross - turnover * cost
                net_ret = strat_ret - turnover * cost_per_trade

                # Sharpe on post-warmup net returns
                if warmup < n:
                    return sharpe(net_ret[warmup:])
                return 0.0

        # Fallback: run gross, then apply flat haircut based on
        # estimated turnover (2 trades per lookback period)
        gross_sharpe = backtest_fn(params, returns)
        lb = params.get('lookback', params.get('channel', params.get('vol_lookback', 20)))
        estimated_annual_trades = 252.0 / max(lb, 1) * 2
        annual_cost = estimated_annual_trades * cost_per_trade
        # Rough haircut: subtract annual cost from annualized mean,
        # keep std the same → Sharpe reduction
        std_approx = 0.01 * np.sqrt(252)  # ~16% annual vol assumption
        if std_approx > 1e-12:
            sharpe_reduction = annual_cost / std_approx
            return gross_sharpe - sharpe_reduction
        return gross_sharpe

    return cost_aware_backtest
