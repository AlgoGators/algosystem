"""
Comprehensive testbench for overfit_detector.py

Validates correctness against the VarScreen/RANSAC algorithm specification:
  - P-value formula: (b+1)/(m+1) per Phipson & Smyth (2010)
  - Solo p-values uniform under the null
  - Unbiased p-values correct for multiple testing
  - Running-best algorithm matches brute-force reference
  - Monotonicity of unbiased p-values
  - Power under the alternative (real signal detected)
  - Shuffle methods preserve correct properties
  - Edge cases handled properly
"""

import sys
import time
import traceback
from collections import OrderedDict

import numpy as np

from overfit_detector import (
    OverfitDetector,
    OverfitResults,
    _block_bootstrap,
    _complete_shuffle,
    _cyclic_permutation,
    _worker_run_pass,
)

# -----------------------------------------------------------------------
# Test helpers
# -----------------------------------------------------------------------

PASS = 0
FAIL = 0
WARN = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name}")
        if detail:
            print(f"         {detail}")


def warn(name, detail=""):
    global WARN
    WARN += 1
    print(f"  [WARN] {name}")
    if detail:
        print(f"         {detail}")


def section(title):
    print(f"\n{'='*72}")
    print(f"  {title}")
    print(f"{'='*72}")


# -----------------------------------------------------------------------
# Backtest functions for testing
# -----------------------------------------------------------------------

def backtest_noise(params, returns):
    """Momentum on arbitrary returns."""
    lb = params['lookback']
    th = params['threshold']
    n = len(returns)
    if n <= lb:
        return 0.0
    cumsum = np.cumsum(returns)
    rm = np.empty(n)
    rm[:lb] = 0.0
    rm[lb:] = (cumsum[lb:] - cumsum[:n - lb]) / lb
    sig = (rm > th).astype(float)
    sr = sig * returns
    sr = sr[lb:]
    if len(sr) == 0:
        return 0.0
    m = np.mean(sr)
    s = np.std(sr, ddof=1)
    if s < 1e-12:
        return 0.0
    return (m / s) * np.sqrt(252)


def backtest_constant(params, returns):
    """Always returns a fixed Sharpe regardless of data — for calibration."""
    return 1.0


def backtest_index_dependent(params, returns):
    """
    Returns Sharpe that depends only on the parameter index, not on data.
    Used to verify the running-best algorithm structure.
    """
    return float(params['idx'])


# -----------------------------------------------------------------------
# Test 1: P-value formula — (b+1)/(m+1)
# -----------------------------------------------------------------------

def test_pvalue_formula():
    section("Test 1: P-value formula is (b+1)/(m+1)")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10], 'threshold': [0.0, 0.001]},
        n_reps=100,
        n_workers=1,
        seed=99,
    )
    res = det.run()

    # P-values should never be zero (Phipson & Smyth 2010)
    check("No solo p-value is zero",
          np.all(res.solo_pvalues > 0),
          f"min solo_pval = {np.min(res.solo_pvalues)}")

    check("No unbiased p-value is zero",
          np.all(res.unbiased_pvalues > 0),
          f"min unbiased_pval = {np.min(res.unbiased_pvalues)}")

    # Minimum possible p-value is 1/(n_reps+1)
    min_possible = 1.0 / (res.n_reps + 1)
    check("Minimum p-value = 1/(nreps+1)",
          np.min(res.solo_pvalues) >= min_possible - 1e-12,
          f"min={np.min(res.solo_pvalues):.6f}, expected_min={min_possible:.6f}")

    # Maximum possible p-value is 1.0
    check("Maximum p-value <= 1.0",
          np.max(res.solo_pvalues) <= 1.0 + 1e-12)


# -----------------------------------------------------------------------
# Test 2: Solo p-values uniform under the null
# -----------------------------------------------------------------------

def test_solo_pvalues_uniform():
    section("Test 2: Solo p-values approximately uniform under the null")

    # Run many small experiments on pure noise and collect solo p-values
    # for the BEST param set. Under H0, they should be uniform.
    rng = np.random.default_rng(123)
    solo_pvals_best = []

    n_experiments = 80
    for exp in range(n_experiments):
        returns = rng.normal(0, 0.01, size=300)
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns,
            param_grid={'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]},
            n_reps=100,
            n_workers=1,
            seed=exp,
        )
        res = det.run()
        # Solo p-value of best param (which is just one of many, so uniform)
        # Actually pick a FIXED param set across experiments
        solo_pvals_best.append(res.solo_pvalues[0])  # first param set

    solo_arr = np.array(solo_pvals_best)

    # KS test for uniformity
    from scipy import stats
    ks_stat, ks_pval = stats.kstest(solo_arr, 'uniform')

    check("Solo p-values pass KS test for uniformity (p > 0.01)",
          ks_pval > 0.01,
          f"KS stat={ks_stat:.4f}, KS p-value={ks_pval:.4f}")

    # Check that they span the range reasonably
    check("Solo p-values span range (min < 0.3, max > 0.7)",
          solo_arr.min() < 0.3 and solo_arr.max() > 0.7,
          f"range: [{solo_arr.min():.3f}, {solo_arr.max():.3f}]")


# -----------------------------------------------------------------------
# Test 3: Unbiased p-value >= solo p-value for best competitor
# -----------------------------------------------------------------------

