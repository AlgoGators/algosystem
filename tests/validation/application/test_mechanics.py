"""
Tests for detector mechanics:
- Subsampling consistency
- Edge cases (single param, constant returns, n_reps=1)
- Sort indices correctness
- Comparison direction (maximize Sharpe)
- Reproducibility with same seed
- Multiprocessing consistency
- Null distribution shape
"""

import numpy as np

from algosystem.validation import OverfitDetector
from tests.validation.conftest import backtest_noise


class TestSubsampling:
    def test_correct_param_count(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={
                "lookback": [3, 5, 8, 10, 15, 20, 30, 40],
                "threshold": [0.0, 0.0005, 0.001, 0.002, 0.003],
            },
            n_reps=50,
            max_param_trials=5,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.n_params == 5

    def test_consistent_array_lengths(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={
                "lookback": [3, 5, 8, 10, 15, 20, 30, 40],
                "threshold": [0.0, 0.0005, 0.001, 0.002, 0.003],
            },
            n_reps=50,
            max_param_trials=5,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert len(res.original_sharpes) == 5
        assert len(res.solo_pvalues) == 5
        assert len(res.sort_indices) == 5
        assert len(res.unbiased_pvalues) == 5


class TestEdgeCases:
    def test_single_param(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [10], "threshold": [0.001]},
            n_reps=50,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.n_params == 1
        assert abs(res.solo_pvalues[0] - res.unbiased_pvalue) < 1e-10

    def test_constant_returns_no_crash(self):
        const_returns = np.ones(300) * 0.001
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=const_returns,
            param_grid={"lookback": [5, 10], "threshold": [0.0]},
            n_reps=20,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res is not None

    def test_n_reps_one(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [5, 10], "threshold": [0.0]},
            n_reps=1,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.n_reps == 1
        assert np.all(res.solo_pvalues >= 0)
        assert np.all(res.solo_pvalues <= 1)


class TestSortIndices:
    def test_descending_order(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.001, 0.002]},
            n_reps=50,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        sorted_sharpes = res.original_sharpes[res.sort_indices]
        diffs = np.diff(sorted_sharpes)
        assert np.all(diffs <= 1e-12)

    def test_first_is_best(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.001, 0.002]},
            n_reps=50,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert res.sort_indices[0] == res.best_param_index


class TestComparisonDirection:
    def test_best_is_max(self, noise_returns, small_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=small_grid,
            n_reps=100,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert abs(res.best_sharpe - np.max(res.original_sharpes)) < 1e-10
        assert res.original_sharpes[res.best_param_index] == np.max(res.original_sharpes)


class TestReproducibility:
    def test_same_seed_same_results(self, noise_returns, small_grid):
        kwargs = {
            "backtest_fn": backtest_noise,
            "returns": noise_returns,
            "param_grid": small_grid,
            "n_reps": 50,
            "n_workers": 1,
            "seed": 42,
        }
        res1 = OverfitDetector(**kwargs).run()
        res2 = OverfitDetector(**kwargs).run()

        assert np.array_equal(res1.original_sharpes, res2.original_sharpes)
        assert np.array_equal(res1.null_best_sharpes, res2.null_best_sharpes)
        assert np.array_equal(res1.solo_pvalues, res2.solo_pvalues)
        assert res1.unbiased_pvalue == res2.unbiased_pvalue


class TestMultiprocessing:
    def test_single_vs_multi(self, noise_returns, small_grid):
        kwargs_base = {
            "backtest_fn": backtest_noise,
            "returns": noise_returns,
            "param_grid": small_grid,
            "n_reps": 50,
            "seed": 42,
        }
        res_single = OverfitDetector(**kwargs_base, n_workers=1).run()
        res_multi = OverfitDetector(**kwargs_base, n_workers=2).run()

        assert np.array_equal(res_single.original_sharpes, res_multi.original_sharpes)
        assert np.array_equal(res_single.null_best_sharpes, res_multi.null_best_sharpes)
        assert res_single.unbiased_pvalue == res_multi.unbiased_pvalue


class TestNullDistributionShape:
    def test_correct_length(self):
        rng = np.random.default_rng(42)
        returns = rng.normal(0, 0.01, size=1000)
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns,
            param_grid={"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.0005, 0.001, 0.002]},
            n_reps=300,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert len(res.null_best_sharpes) == 300
        assert np.all(np.isfinite(res.null_best_sharpes))
        assert np.mean(res.null_best_sharpes > 0) > 0.5
