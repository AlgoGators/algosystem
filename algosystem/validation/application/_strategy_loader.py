"""Strategy callable resolution helpers for validation use cases."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.ports import StrategyEvaluator
from algosystem.validation.domain.strategy import ParameterGrid, StrategySpec


def qualified_path_for(evaluator: StrategyEvaluator) -> str:
    """Return a dotted path describing a callable evaluator."""
    module = getattr(evaluator, "__module__", None)
    qualname = getattr(evaluator, "__qualname__", None)
    if qualname is None and hasattr(evaluator, "__class__"):
        module = evaluator.__class__.__module__
        qualname = evaluator.__class__.__qualname__
    if not module or not qualname:
        raise ValidationError("backtest_fn must have a module and qualified name")
    return f"{module}.{qualname}"


def strategy_spec_from_callable(
    evaluator: StrategyEvaluator,
    parameter_grid: ParameterGrid | dict[str, list[Any]],
    *,
    name: str | None = None,
) -> StrategySpec:
    """Build a StrategySpec from a callable and a grid declaration."""
    strategy_name = name or getattr(evaluator, "__name__", evaluator.__class__.__name__)
    grid = (
        parameter_grid
        if isinstance(parameter_grid, ParameterGrid)
        else ParameterGrid(parameter_grid)
    )
    return StrategySpec(
        name=strategy_name,
        backtest_fn_path=qualified_path_for(evaluator),
        parameter_grid=grid,
    )


def resolve_strategy_evaluator(
    strategy: StrategySpec,
    evaluator: StrategyEvaluator | None = None,
) -> StrategyEvaluator:
    """Resolve the evaluator from an override or from the spec's dotted path."""
    if evaluator is not None:
        return evaluator

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