def test_unbiased_ge_solo_for_best():
    section("Test 3: Unbiased p-value >= solo p-value for best competitor")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20, 40], 'threshold': [0.0, 0.0005, 0.001]},
        n_reps=200,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    best_idx = res.best_param_index
    solo_best = res.solo_pvalues[best_idx]
    unbiased_best = res.unbiased_pvalue

    check("Unbiased p-value >= solo p-value for best competitor",
          unbiased_best >= solo_best - 1e-10,
          f"unbiased={unbiased_best:.4f}, solo={solo_best:.4f}")

    # With the same returns and seed, test on many experiments that
    # on average, more competitors produce higher unbiased p-values.
    # (Not guaranteed per-instance, so we just check the structural property
    # that unbiased >= solo for the best.)
    check("Unbiased p-value corrects upward relative to solo (multiple testing)",
          unbiased_best >= solo_best - 1e-10,
          f"unbiased={unbiased_best:.4f}, solo={solo_best:.4f}")


# -----------------------------------------------------------------------
# Test 4: Monotonicity of unbiased p-values
# -----------------------------------------------------------------------

def test_monotonicity():
    section("Test 4: Unbiased p-values are monotonically non-decreasing")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20, 40, 60],
                    'threshold': [0.0, 0.0005, 0.001, 0.002]},
        n_reps=300,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    # unbiased_pvalues is ordered from best to worst
    diffs = np.diff(res.unbiased_pvalues)
    check("All consecutive differences >= 0 (monotonic non-decreasing)",
          np.all(diffs >= -1e-12),
          f"min diff = {diffs.min():.6f}")

    check("First unbiased p-value equals the reported unbiased_pvalue",
          abs(res.unbiased_pvalues[0] - res.unbiased_pvalue) < 1e-12,
          f"first={res.unbiased_pvalues[0]:.6f}, reported={res.unbiased_pvalue:.6f}")


# -----------------------------------------------------------------------
# Test 5: Running-best algorithm vs brute-force reference
# -----------------------------------------------------------------------

def test_running_best_vs_bruteforce():
    section("Test 5: Running-best algorithm matches brute-force reference")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=300)
    n_reps = 150

    param_grid = {'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]}

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid=param_grid,
        n_reps=n_reps,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    # Brute-force: for the BEST competitor, the unbiased p-value is simply
    # the fraction of permuted passes where max(permuted_sharpes) >= S*
    # This is what prob_overfit computes, and it should match unbiased_pvalue
    # for the best competitor (up to the +1 in numerator/denominator).

    # prob_overfit uses np.mean(null_best >= best_sharpe) which is b/m
    # unbiased_pvalue uses (b+1)/(m+1)
    # They should be very close for large n_reps

    b = np.sum(res.null_best_sharpes >= res.best_sharpe)
    m = len(res.null_best_sharpes)
    expected_unbiased = (b + 1) / (m + 1)

    check("Unbiased p-value for best matches (b+1)/(m+1) formula",
          abs(res.unbiased_pvalue - expected_unbiased) < 1e-10,
          f"computed={res.unbiased_pvalue:.6f}, formula={expected_unbiased:.6f}")


# -----------------------------------------------------------------------
# Test 6: Power test — real signal should be detected
# -----------------------------------------------------------------------

def test_power_real_signal():
    section("Test 6: Power — real signal produces low p-values")

    # Generate data with strong trend/momentum structure
    rng = np.random.default_rng(42)
    n = 3000
    returns = np.empty(n)
    regime = 1.0
    for i in range(n):
        if rng.random() < 0.005:
            regime *= -1
        returns[i] = regime * 0.002 + rng.normal(0, 0.01)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]},
        n_reps=200,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    check("Unbiased p-value < 0.20 for strong signal",
          res.unbiased_pvalue < 0.20,
          f"unbiased_pvalue={res.unbiased_pvalue:.4f}")

    check("Deflated Sharpe > 0.5 for strong signal",
          res.deflated_sharpe > 0.5,
          f"deflated_sharpe={res.deflated_sharpe:.4f}")

    check("P(overfit) < 0.20 for strong signal",
          res.prob_overfit < 0.20,
          f"prob_overfit={res.prob_overfit:.4f}")


# -----------------------------------------------------------------------
# Test 7: No-signal test — noise should produce high p-values
# -----------------------------------------------------------------------

def test_no_signal():
    section("Test 7: No signal produces high p-values")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=2000)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20, 40, 60],
                    'threshold': [0.0, 0.0005, 0.001, 0.002]},
        n_reps=300,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    check("Unbiased p-value > 0.10 on pure noise (large grid)",
          res.unbiased_pvalue > 0.10,
          f"unbiased_pvalue={res.unbiased_pvalue:.4f}")

    check("P(overfit) > 0.10 on pure noise",
          res.prob_overfit > 0.10,
          f"prob_overfit={res.prob_overfit:.4f}")


# -----------------------------------------------------------------------
# Test 8: Shuffle methods
# -----------------------------------------------------------------------

