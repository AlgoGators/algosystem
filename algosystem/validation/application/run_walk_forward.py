"""Walk-forward validation use case."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from algosystem.validation.application._strategy_loader import resolve_strategy_evaluator
from algosystem.validation.application.detect_overfitting import _coerce_returns_array
from algosystem.validation.domain.ports import StrategyEvaluator
from algosystem.validation.domain.statistics.walkforward import (
    WalkForwardResults,
    walk_forward_analysis,
)
from algosystem.validation.domain.strategy import StrategySpec


class RunWalkForward:
    """Run walk-forward analysis for a strategy spec."""

    def __init__(self, evaluator: StrategyEvaluator | None = None) -> None:
        self._evaluator = evaluator

    def execute(
        self,
        strategy: StrategySpec,
        returns: npt.NDArray[np.float64] | Sequence[float],
        *,
        n_folds: int = 5,
        is_ratio: float = 0.8,
        purge_gap: int = 0,
    ) -> WalkForwardResults:
        """Run walk-forward validation and return domain results."""
        evaluator = resolve_strategy_evaluator(strategy, self._evaluator)
        returns_array = _coerce_returns_array(returns)
        return walk_forward_analysis(
            backtest_fn=evaluator,
            returns=returns_array,
            param_grid=strategy.parameter_grid.to_dict(),
            n_folds=n_folds,
            is_ratio=is_ratio,
            purge_gap=purge_gap,
        )
