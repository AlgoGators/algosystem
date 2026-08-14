"""
Tests for strategy backtests:
- All 6 archetypes complete without error
- Strategies detect signal on matching data
- Walk-forward degradation concept
"""

import itertools
import pickle

import numpy as np
import pytest

from tests.validation._generators import generate_mean_reverting, generate_noise, generate_trending

STRATEGY_NAMES = [
    "momentum",
    "mean_reversion",
    "breakout",
    "dual_momentum",
    "pairs",
    "vol_regime",
]


class TestAllStrategiesComplete:
    @pytest.mark.parametrize("name", STRATEGY_NAMES)
    def test_strategy_completes(self, name):
        from algosystem.validation import OverfitDetector
        from algosystem.validation.infrastructure.strategies import BACKTEST_FNS, PARAM_GRIDS

        fn = BACKTEST_FNS[name]
        grid = {k: v[:3] for k, v in PARAM_GRIDS[name].items()}
        returns = generate_noise(n=1000, seed=hash(name) % 2**31)
        det = OverfitDetector(
            backtest_fn=fn,
            returns=returns,
            param_grid=grid,
            n_reps=20,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.n_reps == 20
        assert np.all(np.isfinite(res.original_sharpes))


def test_shipped_strategies_and_cost_wrappers_are_picklable():
    from algosystem.validation.domain import RETAIL_EQUITY
    from algosystem.validation.infrastructure.strategies import (
        BACKTEST_FNS,
        STRATEGY_REGISTRY,
        make_cost_aware,
    )

    returns = generate_noise(n=500, seed=123)
    for name, spec in STRATEGY_REGISTRY.items():
        params = next(spec.parameter_grid.combinations()).to_dict()
        fn = BACKTEST_FNS[name]

        loaded_fn = pickle.loads(pickle.dumps(fn))
        assert loaded_fn(params, returns) == fn(params, returns)

        cost_fn = make_cost_aware(fn, RETAIL_EQUITY, strategy_name=name)
        loaded_cost_fn = pickle.loads(pickle.dumps(cost_fn))
        assert loaded_cost_fn(params, returns) == cost_fn(params, returns)


class TestSignalMatch:
    def test_momentum_on_trending(self):
        from algosystem.validation import OverfitDetector
        from algosystem.validation.infrastructure.strategies import PARAM_GRIDS, momentum_backtest

        n_reps = 150
        res_match = OverfitDetector(
            backtest_fn=momentum_backtest,
            returns=generate_trending(n=3000, seed=42),
            param_grid={k: v[:4] for k, v in PARAM_GRIDS["momentum"].items()},
            n_reps=n_reps,
            n_workers=1,
            seed=42,
        ).run()
        res_noise = OverfitDetector(
            backtest_fn=momentum_backtest,
            returns=generate_noise(n=3000, seed=42),
            param_grid={k: v[:4] for k, v in PARAM_GRIDS["momentum"].items()},
            n_reps=n_reps,
            n_workers=1,
            seed=42,
        ).run()
        assert res_match.unbiased_pvalue < res_noise.unbiased_pvalue
        assert res_match.deflated_sharpe > res_noise.deflated_sharpe

    def test_mean_rev_on_ar1(self):
        from algosystem.validation import OverfitDetector
        from algosystem.validation.infrastructure.strategies import (
            PARAM_GRIDS,
            mean_reversion_backtest,
        )

        n_reps = 150
        res_mr = OverfitDetector(
            backtest_fn=mean_reversion_backtest,
            returns=generate_mean_reverting(n=3000, seed=42),
            param_grid={k: v[:3] for k, v in PARAM_GRIDS["mean_reversion"].items()},
            n_reps=n_reps,
            n_workers=1,
            seed=42,
        ).run()
        res_noise = OverfitDetector(
            backtest_fn=mean_reversion_backtest,
            returns=generate_noise(n=3000, seed=42),
            param_grid={k: v[:3] for k, v in PARAM_GRIDS["mean_reversion"].items()},
            n_reps=n_reps,
            n_workers=1,
            seed=42,
        ).run()
        assert res_mr.unbiased_pvalue < res_noise.unbiased_pvalue


class TestWalkForward:
    def test_trending_persists_oos(self):
        from algosystem.validation.infrastructure.strategies import momentum_backtest

        trending = generate_trending(n=4000, seed=42)
        is_data = trending[:2000]
        oos_data = trending[2000:]

        grid = {"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.001]}
        keys = sorted(grid.keys())
        plist = [dict(zip(keys, c)) for c in itertools.product(*[grid[k] for k in keys])]

        is_sharpes = [momentum_backtest(p, is_data) for p in plist]
        best_idx = np.argmax(is_sharpes)
        oos_sharpe = momentum_backtest(plist[best_idx], oos_data)

        assert oos_sharpe > 0
