"""Multiprocessing validation pass runner."""

from __future__ import annotations

import inspect
import multiprocessing as mp
import os
import pickle
from collections.abc import Mapping, Sequence
from importlib import import_module

import numpy as np
import numpy.typing as npt

from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.ports import StrategyEvaluator
from algosystem.validation.domain.shufflers import SHUFFLE_METHODS
from algosystem.validation.domain.strategy import ParameterSet, StrategySpec


class MultiprocessingPassRunner:
    """Run validation passes across a multiprocessing pool."""

    def __init__(
        self,
        evaluator: StrategyEvaluator | None = None,
        worker_count: int | None = None,
    ) -> None:
        if worker_count is not None and worker_count < 1:
            raise ValidationError("worker_count must be positive")
        self._evaluator = evaluator
        self._worker_count = worker_count

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
        _raise_if_unpicklable(evaluator)

        worker_count = self._worker_count if self._worker_count is not None else os.cpu_count() or 1
        param_dicts = [parameter_set.to_dict() for parameter_set in parameter_sets]
        work_items = [
            (
                irep,
                returns,
                param_dicts,
                evaluator,
                shuffle_method,
                block_size,
                int(seed),
            )
            for irep, seed in enumerate(pass_seeds)
        ]

        rows: list[np.ndarray | None] = [None] * len(work_items)
        try:
            if worker_count == 1:
                for item in work_items:
                    irep, scores = worker_run_pass(item)
                    rows[irep] = scores
            else:
                try:
                    pool = mp.Pool(processes=worker_count)
                except (OSError, RuntimeError):
                    rows = _run_items_in_process(work_items)
                else:
                    with pool:
                        for irep, scores in pool.imap_unordered(worker_run_pass, work_items):
                            rows[irep] = scores
        except ValidationError:
            raise
        except Exception as exc:
            raise ValidationError("multiprocessing validation pass failed") from exc

        if any(row is None for row in rows):
            raise ValidationError("multiprocessing validation pass returned an incomplete matrix")
        return np.vstack([row for row in rows if row is not None])


def _run_items_in_process(work_items: Sequence[tuple]) -> list[np.ndarray | None]:
    rows: list[np.ndarray | None] = [None] * len(work_items)
    for item in work_items:
        irep, scores = worker_run_pass(item)
        rows[irep] = scores
    return rows


def worker_run_pass(args: tuple) -> tuple[int, np.ndarray]:
    """Run one validation pass in a worker process."""
    irep, returns, param_dicts, evaluator, shuffle_method, block_size, seed = args
    try:
        scores = _run_one_pass(
            irep=irep,
            returns=returns,
            param_dicts=param_dicts,
            evaluator=evaluator,
            shuffle_method=shuffle_method,
            block_size=block_size,
            seed=seed,
        )
    except Exception as exc:
        raise ValidationError(f"validation worker failed on pass {irep}") from exc
    return irep, scores


def _run_one_pass(
    *,
    irep: int,
    returns: np.ndarray,
    param_dicts: Sequence[Mapping[str, object]],
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

    scores = np.empty(len(param_dicts), dtype=np.float64)
    for index, params in enumerate(param_dicts):
        scores[index] = _evaluate(evaluator, params, shuffled)
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


def _raise_if_unpicklable(evaluator: StrategyEvaluator) -> None:
    if inspect.ismethod(evaluator):
        raise ValidationError(
            "backtest_fn must be a module-level function, not a lambda or closure; "
            "bound methods are not supported for multiprocessing"
        )
    name = getattr(evaluator, "__name__", "")
    qualname = getattr(evaluator, "__qualname__", "")
    if name == "<lambda>" or "<locals>" in qualname:
        raise ValidationError(
            "backtest_fn must be a module-level function, not a lambda or closure"
        )
    try:
        pickle.dumps(evaluator)
    except (pickle.PickleError, TypeError, AttributeError) as exc:
        raise ValidationError(
            "backtest_fn must be a module-level function, not a lambda or closure; "
            "module-level callable class instances are also supported when picklable"
        ) from exc


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
