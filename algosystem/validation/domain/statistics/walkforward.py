"""
Walk-forward analysis with purging for overfitting detection.

Splits data into rolling IS/OOS windows, optimizes on IS, evaluates on OOS.
Computes Walk-Forward Efficiency (WFE) as a measure of strategy robustness.

Purging removes observations near the IS/OOS boundary to prevent information
leakage from overlapping lookback windows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict

import numpy as np

from algosystem.shared.errors import ValidationError


@dataclass(frozen=True)
class WalkForwardResults:
    """Results from walk-forward analysis."""

    n_folds: int
    purge_gap: int

    # Per-fold results
    is_sharpes: np.ndarray  # best IS Sharpe per fold
    oos_sharpes: np.ndarray  # OOS Sharpe of IS-best per fold
    best_params_per_fold: list  # which param set won IS in each fold
    degradation_ratios: np.ndarray  # OOS/IS per fold

    # Aggregate metrics
    wfe: float  # Walk-Forward Efficiency = mean(OOS) / mean(IS)
    mean_is_sharpe: float
    mean_oos_sharpe: float
    frac_oos_positive: float  # fraction of folds with OOS Sharpe > 0
    frac_oos_profitable: float  # fraction of folds with degradation > 0.5

    # Catastrophic veto
    catastrophic_folds: list = field(default_factory=list)  # fold indices that triggered veto
    vetoed: bool = False  # True if any fold triggered catastrophic veto

    def summary(self) -> list[str]:
        """Return walk-forward analysis results as formatted lines."""
        if self.wfe >= 0.7:
            verdict = "EXCELLENT"
        elif self.wfe >= 0.5:
            verdict = "PASSING"
        elif self.wfe >= 0.3:
            verdict = "WEAK"
        else:
            verdict = "FAILING - likely overfit"

        lines = [
            "=" * 72,
            "WALK-FORWARD ANALYSIS",
            "=" * 72,
            f"Folds                : {self.n_folds}",
            f"Purge gap            : {self.purge_gap} periods",
            "",
            f"Walk-Forward Eff.    : {self.wfe:.4f}  [{verdict}]",
            f"Mean IS Sharpe       : {self.mean_is_sharpe:.4f}",
            f"Mean OOS Sharpe      : {self.mean_oos_sharpe:.4f}",
            f"Folds OOS > 0        : {self.frac_oos_positive:.1%}",
        ]
        if self.vetoed:
            lines.append(f"CATASTROPHIC VETO    : YES - folds {self.catastrophic_folds}")
        lines.extend(
            [
                "",
                "Per-fold breakdown:",
                "-" * 72,
                f"{'Fold':>4}  {'IS Sharpe':>10}  {'OOS Sharpe':>11}  {'Degrad':>8}  Best params",
                "-" * 72,
            ]
        )
        for i in range(self.n_folds):
            dr = self.degradation_ratios[i]
            dr_str = f"{dr:.2f}" if np.isfinite(dr) else "N/A"
            lines.append(
                f"{i+1:4d}  {self.is_sharpes[i]:10.4f}  "
                f"{self.oos_sharpes[i]:11.4f}  {dr_str:>8}  "
                f"{self.best_params_per_fold[i]}"
            )
        lines.append("-" * 72)
        return lines


def walk_forward_analysis(
    backtest_fn: Callable,
    returns: np.ndarray,
    param_grid: Dict[str, list],
    n_folds: int = 5,
    is_ratio: float = 0.8,
    purge_gap: int = 0,
) -> WalkForwardResults:
    """
    Run walk-forward analysis with optional purging.

    Parameters
    ----------
    backtest_fn : callable
        (params_dict, returns_array) -> float (Sharpe)
    returns : np.ndarray
        Full returns series.
    param_grid : dict
        Parameter grid (Cartesian product of all values).
    n_folds : int
        Number of walk-forward folds (default 5).
    is_ratio : float
        Fraction of each fold used for in-sample (default 0.8).
    purge_gap : int
        Number of periods to remove between IS and OOS (default 0).

    Returns
    -------
    WalkForwardResults
    """
    import itertools

    n = len(returns)
    keys = sorted(param_grid.keys())
    values = [param_grid[k] for k in keys]
    param_list = [dict(zip(keys, combo)) for combo in itertools.product(*values)]

    # Compute fold boundaries
    # Each fold: [fold_start, fold_end) with IS = first is_ratio, OOS = rest
    fold_size = n // n_folds
    if fold_size < 20:
        raise ValidationError(f"Fold size {fold_size} too small (n={n}, folds={n_folds})")

    is_sharpes = np.empty(n_folds)
    oos_sharpes = np.empty(n_folds)
    best_params_per_fold = []
    degradation_ratios = np.empty(n_folds)

    for fold in range(n_folds):
        fold_start = fold * fold_size
        fold_end = fold_start + fold_size if fold < n_folds - 1 else n

        is_end = fold_start + int((fold_end - fold_start) * is_ratio)
        oos_start = is_end + purge_gap

        if oos_start >= fold_end:
            # Not enough room for OOS after purging — skip purge
            oos_start = is_end

        is_data = returns[fold_start:is_end]
        oos_data = returns[oos_start:fold_end]

        if len(is_data) < 10 or len(oos_data) < 5:
            is_sharpes[fold] = 0.0
            oos_sharpes[fold] = 0.0
            best_params_per_fold.append({})
            degradation_ratios[fold] = 0.0
            continue

        # Find best params on IS
        best_is = -np.inf
        best_p = param_list[0]
        for p in param_list:
            s = backtest_fn(p, is_data)
            if s > best_is:
                best_is = s
                best_p = p

        # Evaluate on OOS
        oos_s = backtest_fn(best_p, oos_data)

        is_sharpes[fold] = best_is
        oos_sharpes[fold] = oos_s
        best_params_per_fold.append(best_p)
        # Only compute degradation ratio when IS is meaningfully positive
        degradation_ratios[fold] = oos_s / best_is if best_is > 1e-12 else 0.0

    mean_is = np.mean(is_sharpes)
    mean_oos = np.mean(oos_sharpes)
    # WFE only meaningful when mean IS is positive
    wfe = mean_oos / mean_is if mean_is > 1e-12 else 0.0

    # Catastrophic veto: reject if any fold has SR < -1.0 or
    # degradation < -0.5 (OOS is opposite sign and large)
    catastrophic_folds = []
    for i in range(n_folds):
        if oos_sharpes[i] < -1.0:
            catastrophic_folds.append(i + 1)
        elif is_sharpes[i] > 0.5 and oos_sharpes[i] < -0.5:
            catastrophic_folds.append(i + 1)

    return WalkForwardResults(
        n_folds=n_folds,
        purge_gap=purge_gap,
        is_sharpes=is_sharpes,
        oos_sharpes=oos_sharpes,
        best_params_per_fold=best_params_per_fold,
        degradation_ratios=degradation_ratios,
        wfe=float(wfe),
        mean_is_sharpe=float(mean_is),
        mean_oos_sharpe=float(mean_oos),
        frac_oos_positive=float(np.mean(oos_sharpes > 0)),
        frac_oos_profitable=float(np.mean(degradation_ratios > 0.5)),
        catastrophic_folds=catastrophic_folds,
        vetoed=len(catastrophic_folds) > 0,
    )
