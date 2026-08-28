"""
Transaction cost models for realistic strategy backtesting.

Without costs, a strategy with Sharpe 2.0 and 500% annual turnover
might have Sharpe 0.3 in reality. These models apply friction to
position-weighted returns so the overfitting detector validates
net-of-cost performance.

Models:
    FixedCosts      — flat bps per trade (simplest)
    SpreadCosts     — half bid-ask spread per trade
    SquareRootImpact — institutional standard: impact ~ sqrt(size/volume)
    apply_costs     — convenience function wrapping a backtest function
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from algosystem.shared.errors import ValidationError


@dataclass(frozen=True)
class CostModel:
    """
    Transaction cost configuration.

    Parameters
    ----------
    commission_bps : float
        Commission per trade in basis points (e.g., 5.0 = 0.05%).
    spread_bps : float
        Half bid-ask spread in basis points. Applied on each entry/exit.
    market_impact_bps : float
        Additional impact cost in basis points (volume-independent).
    slippage_pct : float
        Percentage slippage per trade (e.g., 0.001 = 0.1%).
    """

    commission_bps: float = 5.0
    spread_bps: float = 2.0
    market_impact_bps: float = 0.0
    slippage_pct: float = 0.0

    @property
    def total_cost_per_trade_bps(self) -> float:
        """Total one-way cost in basis points."""
        return self.commission_bps + self.spread_bps + self.market_impact_bps

    @property
    def total_cost_per_trade_decimal(self) -> float:
        """Total one-way cost as a decimal fraction."""
        return self.total_cost_per_trade_bps / 10000.0 + self.slippage_pct


# Preset cost models for common scenarios
ZERO_COST = CostModel(commission_bps=0, spread_bps=0)
RETAIL_EQUITY = CostModel(commission_bps=5.0, spread_bps=3.0)
INSTITUTIONAL_EQUITY = CostModel(commission_bps=1.0, spread_bps=1.0, market_impact_bps=2.0)
CRYPTO_SPOT = CostModel(commission_bps=10.0, spread_bps=5.0)
FUTURES = CostModel(commission_bps=2.0, spread_bps=1.0)


def compute_turnover(positions: np.ndarray) -> np.ndarray:
    """
    Compute per-period turnover from a position array.

    Turnover at time t = |position[t] - position[t-1]|.
    Turnover[0] = |position[0]| (initial entry).

    Returns array of same length as positions.
    """
    turnover = np.empty(len(positions))
    turnover[0] = abs(positions[0])
    turnover[1:] = np.abs(np.diff(positions))
    return turnover


def apply_transaction_costs(
    returns: np.ndarray,
    positions: np.ndarray,
    cost_model: CostModel,
) -> np.ndarray:
    """
    Apply transaction costs to strategy returns.

    Parameters
    ----------
    returns : np.ndarray
        Gross asset returns (not position-weighted).
    positions : np.ndarray
        Position signal array (same length as returns). Values like
        1.0 = long, -1.0 = short, 0.0 = flat.
    cost_model : CostModel
        Cost configuration.

    Returns
    -------
    np.ndarray
        Net-of-cost strategy returns.
    """
    n = len(returns)
    if len(positions) != n:
        raise ValidationError(
            f"returns ({n}) and positions ({len(positions)}) must have same length"
        )

    # Gross strategy returns = position * asset return
    gross = positions * returns

    # Turnover: position changes incur costs
    turnover = compute_turnover(positions)

    # Cost per period = turnover * cost_per_trade
    cost_per_period = turnover * cost_model.total_cost_per_trade_decimal

    return gross - cost_per_period


def compute_trade_log(
    positions: np.ndarray,
    returns: np.ndarray,
    cost_model: CostModel | None = None,
) -> list[dict]:
    """
    Extract a trade log from position and return arrays.

    Each trade is a dict with:
        entry_idx, exit_idx, direction, duration, gross_pnl, cost, net_pnl

    Parameters
    ----------
    positions : np.ndarray
        Position signal array.
    returns : np.ndarray
        Asset returns.
    cost_model : CostModel or None
        If provided, costs are computed per trade.

    Returns
    -------
    list of dict — one per round-trip trade
    """
    cost = cost_model or ZERO_COST
    trades = []
    n = len(positions)

    in_trade = False
    entry_idx = 0
    direction = 0.0
    cum_gross = 0.0

    for t in range(n):
        if not in_trade and positions[t] != 0:
            # Entry
            in_trade = True
            entry_idx = t
            direction = positions[t]
            cum_gross = 0.0
        elif in_trade:
            cum_gross += direction * returns[t]

            # Exit: position goes to zero or flips
            if positions[t] == 0 or (t < n - 1 and positions[t] != direction):
                entry_cost = abs(direction) * cost.total_cost_per_trade_decimal
                exit_cost = abs(direction) * cost.total_cost_per_trade_decimal
                total_cost = entry_cost + exit_cost

                trades.append(
                    {
                        "entry_idx": entry_idx,
                        "exit_idx": t,
                        "direction": "long" if direction > 0 else "short",
                        "duration": t - entry_idx,
                        "gross_pnl": float(cum_gross),
                        "cost": float(total_cost),
                        "net_pnl": float(cum_gross - total_cost),
                    }
                )
                in_trade = False

                # If position flipped (not just exited), start new trade
                if t < n - 1 and positions[t] != 0 and positions[t] != direction:
                    in_trade = True
                    entry_idx = t
                    direction = positions[t]
                    cum_gross = 0.0

    # Close any open trade at end
    if in_trade:
        entry_cost = abs(direction) * cost.total_cost_per_trade_decimal
        exit_cost = abs(direction) * cost.total_cost_per_trade_decimal
        trades.append(
            {
                "entry_idx": entry_idx,
                "exit_idx": n - 1,
                "direction": "long" if direction > 0 else "short",
                "duration": n - 1 - entry_idx,
                "gross_pnl": float(cum_gross),
                "cost": float(entry_cost + exit_cost),
                "net_pnl": float(cum_gross - entry_cost - exit_cost),
            }
        )

    return trades


def trade_log_summary(trades: list[dict]) -> dict:
    """
    Compute summary statistics from a trade log.

    Returns dict with: n_trades, win_rate, avg_pnl, profit_factor,
    avg_duration, total_costs, gross_pnl, net_pnl, turnover_trades_per_year
    """
    if not trades:
        return {
            "n_trades": 0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "profit_factor": 0.0,
            "avg_duration": 0.0,
            "total_costs": 0.0,
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
        }

    n = len(trades)
    wins = sum(1 for t in trades if t["net_pnl"] > 0)
    gross_wins = sum(t["net_pnl"] for t in trades if t["net_pnl"] > 0)
    gross_losses = abs(sum(t["net_pnl"] for t in trades if t["net_pnl"] <= 0))
    total_duration = sum(t["duration"] for t in trades)
    total_costs = sum(t["cost"] for t in trades)
    gross_pnl = sum(t["gross_pnl"] for t in trades)
    net_pnl = sum(t["net_pnl"] for t in trades)

    return {
        "n_trades": n,
        "win_rate": wins / n if n > 0 else 0.0,
        "avg_pnl": net_pnl / n if n > 0 else 0.0,
        "profit_factor": gross_wins / gross_losses if gross_losses > 1e-12 else float("inf"),
        "avg_duration": total_duration / n if n > 0 else 0.0,
        "total_costs": total_costs,
        "gross_pnl": gross_pnl,
        "net_pnl": net_pnl,
    }


def wrap_backtest_with_costs(
    backtest_fn: Callable,
    cost_model: CostModel,
) -> Callable:
    """
    Wrap a backtest function to apply transaction costs.

    The wrapped function has the same signature as the original:
        (params, returns) -> float (Sharpe)

    but computes net-of-cost Sharpe instead of gross Sharpe.

    This requires the backtest function to be "position-aware" — it must
    return positions as a second element if called with _return_positions=True
    in params. If not supported, falls back to estimating turnover from
    the Sharpe ratio change.

    For the built-in strategies, use the infrastructure make_cost_aware() helper
    instead.
    """
    return TransactionCostBacktest(backtest_fn=backtest_fn, cost_model=cost_model)


@dataclass(frozen=True)
class TransactionCostBacktest:
    """Picklable generic transaction-cost wrapper for position-aware backtests."""

    backtest_fn: Callable
    cost_model: CostModel

    def __call__(self, params: dict, returns: np.ndarray) -> float:
        position_params = dict(params)
        position_params["_return_positions"] = True
        result = self.backtest_fn(position_params, returns)
        if isinstance(result, tuple) and len(result) >= 2:
            positions = np.asarray(result[1], dtype=np.float64)
            net_returns = apply_transaction_costs(
                np.asarray(returns, dtype=np.float64),
                positions,
                self.cost_model,
            )
            return _sharpe(net_returns)

        gross_sharpe = float(self.backtest_fn(params, returns))
        lookback = params.get("lookback", params.get("channel", params.get("vol_lookback", 20)))
        estimated_annual_trades = 252.0 / max(lookback, 1) * 2
        annual_cost = estimated_annual_trades * self.cost_model.total_cost_per_trade_decimal
        std_approx = 0.01 * np.sqrt(252)
        if std_approx > 1e-12:
            return gross_sharpe - annual_cost / std_approx
        return gross_sharpe


def _sharpe(returns: np.ndarray, annualize: float = 252.0) -> float:
    if len(returns) < 2:
        return 0.0
    mean = np.mean(returns)
    std = np.std(returns, ddof=1)
    if std < 1e-12:
        return 0.0
    return float((mean / std) * np.sqrt(annualize))
