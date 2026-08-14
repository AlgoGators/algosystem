"""
Combinatorially Symmetric Cross-Validation (CSCV) for computing
the Probability of Backtest Overfitting (PBO).

Reference: Bailey, Borwein, Lopez de Prado, Zhu (2015)
"The Probability of Backtest Overfitting"
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.validation_metric import ValidationMetricKey


@dataclass(frozen=True)
class PBOResults:
    """Results of Probability of Backtest Overfitting analysis."""

    pbo: float  # P(logit > 0) — fraction where IS-best underperforms OOS median
    logits: np.ndarray  # logit values for each IS/OOS combination
    n_combinations: int  # total C(S, S/2) combinations evaluated
    n_splits: int  # S (number of temporal blocks)
    n_configs: int  # N (number of strategy configurations)

    # Per-combination details
    is_best_indices: np.ndarray  # which config was best IS in each combo
    oos_ranks: np.ndarray  # OOS rank of the IS-best config (1-based)
    oos_sharpes_of_best: np.ndarray  # OOS Sharpe of the IS-best config
    is_sharpes_of_best: np.ndarray  # IS Sharpe of the IS-best config

    # Distribution stats
    logit_mean: float
    logit_std: float

    def summary(self) -> str:
        """Human-readable summary."""
        verdict = (
            "LIKELY OVERFIT"
            if self.pbo > 0.5
            else "BORDERLINE" if self.pbo > 0.3 else "ACCEPTABLE" if self.pbo > 0.1 else "GOOD"
        )
        return (
            f"PBO = {self.pbo:.4f} [{verdict}]\n"
            f"  Combinations evaluated: {self.n_combinations}\n"
            f"  Splits: {self.n_splits}, Configs: {self.n_configs}\n"
            f"  Logit mean: {self.logit_mean:.4f}, std: {self.logit_std:.4f}\n"
            f"  Interpretation: {self.pbo*100:.1f}% of IS/OOS splits show\n"
            f"  the best in-sample choice underperforming the OOS median."
        )


def compute_pbo(
    returns_matrix: np.ndarray,
    n_splits: int = 10,
    metric: str = "sharpe",
    max_combinations: int | None = None,
    seed: int = 42,
) -> PBOResults:
    """
    Compute the Probability of Backtest Overfitting via CSCV.

    Parameters
    ----------
    returns_matrix : np.ndarray, shape (T, N)
        Per-period returns for each of N configurations over T periods.
        Each column is one strategy configuration's return series.
    n_splits : int
        Number of temporal blocks S (must be even). Default 10.
    metric : str
        Performance metric. 'sharpe' (default) or 'total_return'.
    max_combinations : int or None
        If set, randomly sample this many combinations instead of all C(S,S/2).
        Useful when S is large (e.g., S=16 gives 12870 combinations).
    seed : int
        Random seed for combination sampling.

    Returns
    -------
    PBOResults
    """
    T, N = returns_matrix.shape

    if n_splits % 2 != 0:
        raise ValidationError(f"n_splits must be even, got {n_splits}")
    if n_splits > T:
        raise ValidationError(f"n_splits ({n_splits}) cannot exceed T ({T})")
    if N < 2:
        raise ValidationError(f"Need at least 2 configurations, got {N}")

    # Split into S temporal blocks (preserve time order!)
    block_size = T // n_splits
    # Trim to exact multiple
    T_trimmed = block_size * n_splits
    matrix = returns_matrix[:T_trimmed]

    # Reshape into (S, block_size, N)
    blocks = matrix.reshape(n_splits, block_size, N)

    # Generate all C(S, S/2) combinations
    half = n_splits // 2
    all_combos = list(itertools.combinations(range(n_splits), half))

    rng = np.random.default_rng(seed)
    if max_combinations is not None and len(all_combos) > max_combinations:
        indices = rng.choice(len(all_combos), size=max_combinations, replace=False)
        combos = [all_combos[i] for i in sorted(indices)]
    else:
        combos = all_combos

    n_combos = len(combos)
    logits = np.empty(n_combos)
    is_best_indices = np.empty(n_combos, dtype=int)
    oos_ranks = np.empty(n_combos, dtype=int)
    oos_sharpes_of_best = np.empty(n_combos)
    is_sharpes_of_best = np.empty(n_combos)

    all_block_indices = set(range(n_splits))

    for ci, is_blocks in enumerate(combos):
        oos_blocks = sorted(all_block_indices - set(is_blocks))

        # Concatenate blocks for IS and OOS
        is_returns = np.concatenate([blocks[b] for b in is_blocks], axis=0)  # (half*block_size, N)
        oos_returns = np.concatenate([blocks[b] for b in oos_blocks], axis=0)

        # Compute performance for each configuration
        is_perf = _compute_performance(is_returns, metric)  # shape (N,)
        oos_perf = _compute_performance(oos_returns, metric)  # shape (N,)

        # Find best IS configuration
        best_is = np.argmax(is_perf)
        is_best_indices[ci] = best_is
        is_sharpes_of_best[ci] = is_perf[best_is]
        oos_sharpes_of_best[ci] = oos_perf[best_is]

        # Find OOS rank of best IS config (1 = best OOS, N = worst OOS)
        oos_sorted = np.argsort(-oos_perf)  # descending
        rank = np.where(oos_sorted == best_is)[0][0] + 1  # 1-based
        oos_ranks[ci] = rank

        # Compute logit
        omega = (rank - 0.5) / N
        # Clip to avoid log(0) or log(inf)
        omega = np.clip(omega, 1e-10, 1 - 1e-10)
        logits[ci] = np.log(omega / (1 - omega))

    pbo = np.mean(logits > 0)

    return PBOResults(
        pbo=float(pbo),
        logits=logits,
        n_combinations=n_combos,
        n_splits=n_splits,
        n_configs=N,
        is_best_indices=is_best_indices,
        oos_ranks=oos_ranks,
        oos_sharpes_of_best=oos_sharpes_of_best,
        is_sharpes_of_best=is_sharpes_of_best,
        logit_mean=float(np.mean(logits)),
        logit_std=float(np.std(logits)),
    )


def _compute_performance(returns: np.ndarray, metric: str) -> np.ndarray:
    """
    Compute performance metric for each column (configuration).

    Parameters
    ----------
    returns : np.ndarray, shape (T, N)
    metric : str, 'sharpe' or 'total_return'

    Returns
    -------
    np.ndarray, shape (N,)
    """
    if metric == "total_return":
        return np.sum(returns, axis=0)

    # Sharpe ratio (annualized, assumes daily data by default)
    means = np.mean(returns, axis=0)
    stds = np.std(returns, axis=0, ddof=1)
    # Zero-vol configs get Sharpe = 0 (not noise)
    zero_vol = stds < 1e-12
    stds = np.where(zero_vol, 1.0, stds)
    result = (means / stds) * np.sqrt(252)
    result[zero_vol] = 0.0
    return result


def cost_sensitivity_pbo(
    returns_matrix: np.ndarray,
    cost_bps_range: list | None = None,
    n_splits: int = 10,
    seed: int = 42,
) -> dict:
    """
    Compute PBO at different transaction cost assumptions.

    Shows how fragile a strategy's validation is to cost assumptions.
    A strategy whose PBO jumps from 0.1 to 0.9 between 2bp and 5bp is fragile.

    Parameters
    ----------
    returns_matrix : np.ndarray, shape (T, N)
        Per-period gross returns for each configuration.
    cost_bps_range : list of float
        Cost levels in basis points to test. Default [0, 1, 2, 3, 5, 7, 10].
    n_splits : int
        Number of temporal blocks for CSCV.
    seed : int
        Random seed.

    Returns
    -------
    dict with keys:
        cost_levels: list of float (bps)
        pbos: list of float (PBO at each cost level)
        breakeven_cost_bps: float (cost level where PBO crosses 0.5)
    """
    if cost_bps_range is None:
        cost_bps_range = [0, 1, 2, 3, 5, 7, 10]

    pbos = []
    for cost_bps in cost_bps_range:
        # Subtract cost from each period's returns (cost per period in decimal)
        cost_decimal = cost_bps / 10000.0
        adjusted = returns_matrix - cost_decimal
        result = compute_pbo(adjusted, n_splits=n_splits, seed=seed)
        pbos.append(result.pbo)

    # Find breakeven: interpolate where PBO crosses 0.5
    breakeven = float("inf")
    for i in range(len(pbos) - 1):
        if pbos[i] < 0.5 <= pbos[i + 1]:
            # Linear interpolation
            frac = (0.5 - pbos[i]) / (pbos[i + 1] - pbos[i])
            breakeven = cost_bps_range[i] + frac * (cost_bps_range[i + 1] - cost_bps_range[i])
            break
    if pbos[0] >= 0.5:
        breakeven = 0.0  # already overfit at zero cost

    return {
        "cost_levels": cost_bps_range,
        ValidationMetricKey.PBOS.value: pbos,
        ValidationMetricKey.BREAKEVEN_COST_BPS.value: float(breakeven),
    }
