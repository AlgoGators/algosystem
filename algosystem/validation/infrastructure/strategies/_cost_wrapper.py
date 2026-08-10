"""Picklable cost-aware wrappers for validation strategy backtests."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Callable

import numpy as np

from algosystem.shared.errors import ValidationError

from ._utils import sharpe


@dataclass(frozen=True)
class CostAwareBacktest:
    """Picklable callable that applies per-trade costs to a strategy backtest."""

    backtest_fn_path: str
    cost_per_trade: float
    strategy_name: str | None = None

    def __call__(self, params, returns):
        n = len(returns)

        if self.strategy_name is not None:
            positions, strategy_returns, warmup = _get_positions_and_returns(
                self.strategy_name,
                params,
                returns,
            )
            if positions is not None:
                turnover = np.empty(n)
                turnover[0] = abs(positions[0])
                turnover[1:] = np.abs(np.diff(positions))
                net_returns = strategy_returns - turnover * self.cost_per_trade
                if warmup < n:
                    return sharpe(net_returns[warmup:])
                return 0.0

        gross_sharpe = _load_callable(self.backtest_fn_path)(params, returns)
        lookback = params.get("lookback", params.get("channel", params.get("vol_lookback", 20)))
        estimated_annual_trades = 252.0 / max(lookback, 1) * 2
        annual_cost = estimated_annual_trades * self.cost_per_trade
        std_approx = 0.01 * np.sqrt(252)
        if std_approx > 1e-12:
            sharpe_reduction = annual_cost / std_approx
            return gross_sharpe - sharpe_reduction
        return gross_sharpe


def make_cost_aware(
    backtest_fn: Callable,
    cost_model,
    strategy_name: str | None = None,
) -> CostAwareBacktest:
    """
    Wrap a backtest function to return net-of-cost Sharpe.

    The returned object has the same public call signature as the original
    strategy function, but is a module-level callable class instance so it can
    be pickled under the ``spawn`` multiprocessing start method.
    """
    return CostAwareBacktest(
        backtest_fn_path=_qualified_path_for(backtest_fn),
        cost_per_trade=cost_model.total_cost_per_trade_decimal,
        strategy_name=strategy_name,
    )


def _get_positions_and_returns(
    backtest_fn_name: str,
    params: dict,
    returns: np.ndarray,
) -> tuple[np.ndarray | None, np.ndarray | None, int]:
    """Re-implement built-in signal logic to extract positions and returns."""
    n = len(returns)
    strategy_name = "volatility" if backtest_fn_name == "vol_regime" else backtest_fn_name

    if strategy_name == "momentum":
        lookback = params["lookback"]
        threshold = params["threshold"]
        if n <= lookback:
            return np.zeros(n), np.zeros(n), n
        cumsum = np.cumsum(returns)
        rolling_mean = np.empty(n)
        rolling_mean[:lookback] = 0.0
        rolling_mean[lookback:] = (cumsum[lookback:] - cumsum[: n - lookback]) / lookback
        positions = (rolling_mean > threshold).astype(float)
        strategy_returns = np.zeros(n)
        strategy_returns[lookback + 1 :] = positions[lookback:-1] * returns[lookback + 1 :]
        return positions, strategy_returns, lookback

    if strategy_name == "breakout":
        channel = params["channel"]
        hold_days = params["hold_days"]
        if n <= channel + hold_days:
            return np.zeros(n), np.zeros(n), n
        prices = np.cumsum(returns) + 100.0
        positions = np.zeros(n)
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
            positions[index] = pos
        strategy_returns = np.zeros(n)
        strategy_returns[channel + 1 :] = positions[channel:-1] * returns[channel + 1 :]
        return positions, strategy_returns, channel

    if strategy_name == "volatility":
        vol_lookback = params["vol_lookback"]
        vol_threshold = params["vol_threshold"]
        low_weight = params.get("low_weight", 0.3)
        high_weight = params.get("high_weight", 1.0)
        if n <= vol_lookback:
            return np.zeros(n), np.zeros(n), n
        weights = np.empty(n)
        weights[:vol_lookback] = 1.0
        for index in range(vol_lookback, n):
            realized_vol = np.std(returns[index - vol_lookback : index], ddof=1) * np.sqrt(252)
            weights[index] = low_weight if realized_vol > vol_threshold else high_weight
        strategy_returns = np.zeros(n)
        strategy_returns[vol_lookback + 1 :] = (
            weights[vol_lookback:-1] * returns[vol_lookback + 1 :]
        )
        return weights, strategy_returns, vol_lookback

    return None, None, 0


def _qualified_path_for(backtest_fn: Callable) -> str:
    module = getattr(backtest_fn, "__module__", None)
    qualname = getattr(backtest_fn, "__qualname__", None)
    if not module or not qualname or "<locals>" in qualname:
        raise ValidationError("backtest_fn must be a module-level callable")
    return f"{module}.{qualname}"


def _load_callable(path: str) -> Callable:
    module_path, _, attr_path = path.rpartition(".")
    if not module_path or not attr_path:
        raise ValidationError("backtest_fn path must include a module and attribute")
    try:
        module = import_module(module_path)
        resolved: object = module
        for attr in attr_path.split("."):
            resolved = getattr(resolved, attr)
    except (ImportError, AttributeError) as exc:
        raise ValidationError(f"could not resolve backtest_fn from path {path!r}") from exc
    if not callable(resolved):
        raise ValidationError(f"resolved backtest_fn is not callable: {path!r}")
    return resolved
