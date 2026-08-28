"""
Tests for p-value correctness:
- Formula is (b+1)/(m+1) per Phipson & Smyth (2010)
- Solo p-values uniform under the null
- Unbiased p-value >= solo p-value for best competitor
- Monotonicity of unbiased p-values
- Running-best algorithm matches brute-force reference
"""

import numpy as np

from algosystem.validation import OverfitDetector
from tests.validation.conftest import backtest_noise


class TestPvalueFormula:
    def test_no_solo_pvalue_is_zero(self, noise_returns, small_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=small_grid,
            n_reps=100,
            n_workers=1,
            seed=99,
        )
        res = det.run()
        assert np.all(res.solo_pvalues > 0)

    def test_no_unbiased_pvalue_is_zero(self, noise_returns, small_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=small_grid,
            n_reps=100,
            n_workers=1,
            seed=99,
        )
        res = det.run()
        assert np.all(res.unbiased_pvalues > 0)

    def test_minimum_pvalue(self, noise_returns, small_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=small_grid,
            n_reps=100,
            n_workers=1,
            seed=99,
        )
        res = det.run()
        min_possible = 1.0 / (res.n_reps + 1)
        assert np.min(res.solo_pvalues) >= min_possible - 1e-12

    def test_maximum_pvalue_le_one(self, noise_returns, small_grid):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid=small_grid,
            n_reps=100,
            n_workers=1,
            seed=99,
        )
        res = det.run()
        assert np.max(res.solo_pvalues) <= 1.0 + 1e-12


class TestSoloPvaluesUniform:
    def test_ks_uniformity(self):
        from scipy import stats

        rng = np.random.default_rng(123)
        solo_pvals = []
        for exp in range(80):
            returns = rng.normal(0, 0.01, size=300)
            det = OverfitDetector(
                backtest_fn=backtest_noise,
                returns=returns,
                param_grid={"lookback": [5, 10, 20], "threshold": [0.0, 0.001]},
                n_reps=100,
                n_workers=1,
                seed=exp,
            )
            res = det.run()
            solo_pvals.append(res.solo_pvalues[0])

        solo_arr = np.array(solo_pvals)
        _, ks_pval = stats.kstest(solo_arr, "uniform")
        assert ks_pval > 0.01

    def test_range_coverage(self):
        rng = np.random.default_rng(123)
        solo_pvals = []
        for exp in range(80):
            returns = rng.normal(0, 0.01, size=300)
            det = OverfitDetector(
                backtest_fn=backtest_noise,
                returns=returns,
                param_grid={"lookback": [5, 10, 20], "threshold": [0.0, 0.001]},
                n_reps=100,
                n_workers=1,
                seed=exp,
            )
            res = det.run()
            solo_pvals.append(res.solo_pvalues[0])

        solo_arr = np.array(solo_pvals)
        assert solo_arr.min() < 0.3 and solo_arr.max() > 0.7


class TestUnbiasedGeSolo:
    def test_unbiased_ge_solo_for_best(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.0005, 0.001]},
            n_reps=200,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        solo_best = res.solo_pvalues[res.best_param_index]
        assert res.unbiased_pvalue >= solo_best - 1e-10


class TestMonotonicity:
    def test_nondecreasing(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [5, 10, 20, 40, 60], "threshold": [0.0, 0.0005, 0.001, 0.002]},
            n_reps=300,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        diffs = np.diff(res.unbiased_pvalues)
        assert np.all(diffs >= -1e-12)

    def test_first_equals_reported(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [5, 10, 20, 40, 60], "threshold": [0.0, 0.0005, 0.001, 0.002]},
            n_reps=300,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert abs(res.unbiased_pvalues[0] - res.unbiased_pvalue) < 1e-12


class TestRunningBestVsBruteforce:
    def test_formula_match(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [5, 10, 20], "threshold": [0.0, 0.001]},
            n_reps=150,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        b = np.sum(res.null_best_sharpes >= res.best_sharpe)
        m = len(res.null_best_sharpes)
        expected = (b + 1) / (m + 1)
        assert abs(res.unbiased_pvalue - expected) < 1e-10


class TestUnbiasedMatchesProbOverfit:
    def test_close_for_large_n(self, noise_returns):
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=noise_returns,
            param_grid={"lookback": [5, 10, 20, 40], "threshold": [0.0, 0.0005, 0.001]},
            n_reps=500,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        assert abs(res.unbiased_pvalue - res.prob_overfit) < 0.01
