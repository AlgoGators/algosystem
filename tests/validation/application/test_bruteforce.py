"""Full cross-validation against brute-force reference implementation."""

import itertools

import numpy as np

from algosystem.validation import OverfitDetector
from algosystem.validation.domain import complete_shuffle
from tests.validation.conftest import backtest_noise


class TestBruteforceValidation:
    def test_full_crossvalidation(self):
        rng_data = np.random.default_rng(77)
        returns = rng_data.normal(0, 0.01, size=200)
        n_reps = 80
        param_grid = {"lookback": [5, 10, 20], "threshold": [0.0, 0.001]}

        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns,
            param_grid=param_grid,
            n_reps=n_reps,
            shuffle_method="complete",
            n_workers=1,
            seed=55,
        )
        res = det.run()

        # Brute-force: re-run all passes manually
        keys = sorted(param_grid.keys())
        values = [param_grid[k] for k in keys]
        plist = [dict(zip(keys, combo)) for combo in itertools.product(*values)]
        n_params = len(plist)

        master_rng = np.random.default_rng(55)
        pass_seeds = master_rng.integers(0, 2**63, size=1 + n_reps).tolist()

        all_sharpes = []
        for irep in range(1 + n_reps):
            prng = np.random.default_rng(pass_seeds[irep])
            if irep == 0:
                r = returns.copy()
            else:
                r = complete_shuffle(returns, prng)
            sharpes = np.array([backtest_noise(p, r) for p in plist])
            all_sharpes.append(sharpes)

        orig = all_sharpes[0]
        assert np.allclose(orig, res.original_sharpes, atol=1e-10)

        # Solo counts
        bf_solo_count = np.ones(n_params, dtype=np.int64)
        for irep in range(1, 1 + n_reps):
            perm = all_sharpes[irep]
            for i in range(n_params):
                if perm[i] >= orig[i]:
                    bf_solo_count[i] += 1
        bf_solo_pval = bf_solo_count / (1 + n_reps)
        assert np.allclose(bf_solo_pval, res.solo_pvalues, atol=1e-10)

        # Unbiased counts
        sort_idx = np.argsort(-orig)
        bf_unbiased_count = np.ones(n_params, dtype=np.int64)
        for irep in range(1, 1 + n_reps):
            perm = all_sharpes[irep]
            running_best = -np.inf
            for rank in range(n_params - 1, -1, -1):
                idx = sort_idx[rank]
                if perm[idx] > running_best:
                    running_best = perm[idx]
                if running_best >= orig[idx]:
                    bf_unbiased_count[idx] += 1

        bf_raw = bf_unbiased_count / (1 + n_reps)
        bf_ordered = np.empty(n_params)
        prior = 0.0
        for rank in range(n_params):
            idx = sort_idx[rank]
            pval = bf_raw[idx]
            if pval < prior:
                pval = prior
            bf_ordered[rank] = pval
            prior = pval

        assert np.allclose(bf_ordered, res.unbiased_pvalues, atol=1e-10)

        # Null best sharpes
        bf_null_best = np.array([np.max(all_sharpes[i]) for i in range(1, 1 + n_reps)])
        assert np.allclose(bf_null_best, res.null_best_sharpes, atol=1e-10)