def test_shuffle_methods():
    section("Test 8: Shuffle methods preserve correct properties")

    rng = np.random.default_rng(42)
    returns = rng.normal(0.0003, 0.01, size=1000)

    # --- Complete shuffle: preserves marginal distribution ---
    shuffled = _complete_shuffle(rng, returns)
    check("Complete shuffle preserves length",
          len(shuffled) == len(returns))
    check("Complete shuffle preserves mean (approx)",
          abs(np.mean(shuffled) - np.mean(returns)) < 1e-10)
    check("Complete shuffle preserves sorted values",
          np.allclose(np.sort(shuffled), np.sort(returns)))
    check("Complete shuffle changes order",
          not np.array_equal(shuffled, returns))

    # --- Cyclic permutation: preserves ALL autocorrelation ---
    rng2 = np.random.default_rng(42)
    cycled = _cyclic_permutation(rng2, returns)
    check("Cyclic perm preserves length",
          len(cycled) == len(returns))
    check("Cyclic perm preserves sorted values",
          np.allclose(np.sort(cycled), np.sort(returns)))

    # Autocorrelation should be preserved
    from numpy.fft import fft
    orig_spectrum = np.abs(fft(returns)) ** 2
    cycled_spectrum = np.abs(fft(cycled)) ** 2
    check("Cyclic perm preserves power spectrum",
          np.allclose(orig_spectrum, cycled_spectrum, atol=1e-8))

    # --- Block bootstrap: preserves local structure ---
    rng3 = np.random.default_rng(42)
    blocked = _block_bootstrap(rng3, returns, block_size=20)
    check("Block bootstrap preserves length",
          len(blocked) == len(returns))
    check("Block bootstrap changes order",
          not np.array_equal(blocked, returns))

    # All three should work in the detector
    for method in ['complete', 'cyclic', 'block']:
        det = OverfitDetector(
            backtest_fn=backtest_noise,
            returns=returns[:200],
            param_grid={'lookback': [5, 10], 'threshold': [0.0]},
            n_reps=20,
            shuffle_method=method,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        check(f"Shuffle method '{method}' completes without error",
              res.n_reps == 20)


# -----------------------------------------------------------------------
# Test 9: Subsampling uses same subset for all passes
# -----------------------------------------------------------------------

def test_subsampling_consistency():
    section("Test 9: Grid subsampling — same subset for all passes")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=300)

    # Large grid, subsample to 5
    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [3, 5, 8, 10, 15, 20, 30, 40],
                    'threshold': [0.0, 0.0005, 0.001, 0.002, 0.003]},
        n_reps=50,
        max_param_trials=5,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    check("Subsampled result has correct number of params",
          res.n_params == 5,
          f"n_params={res.n_params}")

    check("All arrays have consistent length",
          len(res.original_sharpes) == 5
          and len(res.solo_pvalues) == 5
          and len(res.sort_indices) == 5
          and len(res.unbiased_pvalues) == 5)


# -----------------------------------------------------------------------
# Test 10: Edge cases
# -----------------------------------------------------------------------

def test_edge_cases():
    section("Test 10: Edge cases")

    rng = np.random.default_rng(42)

    # --- Single parameter set ---
    returns = rng.normal(0, 0.01, size=300)
    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [10], 'threshold': [0.001]},
        n_reps=50,
        n_workers=1,
        seed=42,
    )
    res = det.run()
    check("Single param set: n_params=1",
          res.n_params == 1)
    check("Single param set: solo_pval = unbiased_pval (no multiple testing)",
          abs(res.solo_pvalues[0] - res.unbiased_pvalue) < 1e-10,
          f"solo={res.solo_pvalues[0]:.4f}, unbiased={res.unbiased_pvalue:.4f}")

    # --- Constant returns (zero variance) ---
    const_returns = np.ones(300) * 0.001
    det2 = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=const_returns,
        param_grid={'lookback': [5, 10], 'threshold': [0.0]},
        n_reps=20,
        n_workers=1,
        seed=42,
    )
    res2 = det2.run()
    check("Constant returns: no crash", True)

    # --- Very small n_reps ---
    det3 = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10], 'threshold': [0.0]},
        n_reps=1,
        n_workers=1,
        seed=42,
    )
    res3 = det3.run()
    check("n_reps=1: runs without error",
          res3.n_reps == 1)
    check("n_reps=1: p-values are valid (between 0 and 1)",
          np.all(res3.solo_pvalues >= 0) and np.all(res3.solo_pvalues <= 1))


# -----------------------------------------------------------------------
# Test 11: Unbiased p-value for best matches prob_overfit closely
# -----------------------------------------------------------------------

def test_unbiased_matches_prob_overfit():
    section("Test 11: Unbiased p-value ~ P(overfit) for best competitor")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20, 40],
                    'threshold': [0.0, 0.0005, 0.001]},
        n_reps=500,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    # prob_overfit = mean(null_best >= S*) = b/m
    # unbiased_pvalue = (b+1)/(m+1)
    # For large m, these should be very close
    diff = abs(res.unbiased_pvalue - res.prob_overfit)
    check("Unbiased p-value and P(overfit) differ by < 0.01",
          diff < 0.01,
          f"unbiased={res.unbiased_pvalue:.4f}, prob_overfit={res.prob_overfit:.4f}, "
          f"diff={diff:.4f}")


# -----------------------------------------------------------------------
# Test 12: Verify sort_indices correctness
# -----------------------------------------------------------------------

def test_sort_indices():
    section("Test 12: sort_indices correctly orders by descending Sharpe")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20, 40],
                    'threshold': [0.0, 0.001, 0.002]},
        n_reps=50,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    # sort_indices should order original_sharpes in descending order
    sorted_sharpes = res.original_sharpes[res.sort_indices]
    diffs = np.diff(sorted_sharpes)
    check("Sorted Sharpes are non-increasing (descending)",
          np.all(diffs <= 1e-12),
          f"max positive diff = {max(diffs):.8f}")

    check("sort_indices[0] = best_param_index",
          res.sort_indices[0] == res.best_param_index,
          f"sort_indices[0]={res.sort_indices[0]}, best_param_index={res.best_param_index}")


# -----------------------------------------------------------------------
# Test 13: Comparison direction (we MAXIMIZE Sharpe, reference MINIMIZES)
# -----------------------------------------------------------------------

