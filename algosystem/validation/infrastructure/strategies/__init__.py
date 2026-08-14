"""Shipped validation strategy archetypes."""

from __future__ import annotations

from types import MappingProxyType

from algosystem.validation.domain.strategy import ParameterGrid, StrategySpec

from ._cost_wrapper import CostAwareBacktest, make_cost_aware
from .breakout import PARAM_GRID as BREAKOUT_GRID
from .breakout import breakout_backtest
from .dual_momentum import PARAM_GRID as DUAL_MOMENTUM_GRID
from .dual_momentum import dual_momentum_backtest
from .mean_reversion import PARAM_GRID as MEAN_REVERSION_GRID
from .mean_reversion import mean_reversion_backtest
from .momentum import PARAM_GRID as MOMENTUM_GRID
from .momentum import momentum_backtest
from .pairs import PARAM_GRID as PAIRS_GRID
from .pairs import pairs_backtest
from .volatility import PARAM_GRID as VOLATILITY_GRID
from .volatility import vol_regime_backtest, volatility_backtest

_CANONICAL_PARAM_GRIDS = {
    "momentum": MOMENTUM_GRID,
    "mean_reversion": MEAN_REVERSION_GRID,
    "breakout": BREAKOUT_GRID,
    "dual_momentum": DUAL_MOMENTUM_GRID,
    "pairs": PAIRS_GRID,
    "volatility": VOLATILITY_GRID,
}

STRATEGY_ALIASES = MappingProxyType({"vol_regime": "volatility"})

PARAM_GRIDS = MappingProxyType(
    {
        **_CANONICAL_PARAM_GRIDS,
        "vol_regime": VOLATILITY_GRID,
    }
)

BACKTEST_FNS = MappingProxyType(
    {
        "momentum": momentum_backtest,
        "mean_reversion": mean_reversion_backtest,
        "breakout": breakout_backtest,
        "dual_momentum": dual_momentum_backtest,
        "pairs": pairs_backtest,
        "volatility": volatility_backtest,
        "vol_regime": vol_regime_backtest,
    }
)

STRATEGY_REGISTRY = MappingProxyType(
    {
        name: StrategySpec(
            name=name,
            backtest_fn_path=f"{BACKTEST_FNS[name].__module__}.{BACKTEST_FNS[name].__qualname__}",
            parameter_grid=ParameterGrid(grid),
        )
        for name, grid in _CANONICAL_PARAM_GRIDS.items()
    }
)


def get_strategy_spec(name: str) -> StrategySpec:
    """Return a shipped strategy spec by canonical name or alias."""
    canonical = STRATEGY_ALIASES.get(name, name)
    return STRATEGY_REGISTRY[canonical]


__all__ = [
    "BACKTEST_FNS",
    "PARAM_GRIDS",
    "STRATEGY_ALIASES",
    "STRATEGY_REGISTRY",
    "CostAwareBacktest",
    "breakout_backtest",
    "dual_momentum_backtest",
    "get_strategy_spec",
    "make_cost_aware",
    "mean_reversion_backtest",
    "momentum_backtest",
    "pairs_backtest",
    "vol_regime_backtest",
    "volatility_backtest",
]
