"""Signal-screening use case."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from algosystem.validation.application._strategy_loader import resolve_strategy_evaluator
from algosystem.validation.application.detect_overfitting import (
    DetectOverfitting,
    _coerce_returns_array,
)
from algosystem.validation.application.signal_analyzer import SignalAnalyzer
from algosystem.validation.domain.ports import PassRunner, StrategyEvaluator
from algosystem.validation.domain.statistics.signal_analyzer import SignalAnalysisReport
from algosystem.validation.domain.strategy import StrategySpec


class ScreenSignals:
    """Run the signal-analysis workflow over a strategy parameter grid."""

    def __init__(
        self,
        runner: PassRunner,
        evaluator: StrategyEvaluator | None = None,
    ) -> None:
        self._runner = runner
        self._evaluator = evaluator

    def execute(
        self,
        strategy: StrategySpec,
        returns: npt.NDArray[np.float64] | Sequence[float],
        *,
        n_reps: int = 500,
        shuffle_method: str = "complete",
        seed: int | None = None,
        run_pbo: bool = True,
        run_walkforward: bool = True,
        run_tracker: bool = True,
    ) -> SignalAnalysisReport:
        """Screen the signal parameter space and return a report object."""
        evaluator = resolve_strategy_evaluator(strategy, self._evaluator)
        returns_array = _coerce_returns_array(returns)
        analyzer = SignalAnalyzer(
            runner=self._runner,
            backtest_fn=evaluator,
            returns=returns_array,
            signal_params=strategy.parameter_grid.to_dict(),
            strategy_name=strategy.name,
            n_reps=n_reps,
            shuffle_method=shuffle_method,
            seed=42 if seed is None else seed,
        )
        analyzer._overfit_results = DetectOverfitting(self._runner).execute(
            strategy=strategy,
            returns=returns_array,
            n_reps=n_reps,
            shuffle_method=shuffle_method,
            seed=seed,
        )
        analyzer.compute_psr_dsr()
        if run_pbo and analyzer.total_combinations >= 4:
            analyzer.compute_pbo()
        if run_walkforward:
            analyzer.compute_walkforward()
        if run_tracker:
            analyzer.run_trial_tracker()

        verdict, confidence = analyzer._synthesize_verdict()
        return SignalAnalysisReport(
            strategy_name=analyzer.strategy_name,
            n_signals=analyzer.n_signals,
            signal_names=analyzer.signal_names,
            total_combinations=analyzer.total_combinations,
            overfit_results=analyzer._overfit_results,
            psr_result=analyzer._psr_result,
            dsr_result=analyzer._dsr_result,
            pbo_result=analyzer._pbo_result,
            wf_result=analyzer._wf_result,
            trial_tracker=analyzer._tracker,
            figures=[],
            verdict=verdict,
            confidence=confidence,
        )