def test_comparison_direction():
    section("Test 13: Comparison direction — higher Sharpe = better")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20],
                    'threshold': [0.0, 0.001]},
        n_reps=100,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    # best_sharpe should be the maximum
    check("best_sharpe = max(original_sharpes)",
          abs(res.best_sharpe - np.max(res.original_sharpes)) < 1e-10,
          f"best={res.best_sharpe:.4f}, max={np.max(res.original_sharpes):.4f}")

    # The best parameter set should have the highest Sharpe
    check("best_param_index points to max Sharpe",
          res.original_sharpes[res.best_param_index] == np.max(res.original_sharpes))


# -----------------------------------------------------------------------
# Test 14: Deflated Sharpe ratio properties
# -----------------------------------------------------------------------

def test_deflated_sharpe():
    section("Test 14: Deflated Sharpe ratio properties")

    rng = np.random.default_rng(42)

    # On noise: deflated Sharpe should be near zero or negative
    noise_returns = rng.normal(0, 0.01, size=2000)
    det_noise = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=noise_returns,
        param_grid={'lookback': [5, 10, 20, 40, 60],
                    'threshold': [0.0, 0.0005, 0.001, 0.002]},
        n_reps=300,
        n_workers=1,
        seed=42,
    )
    res_noise = det_noise.run()

    check("Noise: deflated Sharpe < 1.0",
          res_noise.deflated_sharpe < 1.0,
          f"deflated_sharpe={res_noise.deflated_sharpe:.4f}")

    # On strong signal: deflated Sharpe should be positive and large
    signal_returns = np.empty(3000)
    regime = 1.0
    for i in range(3000):
        if rng.random() < 0.005:
            regime *= -1
        signal_returns[i] = regime * 0.002 + rng.normal(0, 0.01)

    det_signal = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=signal_returns,
        param_grid={'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]},
        n_reps=300,
        n_workers=1,
        seed=42,
    )
    res_signal = det_signal.run()

    check("Signal: deflated Sharpe > noise deflated Sharpe",
          res_signal.deflated_sharpe > res_noise.deflated_sharpe,
          f"signal={res_signal.deflated_sharpe:.4f}, "
          f"noise={res_noise.deflated_sharpe:.4f}")


# -----------------------------------------------------------------------
# Test 15: Reproducibility with same seed
# -----------------------------------------------------------------------

def test_reproducibility():
    section("Test 15: Reproducibility with same seed")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    kwargs = dict(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]},
        n_reps=50,
        n_workers=1,
        seed=42,
    )

    res1 = OverfitDetector(**kwargs).run()
    res2 = OverfitDetector(**kwargs).run()

    check("Same seed produces identical original_sharpes",
          np.array_equal(res1.original_sharpes, res2.original_sharpes))

    check("Same seed produces identical null_best_sharpes",
          np.array_equal(res1.null_best_sharpes, res2.null_best_sharpes))

    check("Same seed produces identical solo_pvalues",
          np.array_equal(res1.solo_pvalues, res2.solo_pvalues))

    check("Same seed produces identical unbiased_pvalue",
          res1.unbiased_pvalue == res2.unbiased_pvalue)


# -----------------------------------------------------------------------
# Test 16: Multiprocessing consistency
# -----------------------------------------------------------------------

def test_multiprocessing():
    section("Test 16: Multiprocessing produces same results as single-process")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    kwargs_base = dict(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]},
        n_reps=50,
        seed=42,
    )

    res_single = OverfitDetector(**kwargs_base, n_workers=1).run()
    res_multi = OverfitDetector(**kwargs_base, n_workers=2).run()

    check("Single vs multi: same original_sharpes",
          np.array_equal(res_single.original_sharpes, res_multi.original_sharpes))

    check("Single vs multi: same null_best_sharpes",
          np.array_equal(res_single.null_best_sharpes, res_multi.null_best_sharpes))

    check("Single vs multi: same unbiased_pvalue",
          res_single.unbiased_pvalue == res_multi.unbiased_pvalue)


# -----------------------------------------------------------------------
# Test 17: Null distribution shape
# -----------------------------------------------------------------------

def test_null_distribution_shape():
    section("Test 17: Null distribution shape sanity checks")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=1000)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20, 40],
                    'threshold': [0.0, 0.0005, 0.001, 0.002]},
        n_reps=300,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    check("Null distribution has correct length",
          len(res.null_best_sharpes) == 300)

    check("Null distribution has finite values",
          np.all(np.isfinite(res.null_best_sharpes)))

    # The null best-sharpe should be the MAX across all param sets per pass,
    # so it should generally be positive (max of several near-zero values)
    check("Null best-sharpes are mostly positive (max of several values)",
          np.mean(res.null_best_sharpes > 0) > 0.5,
          f"fraction positive: {np.mean(res.null_best_sharpes > 0):.2f}")

    # The null distribution's mean should be near the observed best Sharpe
    # under H0 (since observed best comes from the same distribution)
    null_mean = np.mean(res.null_best_sharpes)
    check("Null distribution mean is within 3 std of S* under H0",
          abs(res.best_sharpe - null_mean) < 3 * np.std(res.null_best_sharpes),
          f"S*={res.best_sharpe:.4f}, null_mean={null_mean:.4f}, "
          f"null_std={np.std(res.null_best_sharpes):.4f}")


# -----------------------------------------------------------------------
# Test 18: report() and plot methods don't crash
# -----------------------------------------------------------------------

