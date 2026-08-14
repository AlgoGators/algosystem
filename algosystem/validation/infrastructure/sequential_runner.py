"""Sequential validation pass runner."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib import import_module

import numpy as np
import numpy.typing as npt

from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.ports import StrategyEvaluator
from algosystem.validation.domain.shufflers import SHUFFLE_METHODS
from algosystem.validation.domain.strategy import ParameterSet, StrategySpec


class SequentialPassRunner:
    """Run validation passes in the current process."""

    def __init__(self, evaluator: StrategyEvaluator | None = None) -> None:
        self._evaluator = evaluator

    def run_passes(
        self,
        strategy: StrategySpec,
        returns: npt.NDArray[np.float64],
        parameter_sets: Sequence[ParameterSet],
        pass_seeds: Sequence[int],
        shuffle_method: str,
        block_size: int | None = None,
    ) -> npt.NDArray[np.float64]:
        """Run all requested passes and return a score matrix."""
        evaluator = self._evaluator or _load_strategy_evaluator(strategy)
        try:
            rows = [
                _run_one_pass(
                    irep=irep,
                    returns=returns,
                    parameter_sets=parameter_sets,
                    evaluator=evaluator,
                    shuffle_method=shuffle_method,
                    block_size=block_size,
                    seed=int(seed),
                )
                for irep, seed in enumerate(pass_seeds)
            ]
        except Exception as exc:
            raise ValidationError("sequential validation pass failed") from exc
        return np.vstack(rows)


def _run_one_pass(
    *,
    irep: int,
    returns: np.ndarray,
    parameter_sets: Sequence[ParameterSet],
    evaluator: StrategyEvaluator,
    shuffle_method: str,
    block_size: int | None,
    seed: int,
) -> np.ndarray:
    if irep == 0:
        shuffled = returns
    else:
        shuffle_fn = SHUFFLE_METHODS.get(shuffle_method)
        if shuffle_fn is None:
            raise ValidationError(f"Unknown shuffle method: {shuffle_method}")
        rng = np.random.default_rng(seed)
        if shuffle_method == "block":
            shuffled = shuffle_fn(returns, rng, block_size)
        else:
            shuffled = shuffle_fn(returns, rng)

    scores = np.empty(len(parameter_sets), dtype=np.float64)
    for index, parameter_set in enumerate(parameter_sets):
        scores[index] = _evaluate(evaluator, parameter_set.to_dict(), shuffled)
    return scores


def _evaluate(
    evaluator: StrategyEvaluator,
    params: Mapping[str, object],
    returns: np.ndarray,
) -> float:
    try:
        score = float(evaluator(params, returns))
    except Exception as exc:
        raise ValidationError("strategy evaluation failed") from exc
    if not np.isfinite(score):
        raise ValidationError("strategy evaluator returned a non-finite score")
    return score


def _load_strategy_evaluator(strategy: StrategySpec) -> StrategyEvaluator:
    module_path, _, attr_path = strategy.backtest_fn_path.rpartition(".")
    if not module_path or not attr_path:
        raise ValidationError("backtest_fn path must include a module and attribute")

    try:
        module = import_module(module_path)
        resolved: object = module
        for attr in attr_path.split("."):
            resolved = getattr(resolved, attr)
    except (ImportError, AttributeError) as exc:
        raise ValidationError(
            f"could not resolve backtest_fn from path {strategy.backtest_fn_path!r}"
        ) from exc
    if not callable(resolved):
        raise ValidationError(
            f"resolved backtest_fn is not callable: {strategy.backtest_fn_path!r}"
        )
    return resolved
