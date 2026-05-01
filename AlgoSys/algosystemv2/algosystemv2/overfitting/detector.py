"""
Permutation-based overfitting detector for trading strategy backtests.

Inspired by the RANSAC/VarScreen approach to unbiased p-values (Timothy Masters).
Detects whether an optimized strategy's performance could have been achieved
by overfitting to noise, correcting for the multiple-testing problem inherent
in searching over many parameter combinations.

Usage:
    from algosystemv2.overfitting import OverfitDetector

    def my_backtest(params, returns):
        # your backtest logic
        return sharpe_ratio

    detector = OverfitDetector(
        backtest_fn=my_backtest,
        returns=my_returns_series,
        param_grid={'lookback': [10, 20, 50], 'threshold': [0.5, 1.0, 1.5]},
    )
    results = detector.run()
    results.report()
"""

from __future__ import annotations

import itertools
import multiprocessing as mp
import os
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from .results import OverfitResults
from .worker import worker_run_pass


class OverfitDetector:
    """
    Permutation-based overfitting detector for strategy backtests.

    Parameters
    ----------
    backtest_fn : callable
        Function with signature (params_dict, returns_array) -> float (Sharpe ratio).
        Must be picklable for multiprocessing (i.e., a module-level function,
        not a lambda or closure).
    returns : array-like
        Historical returns series (1-D).
    param_grid : dict
        Maps parameter names to lists of values to search over.
        All combinations are tested (Cartesian product).
    n_reps : int
        Number of Monte Carlo permutation replications (default 1000).
        Pass 0 is unpermuted; passes 1..n_reps are permuted.
    shuffle_method : str
        One of 'complete', 'cyclic', 'block'.
    block_size : int or None
        Block size for block bootstrap. Defaults to sqrt(n) if None.
    max_param_trials : int or None
        If set and the total grid is larger, randomly subsample this many
        parameter combinations per pass (same subset for every pass).
    n_workers : int or None
        Number of parallel workers. Defaults to all available cores.
    seed : int
        Master random seed for reproducibility.
    """

    def __init__(
        self,
        backtest_fn: Callable,
        returns: np.ndarray | Sequence[float],
        param_grid: Dict[str, List[Any]],
        n_reps: int = 1000,
        shuffle_method: str = 'complete',
        block_size: int | None = None,
        max_param_trials: int | None = None,
        n_workers: int | None = None,
        seed: int = 42,
    ):
        self.backtest_fn = backtest_fn
        self.returns = np.asarray(returns, dtype=np.float64)
        self.param_grid = param_grid
        self.n_reps = n_reps
        self.shuffle_method = shuffle_method
        self.block_size = block_size
        self.max_param_trials = max_param_trials
        self.n_workers = n_workers or os.cpu_count() or 1
        self.seed = seed

        keys = sorted(param_grid.keys())
        values = [param_grid[k] for k in keys]
        self._param_list = [
            dict(zip(keys, combo))
            for combo in itertools.product(*values)
        ]
        self._keys = keys

    @property
    def param_list(self) -> list:
        return self._param_list

    def run(self) -> OverfitResults:
        """Execute the full permutation test and return results."""
        # Pre-test diagnostic: check for autocorrelation
        from .diagnostics import check_autocorrelation
        ac = check_autocorrelation(self.returns)
        if ac.warning_message and self.shuffle_method == 'complete':
            print(ac.warning_message)

        rng = np.random.default_rng(self.seed)
        n_params_full = len(self._param_list)

        # Handle subsampling if grid is too large
        subsample_indices = None
        if self.max_param_trials is not None and n_params_full > self.max_param_trials:
            subsample_indices = rng.choice(
                n_params_full, size=self.max_param_trials, replace=False
            )
            subsample_indices.sort()
            effective_param_list = [self._param_list[i] for i in subsample_indices]
            print(f"Grid has {n_params_full} combinations; subsampling to "
                  f"{self.max_param_trials} per pass.")
        else:
            effective_param_list = self._param_list

        n_params = len(effective_param_list)
        total_passes = 1 + self.n_reps

        print(f"Running {total_passes} passes x {n_params} parameter sets "
              f"= {total_passes * n_params:,} backtests")
        print(f"Using {self.n_workers} worker(s), shuffle={self.shuffle_method}")

        pass_seeds = rng.integers(0, 2**63, size=total_passes).tolist()

        work_items = [
            (irep, self.returns, effective_param_list, self.backtest_fn,
             self.shuffle_method, self.block_size, pass_seeds[irep], None)
            for irep in range(total_passes)
        ]

        t0 = time.time()
        all_sharpes = [None] * total_passes

        if self.n_workers == 1:
            for item in work_items:
                irep, sharpes = worker_run_pass(item)
                all_sharpes[irep] = sharpes
                if irep == 0:
                    elapsed = time.time() - t0
                    print(f"  Pass 0 (unpermuted) done in {elapsed:.1f}s")
                elif irep % max(1, self.n_reps // 10) == 0:
                    elapsed = time.time() - t0
                    rate = irep / elapsed if elapsed > 0 else 0
                    eta = (self.n_reps - irep) / rate if rate > 0 else 0
                    print(f"  Pass {irep}/{self.n_reps} "
                          f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")
        else:
            completed = 0
            with mp.Pool(processes=self.n_workers) as pool:
                for irep, sharpes in pool.imap_unordered(worker_run_pass, work_items):
                    all_sharpes[irep] = sharpes
                    completed += 1
                    if irep == 0:
                        elapsed = time.time() - t0
                        print(f"  Pass 0 (unpermuted) done in {elapsed:.1f}s")
                    elif completed % max(1, self.n_reps // 10) == 0:
                        elapsed = time.time() - t0
                        rate = completed / elapsed if elapsed > 0 else 0
                        eta = (total_passes - completed) / rate if rate > 0 else 0
                        print(f"  {completed}/{total_passes} passes done "
                              f"({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

        elapsed = time.time() - t0
        print(f"All passes complete in {elapsed:.1f}s")

        return self._compute_results(
            all_sharpes, effective_param_list, n_params, subsample_indices
        )

    def _compute_results(
        self,
        all_sharpes: list,
        effective_param_list: list,
        n_params: int,
        subsample_indices,
    ) -> OverfitResults:
        """Compute p-values using the RANSAC/VarScreen algorithm."""
        total_passes = 1 + self.n_reps
        original_sharpes = all_sharpes[0]

        sort_indices = np.argsort(-original_sharpes)

        # Initialize counts (start at 1 — Phipson & Smyth 2010)
        solo_count = np.ones(n_params, dtype=np.int64)
        unbiased_count = np.ones(n_params, dtype=np.int64)
        null_best_sharpes = np.empty(self.n_reps, dtype=np.float64)

        for irep in range(1, total_passes):
            perm_sharpes = all_sharpes[irep]

            for i in range(n_params):
                if perm_sharpes[i] >= original_sharpes[i]:
                    solo_count[i] += 1

            # Unbiased count: worst-to-best running maximum
            running_best = -np.inf
            for rank in range(n_params - 1, -1, -1):
                idx = sort_indices[rank]
                if perm_sharpes[idx] > running_best:
                    running_best = perm_sharpes[idx]
                if running_best >= original_sharpes[idx]:
                    unbiased_count[idx] += 1

            null_best_sharpes[irep - 1] = np.max(perm_sharpes)

        total_obs = 1 + self.n_reps
        solo_pvalues = solo_count / total_obs

        # Unbiased p-values with monotonicity enforcement
        raw_unbiased = unbiased_count / total_obs
        unbiased_pvalues_ordered = np.empty(n_params, dtype=np.float64)
        prior = 0.0
        for rank in range(n_params):
            idx = sort_indices[rank]
            pval = raw_unbiased[idx]
            if pval < prior:
                pval = prior
            unbiased_pvalues_ordered[rank] = pval
            prior = pval

        best_idx = sort_indices[0]
        best_sharpe = original_sharpes[best_idx]
        unbiased_pvalue = unbiased_pvalues_ordered[0]

        prob_overfit = np.mean(null_best_sharpes >= best_sharpe)

        null_mean = np.mean(null_best_sharpes)
        null_std = np.std(null_best_sharpes, ddof=1) if self.n_reps > 1 else 1.0
        deflated_sharpe = (best_sharpe - null_mean) / null_std if null_std > 0 else 0.0

        report_param_list = (
            effective_param_list if subsample_indices is not None
            else self._param_list
        )

        return OverfitResults(
            param_list=report_param_list,
            n_params=n_params,
            n_reps=self.n_reps,
            shuffle_method=self.shuffle_method,
            original_sharpes=original_sharpes,
            best_param_index=int(best_idx),
            best_sharpe=float(best_sharpe),
            solo_pvalues=solo_pvalues,
            unbiased_pvalue=float(unbiased_pvalue),
            unbiased_pvalues=unbiased_pvalues_ordered,
            null_best_sharpes=null_best_sharpes,
            prob_overfit=float(prob_overfit),
            deflated_sharpe=float(deflated_sharpe),
            sort_indices=sort_indices,
            returns=self.returns,
        )