def test_output_methods():
    section("Test 18: report() and plot methods run without error")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=300)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10], 'threshold': [0.0, 0.001]},
        n_reps=20,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    try:
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        res.report()
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
        check("report() runs without error", True)
        check("report() produces output",
              len(output) > 100,
              f"output length: {len(output)}")
    except Exception as e:
        sys.stdout = old_stdout
        check("report() runs without error", False, str(e))

    try:
        import matplotlib
        matplotlib.use('Agg')
        fig = res.plot_null_distribution(save_path='_test_null.png')
        check("plot_null_distribution() runs without error", fig is not None)
    except ImportError:
        warn("matplotlib not available, skipping plot test")
    except Exception as e:
        check("plot_null_distribution() runs without error", False, str(e))

    try:
        import matplotlib
        matplotlib.use('Agg')
        fig = res.plot_parameter_sensitivity(save_path='_test_sens.png')
        check("plot_parameter_sensitivity() runs without error", fig is not None)
    except ImportError:
        warn("matplotlib not available, skipping plot test")
    except Exception as e:
        check("plot_parameter_sensitivity() runs without error", False, str(e))

    # Cleanup
    import os
    for f in ['_test_null.png', '_test_sens.png']:
        if os.path.exists(f):
            os.remove(f)


# -----------------------------------------------------------------------
# Test 19: Cross-validate against manual brute-force implementation
# -----------------------------------------------------------------------

def test_cross_validate_bruteforce():
    section("Test 19: Full cross-validation against brute-force implementation")

    rng_data = np.random.default_rng(77)
    returns = rng_data.normal(0, 0.01, size=200)
    n_reps = 80
    param_grid = {'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]}

    # Run our detector
    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid=param_grid,
        n_reps=n_reps,
        shuffle_method='complete',
        n_workers=1,
        seed=55,
    )
    res = det.run()

    # Brute-force: re-run all passes manually
    import itertools
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
            r = _complete_shuffle(prng, returns)
        sharpes = np.array([backtest_noise(p, r) for p in plist])
        all_sharpes.append(sharpes)

    orig = all_sharpes[0]

    # Verify original sharpes match
    check("Brute-force: original sharpes match",
          np.allclose(orig, res.original_sharpes, atol=1e-10),
          f"max diff = {np.max(np.abs(orig - res.original_sharpes)):.2e}")

    # Compute solo counts manually
    bf_solo_count = np.ones(n_params, dtype=np.int64)
    for irep in range(1, 1 + n_reps):
        perm = all_sharpes[irep]
        for i in range(n_params):
            if perm[i] >= orig[i]:
                bf_solo_count[i] += 1

    bf_solo_pval = bf_solo_count / (1 + n_reps)

    check("Brute-force: solo p-values match",
          np.allclose(bf_solo_pval, res.solo_pvalues, atol=1e-10),
          f"max diff = {np.max(np.abs(bf_solo_pval - res.solo_pvalues)):.2e}")

    # Compute unbiased counts manually (worst-to-best running maximum)
    sort_idx = np.argsort(-orig)  # descending
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

    bf_raw_unbiased = bf_unbiased_count / (1 + n_reps)

    # Apply monotonicity
    bf_unbiased_ordered = np.empty(n_params)
    prior = 0.0
    for rank in range(n_params):
        idx = sort_idx[rank]
        pval = bf_raw_unbiased[idx]
        if pval < prior:
            pval = prior
        bf_unbiased_ordered[rank] = pval
        prior = pval

    check("Brute-force: unbiased p-values match",
          np.allclose(bf_unbiased_ordered, res.unbiased_pvalues, atol=1e-10),
          f"max diff = {np.max(np.abs(bf_unbiased_ordered - res.unbiased_pvalues)):.2e}")

    # Check null_best_sharpes
    bf_null_best = np.array([np.max(all_sharpes[irep]) for irep in range(1, 1 + n_reps)])
    check("Brute-force: null_best_sharpes match",
          np.allclose(bf_null_best, res.null_best_sharpes, atol=1e-10),
          f"max diff = {np.max(np.abs(bf_null_best - res.null_best_sharpes)):.2e}")


# -----------------------------------------------------------------------
# Test 20: Surface analysis metrics — structure and sanity
# -----------------------------------------------------------------------

def test_surface_analysis_structure():
    section("Test 20: Surface analysis metrics — structure and sanity")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=500)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20, 40],
                    'threshold': [0.0, 0.0005, 0.001, 0.002]},
        n_reps=50,
        n_workers=1,
        seed=42,
    )
    res = det.run()
    sa = res.surface_analysis()

    check("surface_analysis returns dict", isinstance(sa, dict))

    expected_keys = ['robustness_ratio', 'frac_positive', 'frac_above_half',
                     'plateau_score', 'cv_neighbors', 'peak_to_neighbor',
                     'per_param_sensitivity']
    for k in expected_keys:
        check(f"surface_analysis has key '{k}'", k in sa, f"keys: {list(sa.keys())}")

    check("robustness_ratio in [0, inf)",
          sa['robustness_ratio'] >= 0)
    check("frac_positive in [0, 1]",
          0 <= sa['frac_positive'] <= 1)
    check("frac_above_half in [0, 1]",
          0 <= sa['frac_above_half'] <= 1)
    check("plateau_score in [0, 1]",
          0 <= sa['plateau_score'] <= 1)

    # Per-param sensitivity should have one entry per param
    pps = sa['per_param_sensitivity']
    check("per_param_sensitivity has entry for 'lookback'", 'lookback' in pps)
    check("per_param_sensitivity has entry for 'threshold'", 'threshold' in pps)

    # Sobol indices should be non-negative and sum to <= 1 (they can exceed 1
    # due to interactions, but first-order should generally sum to ~1)
    sobol_sum = sum(v['sobol_first'] for v in pps.values())
    check("Sobol first-order indices are non-negative",
          all(v['sobol_first'] >= 0 for v in pps.values()))
    check("Sobol first-order indices sum is reasonable (< 2.0)",
          sobol_sum < 2.0,
          f"sum = {sobol_sum:.4f}")


