"""
Tests for strategy backtests:
- All 6 archetypes complete without error
- Strategies detect signal on matching data
- Walk-forward degradation concept
"""

import itertools

import numpy as np
import pytest

from algosystemv2.overfitting import OverfitDetector
from algosystemv2.overfitting.data_generators import (
    generate_mean_reverting,
    generate_noise,
    generate_trending,
)
from algosystemv2.overfitting.strategies import (
    BACKTEST_FNS,
    PARAM_GRIDS,
    breakout_backtest,
    dual_momentum_backtest,
    mean_reversion_backtest,
    momentum_backtest,
    pairs_backtest,
    vol_regime_backtest,
)


class TestAllStrategiesComplete:
    @pytest.mark.parametrize("name", list(BACKTEST_FNS.keys()))
    def test_strategy_completes(self, name):
        fn = BACKTEST_FNS[name]
        grid = {k: v[:3] for k, v in PARAM_GRIDS[name].items()}
        returns = generate_noise(n=1000, seed=hash(name) % 2**31)
        det = OverfitDetector(
            backtest_fn=fn, returns=returns, param_grid=grid,
            n_reps=20, n_workers=1, seed=42,
        )
        res = det.run()
        assert res.n_reps == 20
        assert np.all(np.isfinite(res.original_sharpes))


class TestSignalMatch:
    def test_momentum_on_trending(self):
        n_reps = 150
        res_match = OverfitDetector(
            backtest_fn=momentum_backtest,
            returns=generate_trending(n=3000, seed=42),
            param_grid={k: v[:4] for k, v in PARAM_GRIDS['momentum'].items()},
            n_reps=n_reps, n_workers=1, seed=42,
        ).run()
        res_noise = OverfitDetector(
            backtest_fn=momentum_backtest,
            returns=generate_noise(n=3000, seed=42),
            param_grid={k: v[:4] for k, v in PARAM_GRIDS['momentum'].items()},
            n_reps=n_reps, n_workers=1, seed=42,
        ).run()
        assert res_match.unbiased_pvalue < res_noise.unbiased_pvalue
        assert res_match.deflated_sharpe > res_noise.deflated_sharpe

    def test_mean_rev_on_ar1(self):
        n_reps = 150
        res_mr = OverfitDetector(
            backtest_fn=mean_reversion_backtest,
            returns=generate_mean_reverting(n=3000, seed=42),
            param_grid={k: v[:3] for k, v in PARAM_GRIDS['mean_reversion'].items()},
            n_reps=n_reps, n_workers=1, seed=42,
        ).run()
        res_noise = OverfitDetector(
            backtest_fn=mean_reversion_backtest,
            returns=generate_noise(n=3000, seed=42),
            param_grid={k: v[:3] for k, v in PARAM_GRIDS['mean_reversion'].items()},
            n_reps=n_reps, n_workers=1, seed=42,
        ).run()
        assert res_mr.unbiased_pvalue < res_noise.unbiased_pvalue


class TestWalkForward:
    def test_trending_persists_oos(self):
        trending = generate_trending(n=4000, seed=42)
        is_data = trending[:2000]
        oos_data = trending[2000:]

        grid = {'lookback': [5, 10, 20, 40], 'threshold': [0.0, 0.001]}
        keys = sorted(grid.keys())
        plist = [dict(zip(keys, c)) for c in itertools.product(*[grid[k] for k in keys])]

        is_sharpes = [momentum_backtest(p, is_data) for p in plist]
        best_idx = np.argmax(is_sharpes)
        oos_sharpe = momentum_backtest(plist[best_idx], oos_data)

        assert oos_sharpe > 0
