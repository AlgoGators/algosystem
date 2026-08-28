"""Validation composition helpers and compatibility facade."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from importlib import import_module
from typing import Any

import numpy as np
import numpy.typing as npt

from algosystem.shared.errors import ValidationError
from algosystem.validation.application._strategy_loader import (
    resolve_strategy_evaluator,
    strategy_spec_from_callable,
)
from algosystem.validation.application.detect_overfitting import DetectOverfitting
from algosystem.validation.application.equity_curve_bridge import returns_from
from algosystem.validation.domain.ports import StrategyEvaluator
from algosystem.validation.domain.results import OverfitResults
from algosystem.validation.domain.strategy import ParameterGrid, StrategySpec
from algosystem.validation.infrastructure.default_runner import default_pass_runner


class OverfitDetector:
    """
    Backward-compatible convenience wrapper over DetectOverfitting.

    ``backtest_fn`` is passed to the runner as a function reference. When using
    more than one worker it must be picklable, normally a module-level function
    or a module-level callable class instance.
    """

    def __init__(
        self,
        backtest_fn: StrategyEvaluator,
        returns: npt.NDArray[np.float64] | Sequence[float],
        param_grid: dict[str, list[Any]],
        n_reps: int = 1000,
        shuffle_method: str = "complete",
        block_size: int | None = None,
        max_param_trials: int | None = None,
        n_workers: int | None = None,
        seed: int = 42,
    ) -> None:
        self.backtest_fn = backtest_fn
        self.returns = returns_from(returns, input_kind="returns")
        self.param_grid = param_grid
        self.n_reps = n_reps
        self.shuffle_method = shuffle_method
        self.block_size = block_size
        self.max_param_trials = max_param_trials
        self.n_workers = n_workers
        self.seed = seed
        self.strategy = strategy_spec_from_callable(
            backtest_fn,
            param_grid,
            name=getattr(backtest_fn, "__name__", "strategy"),
        )

    @property
    def param_list(self) -> list[dict[str, object]]:
        """Return the Cartesian parameter combinations in reproducible order."""
        return [
            parameter_set.to_dict() for parameter_set in self.strategy.parameter_grid.combinations()
        ]

    def run(self) -> OverfitResults:
        """Execute the detector and return overfitting results."""
        runner = default_pass_runner(self.backtest_fn, self.n_workers)
        return DetectOverfitting(runner).execute(
            strategy=self.strategy,
            returns=self.returns,
            n_reps=self.n_reps,
            shuffle_method=self.shuffle_method,
            block_size=self.block_size,
            max_param_trials=self.max_param_trials,
            seed=self.seed,
        )


def resolve_strategy(
    strategy: str | StrategySpec | StrategyEvaluator,
    param_grid: Mapping[str, Sequence[object]] | ParameterGrid | None = None,
) -> tuple[StrategySpec, StrategyEvaluator]:
    """Resolve a public strategy input into a spec and evaluator."""
    from algosystem.validation.infrastructure.strategies import (
        BACKTEST_FNS,
        STRATEGY_ALIASES,
        STRATEGY_REGISTRY,
    )

    if isinstance(strategy, StrategySpec):
        spec = _replace_grid(strategy, param_grid)
        return spec, resolve_strategy_evaluator(spec)

    if isinstance(strategy, str):
        normalized = strategy.strip()
        if not normalized:
            raise ValidationError("strategy must not be empty")
        canonical = STRATEGY_ALIASES.get(normalized, normalized)
        if canonical in STRATEGY_REGISTRY:
            spec = _replace_grid(STRATEGY_REGISTRY[canonical], param_grid)
            return spec, BACKTEST_FNS[canonical]
        evaluator = _load_callable_from_path(normalized)
        if param_grid is None:
            raise ValidationError("param_grid is required when strategy is a callable path")
        return (
            strategy_spec_from_callable(evaluator, _coerce_grid(param_grid), name=normalized),
            evaluator,
        )

    if callable(strategy):
        if param_grid is None:
            raise ValidationError("param_grid is required when strategy is a callable")
        return (
            strategy_spec_from_callable(strategy, _coerce_grid(param_grid)),
            strategy,
        )

    raise ValidationError("strategy must be a shipped name, StrategySpec, or callable")


def detect_overfitting(
    *,
    strategy: str | StrategySpec | StrategyEvaluator,
    returns: object,
    param_grid: Mapping[str, Sequence[object]] | ParameterGrid | None = None,
    n_reps: int = 1000,
    shuffle_method: str = "complete",
    block_size: int | None = None,
    max_param_trials: int | None = None,
    n_workers: int | None = None,
    seed: int | None = None,
) -> OverfitResults:
    """Run overfitting detection with default infrastructure composition."""
    spec, evaluator = resolve_strategy(strategy, param_grid=param_grid)
    runner = default_pass_runner(evaluator, n_workers)
    return DetectOverfitting(runner).execute(
        strategy=spec,
        returns=returns_from(returns, input_kind="returns"),
        n_reps=n_reps,
        shuffle_method=shuffle_method,
        block_size=block_size,
        max_param_trials=max_param_trials,
        seed=seed,
    )


def _replace_grid(
    strategy: StrategySpec,
    param_grid: Mapping[str, Sequence[object]] | ParameterGrid | None,
) -> StrategySpec:
    if param_grid is None:
        return strategy
    return StrategySpec(
        name=strategy.name,
        backtest_fn_path=strategy.backtest_fn_path,
        parameter_grid=_coerce_grid(param_grid),
    )


def _coerce_grid(param_grid: Mapping[str, Sequence[object]] | ParameterGrid) -> ParameterGrid:
    return param_grid if isinstance(param_grid, ParameterGrid) else ParameterGrid(param_grid)


def _load_callable_from_path(path: str) -> StrategyEvaluator:
    normalized = path.replace(":", ".")
    module_path, _, attr_path = normalized.rpartition(".")
    if not module_path or not attr_path:
        raise ValidationError(
            "custom strategy must be a shipped name or qualified module:function path"
        )
    try:
        module = import_module(module_path)
        resolved: object = module
        for attr in attr_path.split("."):
            resolved = getattr(resolved, attr)
    except (ImportError, AttributeError) as exc:
        raise ValidationError(f"could not resolve strategy callable: {path}") from exc
    if not callable(resolved):
        raise ValidationError(f"resolved strategy is not callable: {path}")
    return resolved


__all__ = ["OverfitDetector", "detect_overfitting", "resolve_strategy"]