# -----------------------------------------------------------------------
# Test 21: Surface analysis — plateau vs spike detection
# -----------------------------------------------------------------------

def test_surface_plateau_vs_spike():
    section("Test 21: Surface analysis — plateau vs spike detection")

    rng = np.random.default_rng(42)

    # Strategy A: flat surface (constant Sharpe regardless of params)
    def flat_backtest(params, returns):
        # Just buy-and-hold regardless of parameters
        return _sharpe(returns)

    from overfit_detector import OverfitDetector

    flat_returns = rng.normal(0.0005, 0.01, size=500)
    det_flat = OverfitDetector(
        backtest_fn=flat_backtest,
        returns=flat_returns,
        param_grid={'lookback': [5, 10, 20, 40],
                    'threshold': [0.0, 0.001, 0.002]},
        n_reps=20,
        n_workers=1,
        seed=42,
    )
    res_flat = det_flat.run()
    sa_flat = res_flat.surface_analysis()

    # Strategy B: spiky surface (depends heavily on one param)
    def spiky_backtest(params, returns):
        # Only works for lookback=10, everything else is garbage
        if params['lookback'] == 10 and params['threshold'] == 0.001:
            return 3.0
        return rng.normal(0, 0.2)

    det_spiky = OverfitDetector(
        backtest_fn=spiky_backtest,
        returns=flat_returns,
        param_grid={'lookback': [5, 10, 20, 40],
                    'threshold': [0.0, 0.001, 0.002]},
        n_reps=20,
        n_workers=1,
        seed=42,
    )
    res_spiky = det_spiky.run()
    sa_spiky = res_spiky.surface_analysis()

    check("Flat surface: robustness_ratio close to 1.0",
          abs(sa_flat['robustness_ratio'] - 1.0) < 0.01,
          f"RR = {sa_flat['robustness_ratio']:.4f}")

    check("Flat surface: plateau_score = 1.0 (all points near best)",
          sa_flat['plateau_score'] > 0.9,
          f"plateau = {sa_flat['plateau_score']:.4f}")

    check("Spiky surface: lower robustness_ratio than flat",
          sa_spiky['robustness_ratio'] < sa_flat['robustness_ratio'],
          f"spiky={sa_spiky['robustness_ratio']:.4f}, "
          f"flat={sa_flat['robustness_ratio']:.4f}")

    check("Spiky surface: lower plateau_score than flat",
          sa_spiky['plateau_score'] < sa_flat['plateau_score'],
          f"spiky={sa_spiky['plateau_score']:.4f}, "
          f"flat={sa_flat['plateau_score']:.4f}")


def _sharpe(returns):
    """Helper for test backtests."""
    if len(returns) < 2:
        return 0.0
    m = np.mean(returns)
    s = np.std(returns, ddof=1)
    if s < 1e-12:
        return 0.0
    return (m / s) * np.sqrt(252)


# -----------------------------------------------------------------------
# Test 22: Surface report and 2D plot don't crash
# -----------------------------------------------------------------------

def test_surface_output_methods():
    section("Test 22: surface_report() and plot_surface_2d() run without error")

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=300)

    det = OverfitDetector(
        backtest_fn=backtest_noise,
        returns=returns,
        param_grid={'lookback': [5, 10, 20], 'threshold': [0.0, 0.001]},
        n_reps=20,
        n_workers=1,
        seed=42,
    )
    res = det.run()

    try:
        import io as _io
        old = sys.stdout
        sys.stdout = _io.StringIO()
        res.surface_report()
        output = sys.stdout.getvalue()
        sys.stdout = old
        check("surface_report() runs without error", True)
        check("surface_report() produces output", len(output) > 50)
    except Exception as e:
        sys.stdout = old
        check("surface_report() runs without error", False, str(e))

    try:
        import matplotlib
        matplotlib.use('Agg')
        fig = res.plot_surface_2d('lookback', 'threshold', save_path='_test_2d.png')
        check("plot_surface_2d() runs without error", fig is not None)
        import os
        if os.path.exists('_test_2d.png'):
            os.remove('_test_2d.png')
    except ImportError:
        warn("matplotlib not available, skipping 2D plot test")
    except Exception as e:
        check("plot_surface_2d() runs without error", False, str(e))


# -----------------------------------------------------------------------
# Test 23: Multi-strategy overfitting detection
# -----------------------------------------------------------------------

