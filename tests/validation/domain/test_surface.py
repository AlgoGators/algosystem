"""
Tests for surface analysis:
- Structure and sanity of surface metrics
- Plateau vs spike detection
- Sobol indices detect dominant parameters
- Cross-strategy surface comparison
"""

import numpy as np

from algosystem.validation import OverfitDetector
from tests.validation.conftest import backtest_noise


def sharpe(returns):
    if len(returns) < 2:
        return 0.0
    mean = np.mean(returns)
    std = np.std(returns, ddof=1)
    if std < 1e-12:
        return 0.0
    return (mean / std) * np.sqrt(252)


class TestSurfaceAnalysisStructure:
    def test_returns_dict(self, noise_returns, medium_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=medium_grid,
            n_reps=50,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        sa = res.surface_analysis()
        assert isinstance(sa, dict)

    def test_expected_keys(self, noise_returns, medium_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=medium_grid,
            n_reps=50,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        sa = res.surface_analysis()
        for k in [
            "robustness_ratio",
            "frac_positive",
            "frac_above_half",
            "plateau_score",
            "cv_neighbors",
            "peak_to_neighbor",
            "per_param_sensitivity",
        ]:
            assert k in sa

    def test_metric_ranges(self, noise_returns, medium_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=medium_grid,
            n_reps=50,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        sa = res.surface_analysis()
        assert sa["robustness_ratio"] >= 0
        assert 0 <= sa["frac_positive"] <= 1
        assert 0 <= sa["frac_above_half"] <= 1
        assert 0 <= sa["plateau_score"] <= 1

    def test_sobol_nonnegative(self, noise_returns, medium_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=medium_grid,
            n_reps=50,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        sa = res.surface_analysis()
        pps = sa["per_param_sensitivity"]
        assert "lookback" in pps
        assert "threshold" in pps
        assert all(v["sobol_first"] >= 0 for v in pps.values())


class TestPlateauVsSpike:
    def test_flat_surface(self):
        rng = np.random.default_rng(42)
        flat_returns = rng.normal(0.0005, 0.01, size=500)

        def flat_backtest(params, returns):
            return sharpe(returns)

        det = OverfitDetector(
            backtest_fn=flat_backtest,
            returns=flat_returns,
            param_grid={"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.001, 0.002]},
            n_reps=20,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        sa = res.surface_analysis()
        assert abs(sa["robustness_ratio"] - 1.0) < 0.01
        assert sa["plateau_score"] > 0.9

    def test_spiky_worse_than_flat(self):
        rng = np.random.default_rng(42)
        flat_returns = rng.normal(0.0005, 0.01, size=500)

        def flat_backtest(params, returns):
            return sharpe(returns)

        def spiky_backtest(params, returns):
            if params["lookback"] == 10 and params["threshold"] == 0.001:
                return 3.0
            return rng.normal(0, 0.2)

        grid = {"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.001, 0.002]}

        sa_flat = (
            OverfitDetector(
                backtest_fn=flat_backtest,
                returns=flat_returns,
                param_grid=grid,
                n_reps=20,
                n_workers=1,
                seed=42,
            )
            .run()
            .surface_analysis()
        )

        sa_spiky = (
            OverfitDetector(
                backtest_fn=spiky_backtest,
                returns=flat_returns,
                param_grid=grid,
                n_reps=20,
                n_workers=1,
                seed=42,
            )
            .run()
            .surface_analysis()
        )

        assert sa_spiky["robustness_ratio"] < sa_flat["robustness_ratio"]
        assert sa_spiky["plateau_score"] < sa_flat["plateau_score"]


class TestSobolDominantParam:
    def test_lookback_dominates(self):
        def lookback_dependent(params, returns):
            return 5.0 / (1 + abs(params["lookback"] - 20))

        rng = np.random.default_rng(42)
        returns = rng.normal(0, 0.01, size=300)
        det = OverfitDetector(
            backtest_fn=lookback_dependent,
            returns=returns,
            param_grid={
                "lookback": [5, 10, 15, 20, 30, 40, 60],
                "threshold": [0.0, 0.001, 0.002, 0.003],
            },
            n_reps=20,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        sa = res.surface_analysis()
        pps = sa["per_param_sensitivity"]
        assert pps["lookback"]["sobol_first"] > pps["threshold"]["sobol_first"]
        assert pps["lookback"]["sobol_first"] > 0.5
        assert pps["threshold"]["sobol_first"] < 0.05
