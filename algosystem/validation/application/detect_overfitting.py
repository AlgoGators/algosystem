"""Permutation-based overfitting detection use case."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.ports import PassRunner
from algosystem.validation.domain.results import OverfitResults
from algosystem.validation.domain.shufflers import SHUFFLE_METHODS
from algosystem.validation.domain.strategy import ParameterSet, StrategySpec


class DetectOverfitting:
    """Orchestrate permutation passes and compute overfitting statistics."""

    def __init__(self, runner: PassRunner) -> None:
        self._runner = runner

    def execute(
        self,
        strategy: StrategySpec,
        returns: npt.NDArray[np.float64] | Sequence[float],
        *,
        n_reps: int = 1000,
        shuffle_method: str = "complete",
        block_size: int | None = None,
        max_param_trials: int | None = None,
        seed: int | None = None,
    ) -> OverfitResults:
        """Run the permutation test and return domain results."""
        if n_reps < 1:
            raise ValidationError("n_reps must be at least 1")
        if shuffle_method not in SHUFFLE_METHODS:
            raise ValidationError(f"Unknown shuffle method: {shuffle_method}")
        if block_size is not None and block_size < 1:
            raise ValidationError("block_size must be positive")

        returns_array = _coerce_returns_array(returns)
        parameter_sets = list(strategy.parameter_grid.combinations())
        if not parameter_sets:
            raise ValidationError("parameter grid would produce zero combinations")

        rng = np.random.default_rng(seed)
        effective_parameter_sets = _subsample_parameter_sets(
            parameter_sets,
            max_param_trials=max_param_trials,
            rng=rng,
        )
        pass_seeds = [int(seed_value) for seed_value in rng.integers(0, 2**63, size=n_reps + 1)]

        try:
            score_matrix = self._runner.run_passes(
                strategy=strategy,
                returns=returns_array,
                parameter_sets=effective_parameter_sets,
                pass_seeds=pass_seeds,
                shuffle_method=shuffle_method,
                block_size=block_size,
            )
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError("pass runner failed during overfitting detection") from exc

        return _compute_results(
            score_matrix=score_matrix,
            parameter_sets=effective_parameter_sets,
            n_reps=n_reps,
            shuffle_method=shuffle_method,
            returns=returns_array,
        )


def _coerce_returns_array(returns: npt.NDArray[np.float64] | Sequence[float]) -> np.ndarray:
    values = np.asarray(returns, dtype=np.float64)
    if values.ndim != 1:
        raise ValidationError("returns must be one-dimensional")
    if values.size == 0:
        raise ValidationError("returns must not be empty")
    if values.size == 1:
        raise ValidationError("returns must contain at least two observations")
    if not np.isfinite(values).all():
        raise ValidationError("returns must contain only finite values")
    return values


def _subsample_parameter_sets(
    parameter_sets: list[ParameterSet],
    *,
    max_param_trials: int | None,
    rng: np.random.Generator,
) -> list[ParameterSet]:
    if max_param_trials is None or len(parameter_sets) <= max_param_trials:
        return parameter_sets
    if max_param_trials < 1:
        raise ValidationError("max_param_trials must be positive")

    indices = rng.choice(len(parameter_sets), size=max_param_trials, replace=False)
    indices.sort()
    return [parameter_sets[int(index)] for index in indices]


def _compute_results(  # noqa: C901
    *,
    score_matrix: np.ndarray,
    parameter_sets: Sequence[ParameterSet],
    n_reps: int,
    shuffle_method: str,
    returns: np.ndarray,
) -> OverfitResults:
    n_params = len(parameter_sets)
    total_passes = n_reps + 1
    score_matrix = np.asarray(score_matrix, dtype=np.float64)
    if score_matrix.shape != (total_passes, n_params):
        raise ValidationError(
            f"pass runner returned shape {score_matrix.shape}, expected {(total_passes, n_params)}"
        )
    if not np.isfinite(score_matrix).all():
        raise ValidationError("pass runner returned non-finite scores")

    original_sharpes = score_matrix[0].copy()
    sort_indices = np.argsort(-original_sharpes)

    solo_count = np.ones(n_params, dtype=np.int64)
    unbiased_count = np.ones(n_params, dtype=np.int64)
    null_best_sharpes = np.empty(n_reps, dtype=np.float64)

    for irep in range(1, total_passes):
        perm_sharpes = score_matrix[irep]
        for i in range(n_params):
            if perm_sharpes[i] >= original_sharpes[i]:
                solo_count[i] += 1

        running_best = -np.inf
        for rank in range(n_params - 1, -1, -1):
            idx = sort_indices[rank]
            if perm_sharpes[idx] > running_best:
                running_best = perm_sharpes[idx]
            if running_best >= original_sharpes[idx]:
                unbiased_count[idx] += 1

        null_best_sharpes[irep - 1] = np.max(perm_sharpes)

    total_obs = total_passes
    solo_pvalues = solo_count / total_obs

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

    best_idx = int(sort_indices[0])
    best_sharpe = float(original_sharpes[best_idx])
    unbiased_pvalue = float(unbiased_pvalues_ordered[0])
    prob_overfit = float(np.mean(null_best_sharpes >= best_sharpe))

    null_mean = np.mean(null_best_sharpes)
    null_std = np.std(null_best_sharpes, ddof=1) if n_reps > 1 else 1.0
    deflated_sharpe = float((best_sharpe - null_mean) / null_std) if null_std > 0 else 0.0

    return OverfitResults(
        param_list=[parameter_set.to_dict() for parameter_set in parameter_sets],
        n_params=n_params,
        n_reps=n_reps,
        shuffle_method=shuffle_method,
        original_sharpes=original_sharpes,
        best_param_index=best_idx,
        best_sharpe=best_sharpe,
        solo_pvalues=solo_pvalues,
        unbiased_pvalue=unbiased_pvalue,
        unbiased_pvalues=unbiased_pvalues_ordered,
        null_best_sharpes=null_best_sharpes,
        prob_overfit=prob_overfit,
        deflated_sharpe=deflated_sharpe,
        sort_indices=sort_indices,
        returns=returns,
    )