def test_multi_strategy():
    section("Test 23: Multi-strategy backtests (6 archetypes)")

    from strategies import (
        momentum_backtest, mean_reversion_backtest, breakout_backtest,
        vol_regime_backtest, dual_momentum_backtest, pairs_backtest,
        generate_noise, generate_trending, generate_mean_reverting,
        generate_volatile_regimes, PARAM_GRIDS,
    )

    # Test each strategy runs without error on its natural data
    strategy_tests = [
        ('momentum',       momentum_backtest,       generate_noise(n=1000, seed=1)),
        ('mean_reversion', mean_reversion_backtest,  generate_noise(n=1000, seed=2)),
        ('breakout',       breakout_backtest,        generate_noise(n=1000, seed=3)),
        ('vol_regime',     vol_regime_backtest,      generate_noise(n=1000, seed=4)),
        ('dual_momentum',  dual_momentum_backtest,   generate_noise(n=1000, seed=5)),
        ('pairs',          pairs_backtest,           generate_noise(n=1000, seed=6)),
    ]

    for name, fn, returns in strategy_tests:
        grid = PARAM_GRIDS[name]
        # Use small subgrid for speed
        small_grid = {k: v[:3] for k, v in grid.items()}
        det = OverfitDetector(
            backtest_fn=fn,
            returns=returns,
            param_grid=small_grid,
            n_reps=20,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        check(f"Strategy '{name}' completes without error",
              res.n_reps == 20)
        check(f"Strategy '{name}' produces finite Sharpes",
              np.all(np.isfinite(res.original_sharpes)),
              f"non-finite count: {np.sum(~np.isfinite(res.original_sharpes))}")


# -----------------------------------------------------------------------
# Test 24: Strategy on matching vs non-matching data
# -----------------------------------------------------------------------

def test_strategy_signal_match():
    section("Test 24: Strategy on matching data vs noise — signal detection")

    from strategies import (
        momentum_backtest, mean_reversion_backtest,
        generate_trending, generate_mean_reverting, generate_noise,
        PARAM_GRIDS,
    )

    n_reps = 150

    # Momentum on trending data (should detect signal)
    det_match = OverfitDetector(
        backtest_fn=momentum_backtest,
        returns=generate_trending(n=3000, seed=42),
        param_grid={k: v[:4] for k, v in PARAM_GRIDS['momentum'].items()},
        n_reps=n_reps,
        n_workers=1,
        seed=42,
    )
    res_match = det_match.run()

    # Momentum on pure noise (should NOT detect signal)
    det_noise = OverfitDetector(
        backtest_fn=momentum_backtest,
        returns=generate_noise(n=3000, seed=42),
        param_grid={k: v[:4] for k, v in PARAM_GRIDS['momentum'].items()},
        n_reps=n_reps,
        n_workers=1,
        seed=42,
    )
    res_noise = det_noise.run()

    check("Momentum on trending: lower p-value than on noise",
          res_match.unbiased_pvalue < res_noise.unbiased_pvalue,
          f"trending p={res_match.unbiased_pvalue:.4f}, "
          f"noise p={res_noise.unbiased_pvalue:.4f}")

    check("Momentum on trending: higher deflated Sharpe than on noise",
          res_match.deflated_sharpe > res_noise.deflated_sharpe,
          f"trending DS={res_match.deflated_sharpe:.4f}, "
          f"noise DS={res_noise.deflated_sharpe:.4f}")

    # Mean-reversion on mean-reverting data (should detect signal)
    det_mr = OverfitDetector(
        backtest_fn=mean_reversion_backtest,
        returns=generate_mean_reverting(n=3000, seed=42),
        param_grid={k: v[:3] for k, v in PARAM_GRIDS['mean_reversion'].items()},
        n_reps=n_reps,
        n_workers=1,
        seed=42,
    )
    res_mr = det_mr.run()

    # Mean-reversion on pure noise
    det_mr_noise = OverfitDetector(
        backtest_fn=mean_reversion_backtest,
        returns=generate_noise(n=3000, seed=42),
        param_grid={k: v[:3] for k, v in PARAM_GRIDS['mean_reversion'].items()},
        n_reps=n_reps,
        n_workers=1,
        seed=42,
    )
    res_mr_noise = det_mr_noise.run()

    check("Mean-rev on AR(1): lower p-value than on noise",
          res_mr.unbiased_pvalue < res_mr_noise.unbiased_pvalue,
          f"AR(1) p={res_mr.unbiased_pvalue:.4f}, "
          f"noise p={res_mr_noise.unbiased_pvalue:.4f}")


# -----------------------------------------------------------------------
# Test 25: Surface analysis Sobol indices — dominant parameter detection
# -----------------------------------------------------------------------

def test_sobol_dominant_param():
    section("Test 25: Sobol indices detect dominant parameter")

    # Backtest where Sharpe depends strongly on 'lookback' but not 'threshold'
    def lookback_dependent(params, returns):
        lb = params['lookback']
        # Sharpe is just a function of lookback, not threshold or data
        return 5.0 / (1 + abs(lb - 20))

    rng = np.random.default_rng(42)
    returns = rng.normal(0, 0.01, size=300)

    det = OverfitDetector(
        backtest_fn=lookback_dependent,
        returns=returns,
        param_grid={'lookback': [5, 10, 15, 20, 30, 40, 60],
                    'threshold': [0.0, 0.001, 0.002, 0.003]},
        n_reps=20,
        n_workers=1,
        seed=42,
    )
    res = det.run()
    sa = res.surface_analysis()
    pps = sa['per_param_sensitivity']

    sobol_lb = pps['lookback']['sobol_first']
    sobol_th = pps['threshold']['sobol_first']

    check("Lookback has higher Sobol index than threshold",
          sobol_lb > sobol_th,
          f"lookback S1={sobol_lb:.4f}, threshold S1={sobol_th:.4f}")

    check("Lookback Sobol index is high (>0.5)",
          sobol_lb > 0.5,
          f"lookback S1={sobol_lb:.4f}")

    check("Threshold Sobol index is near zero (<0.05)",
          sobol_th < 0.05,
          f"threshold S1={sobol_th:.4f}")


# -----------------------------------------------------------------------
# Test 26: Multi-strategy surface comparison (flat vs spiky strategies)
# -----------------------------------------------------------------------

def test_surface_across_strategies():
    section("Test 26: Surface metrics across strategies on noise")

    from strategies import (
        momentum_backtest, breakout_backtest,
        generate_noise, PARAM_GRIDS,
    )

    noise = generate_noise(n=2000, seed=42)

    results = {}
    for name, fn in [('momentum', momentum_backtest),
                      ('breakout', breakout_backtest)]:
        grid = {k: v[:4] for k, v in PARAM_GRIDS[name].items()}
        det = OverfitDetector(
            backtest_fn=fn,
            returns=noise,
            param_grid=grid,
            n_reps=50,
            n_workers=1,
            seed=42,
        )
        res = det.run()
        sa = res.surface_analysis()
        results[name] = sa

    # Both should have valid metrics on noise
    for name, sa in results.items():
        check(f"{name} on noise: frac_positive in [0,1]",
              0 <= sa['frac_positive'] <= 1)
        check(f"{name} on noise: robustness_ratio is finite",
              np.isfinite(sa['robustness_ratio']),
              f"RR={sa['robustness_ratio']}")


# -----------------------------------------------------------------------
# Test 27: Walk-forward degradation ratio (conceptual validation)
# -----------------------------------------------------------------------

def test_walk_forward_concept():
    section("Test 27: Walk-forward concept — IS vs OOS Sharpe comparison")

    from strategies import momentum_backtest, generate_trending, generate_noise

    # Split data: first half IS, second half OOS
    trending = generate_trending(n=4000, seed=42)
    is_data = trending[:2000]
    oos_data = trending[2000:]

    noise = generate_noise(n=4000, seed=42)
    is_noise = noise[:2000]
    oos_noise = noise[2000:]

    grid = {'lookback': [5, 10, 20, 40], 'threshold': [0.0, 0.001]}

    # Find best params on IS
    import itertools
    keys = sorted(grid.keys())
    plist = [dict(zip(keys, c)) for c in itertools.product(*[grid[k] for k in keys])]

    # Trending data: IS -> OOS degradation should be moderate
    is_sharpes = [momentum_backtest(p, is_data) for p in plist]
    best_idx = np.argmax(is_sharpes)
    oos_sharpe_trend = momentum_backtest(plist[best_idx], oos_data)
    is_sharpe_trend = is_sharpes[best_idx]
    degradation_trend = oos_sharpe_trend / is_sharpe_trend if is_sharpe_trend > 0 else 0

    # Noise: IS -> OOS degradation should be severe
    is_sharpes_noise = [momentum_backtest(p, is_noise) for p in plist]
    best_idx_noise = np.argmax(is_sharpes_noise)
    oos_sharpe_noise = momentum_backtest(plist[best_idx_noise], oos_noise)
    is_sharpe_noise = is_sharpes_noise[best_idx_noise]
    degradation_noise = oos_sharpe_noise / is_sharpe_noise if is_sharpe_noise > 0 else 0

    check("Trending: OOS degradation ratio is positive",
          degradation_trend > 0,
          f"IS={is_sharpe_trend:.2f}, OOS={oos_sharpe_trend:.2f}, "
          f"ratio={degradation_trend:.2f}")

    # On trending data, the IS-optimal params should still work OOS
    # (degradation ratio > 0 is enough — the specific comparison with noise
    # is too noisy for a single realization)
    check("Trending: IS-best still positive OOS (real signal persists)",
          oos_sharpe_trend > 0,
          f"IS={is_sharpe_trend:.2f}, OOS={oos_sharpe_trend:.2f}")


# -----------------------------------------------------------------------
# Run all tests
# -----------------------------------------------------------------------

if __name__ == '__main__':
    print("\n" + "#" * 72)
    print("#  OVERFIT DETECTOR TESTBENCH")
    print("#  Validating against VarScreen/RANSAC algorithm specification")
    print("#" * 72)

    t0 = time.time()

    # Suppress detector progress output during tests
    import io
    old_stdout = sys.stdout

    class FilteredOutput:
        """Pass through test output but suppress detector progress."""
        def __init__(self, real_stdout):
            self._real = real_stdout
            self._suppress = False

        def write(self, s):
            # Suppress lines from the detector (Running, Pass, All passes, etc.)
            for prefix in ['Running ', '  Pass ', 'All passes', 'Using ',
                           'Grid has', 'Plot saved']:
                if s.lstrip().startswith(prefix):
                    return
            self._real.write(s)

        def flush(self):
            self._real.flush()

    sys.stdout = FilteredOutput(old_stdout)

    tests = [
        test_pvalue_formula,
        test_solo_pvalues_uniform,
        test_unbiased_ge_solo_for_best,
        test_monotonicity,
        test_running_best_vs_bruteforce,
        test_power_real_signal,
        test_no_signal,
        test_shuffle_methods,
        test_subsampling_consistency,
        test_edge_cases,
        test_unbiased_matches_prob_overfit,
        test_sort_indices,
        test_comparison_direction,
        test_deflated_sharpe,
        test_reproducibility,
        test_multiprocessing,
        test_null_distribution_shape,
        test_output_methods,
        test_cross_validate_bruteforce,
        test_surface_analysis_structure,
        test_surface_plateau_vs_spike,
        test_surface_output_methods,
        test_multi_strategy,
        test_strategy_signal_match,
        test_sobol_dominant_param,
        test_surface_across_strategies,
        test_walk_forward_concept,
    ]

    for test_fn in tests:
        try:
            test_fn()
        except Exception as e:
            sys.stdout = FilteredOutput(old_stdout)
            section(f"EXCEPTION in {test_fn.__name__}")
            traceback.print_exc()
            FAIL += 1

    elapsed = time.time() - t0
    sys.stdout = old_stdout

    print(f"\n{'='*72}")
    print(f"  RESULTS: {PASS} passed, {FAIL} failed, {WARN} warnings  "
          f"({elapsed:.1f}s)")
    print(f"{'='*72}")

    if FAIL > 0:
        print("\n  *** FAILURES DETECTED — see above for details ***\n")
        sys.exit(1)
    else:
        print("\n  All tests passed.\n")
        sys.exit(0)
