"""
Strategy backtests for use with OverfitDetector.

Each strategy function has the signature:
    backtest(params: dict, returns: np.ndarray) -> float  (annualized Sharpe)
"""

from .breakout import breakout_backtest
from .breakout import PARAM_GRID as BREAKOUT_GRID
from .dual_momentum import dual_momentum_backtest
from .dual_momentum import PARAM_GRID as DUAL_MOMENTUM_GRID
from .mean_reversion import mean_reversion_backtest
from .mean_reversion import PARAM_GRID as MEAN_REVERSION_GRID
from .momentum import momentum_backtest
from .momentum import PARAM_GRID as MOMENTUM_GRID
from .pairs import pairs_backtest
from .pairs import PARAM_GRID as PAIRS_GRID
from .volatility import vol_regime_backtest
from .volatility import PARAM_GRID as VOL_REGIME_GRID

PARAM_GRIDS = {
    'momentum': MOMENTUM_GRID,
    'mean_reversion': MEAN_REVERSION_GRID,
    'breakout': BREAKOUT_GRID,
    'vol_regime': VOL_REGIME_GRID,
    'dual_momentum': DUAL_MOMENTUM_GRID,
    'pairs': PAIRS_GRID,
}

BACKTEST_FNS = {
    'momentum': momentum_backtest,
    'mean_reversion': mean_reversion_backtest,
    'breakout': breakout_backtest,
    'vol_regime': vol_regime_backtest,
    'dual_momentum': dual_momentum_backtest,
    'pairs': pairs_backtest,
}

__all__ = [
    'momentum_backtest',
    'mean_reversion_backtest',
    'breakout_backtest',
    'vol_regime_backtest',
    'dual_momentum_backtest',
    'pairs_backtest',
    'PARAM_GRIDS',
    'BACKTEST_FNS',
]
