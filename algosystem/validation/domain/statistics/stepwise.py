"""
Stepwise permutation test with familywise error rate (FWE) control.

Based on Romano and Wolf (2016) "Efficient Computation of Adjusted p-Values
for Resampling-Based Stepdown Multiple Testing" as adapted by Timothy Masters
in VarScreen (p29-36 of the manual).

Key improvement over the traditional "best-of" MCPT:
- Traditional method gives correct p-values ONLY for the best competitor;
  all others are upper bounds (conservative → misses real signals).
- Stepwise method tests each hypothesis individually, best-to-worst, with
  the null distribution shrinking at each step (only non-rejected competitors
  contribute). This gives correct p-values for ALL competitors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.shufflers import SHUFFLE_METHODS


@dataclass(frozen=True)
class StepwiseResults:
    """Results from stepwise permutation test."""

    n_params: int
    n_reps: int
    alpha: float
    param_list: list
    original_sharpes: np.ndarray
    sort_indices: np.ndarray  # descending order of original Sharpes

    # Per-competitor results
    stepwise_pvalues: np.ndarray  # p-value from stepwise procedure (ordered best→worst)
    passed: np.ndarray  # bool array — True if null rejected (has signal)
    n_rejected: int  # how many nulls were rejected

    def summary(self) -> list[str]:
        """Return stepwise test results as formatted lines."""
        lines = [
            "=" * 72,
            "STEPWISE PERMUTATION TEST (Romano-Wolf)",
            "=" * 72,
            f"Competitors tested   : {self.n_params}",
            f"Permutation reps     : {self.n_reps}",
            f"FWE alpha            : {self.alpha}",
            f"Nulls rejected       : {self.n_rejected}",
            "",
        ]

        n_show = min(20, self.n_params)
        lines.extend(
            [
                f"Top {n_show} parameter sets (stepwise order):",
                "-" * 72,
                f"{'Rank':>4}  {'Sharpe':>8}  {'Step pval':>10}  {'Rejected':>8}  Params",
                "-" * 72,
            ]
        )
        for rank in range(n_show):
            idx = self.sort_indices[rank]
            pval = self.stepwise_pvalues[rank]
            rejected = "YES" if self.passed[idx] else "no"
            lines.append(
                f"{rank+1:4d}  {self.original_sharpes[idx]:8.4f}  "
                f"{pval:10.4f}  {rejected:>8}  {self.param_list[idx]}"
            )
        lines.append("-" * 72)
        return lines


def stepwise_permutation_test(  # noqa: C901
    backtest_fn: Callable,
    returns: np.ndarray,
    param_list: list,
    original_sharpes: np.ndarray,
    n_reps: int = 1000,
    alpha: float = 0.10,
    shuffle_method: str = "complete",
    block_size: int | None = None,
    seed: int = 42,
) -> StepwiseResults:
    """
    Run the stepwise permutation test (Masters/Romano-Wolf).

    This is slower than the traditional MCPT because it re-runs all
    permutations at each step. However, it provides correct (not
    conservative) p-values for ALL competitors, not just the best.

    Parameters
    ----------
    backtest_fn : callable
        (params_dict, returns_array) -> float (Sharpe)
    returns : np.ndarray
        Original returns series.
    param_list : list of dict
        All parameter combinations.
    original_sharpes : np.ndarray
        Pre-computed Sharpes on unpermuted data (from OverfitDetector.run()).
    n_reps : int
        Number of permutation replications.
    alpha : float
        Familywise error rate threshold (default 0.10).
    shuffle_method : str
        'complete', 'cyclic', or 'block'.
    block_size : int or None
        Block size for block shuffle.
    seed : int
        Random seed.

    Returns
    -------
    StepwiseResults
    """
    n_params = len(param_list)
    rng = np.random.default_rng(seed)

    # Sort indices: best (highest Sharpe) last in ascending array
    # We work backwards from best to worst
    sort_indices = np.argsort(-original_sharpes)  # descending

    passed = np.zeros(n_params, dtype=bool)
    stepwise_pvalues = np.full(n_params, np.nan)

    # Pre-generate seeds for reproducibility
    pass_seeds = rng.integers(0, 2**63, size=n_reps).tolist()

    shuffle_fn = SHUFFLE_METHODS.get(shuffle_method)
    if shuffle_fn is None:
        raise ValidationError(f"Unknown shuffle method: {shuffle_method}")

    # Stepwise: process from best to worst
    n_rejected = 0
    for step in range(n_params):
        this_i = sort_indices[step]  # index of current best remaining competitor
        count = 1  # start at 1

        for irep in range(n_reps):
            # Use the SAME permutation across all steps (Romano-Wolf requirement).
            # Only the set of competitors contributing to the max changes.
            rep_rng = np.random.default_rng(pass_seeds[irep])

            # Shuffle returns
            if shuffle_method == "block":
                shuffled = shuffle_fn(returns, rep_rng, block_size)
            else:
                shuffled = shuffle_fn(returns, rep_rng)

            # Find max Sharpe among ONLY the not-yet-rejected competitors
            max_f = -np.inf
            for i in range(n_params):
                if not passed[i]:
                    f = backtest_fn(param_list[i], shuffled)
                    if f > max_f:
                        max_f = f

            # Does the permuted max beat this competitor's original Sharpe?
            if max_f >= original_sharpes[this_i]:
                count += 1

        pval = count / (n_reps + 1)
        # Enforce monotonicity: stepwise p-values must be non-decreasing
        if step > 0 and not np.isnan(stepwise_pvalues[step - 1]):
            pval = max(pval, stepwise_pvalues[step - 1])
        stepwise_pvalues[step] = pval

        if pval <= alpha:
            passed[this_i] = True
            n_rejected += 1
        else:
            # Stop — no more can be rejected at this FWE level
            # Fill remaining with NaN (not tested)
            for remaining in range(step + 1, n_params):
                stepwise_pvalues[remaining] = np.nan
            break

    return StepwiseResults(
        n_params=n_params,
        n_reps=n_reps,
        alpha=alpha,
        param_list=param_list,
        original_sharpes=original_sharpes,
        sort_indices=sort_indices,
        stepwise_pvalues=stepwise_pvalues,
        passed=passed,
        n_rejected=n_rejected,
    )
