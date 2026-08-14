"""Signal parameter-space analysis use case."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt

from algosystem.validation.application._strategy_loader import qualified_path_for
from algosystem.validation.application.detect_overfitting import DetectOverfitting
from algosystem.validation.domain.ports import ChartRenderer, PassRunner, StrategyEvaluator
from algosystem.validation.domain.statistics.cscv import compute_pbo
from algosystem.validation.domain.statistics.psr_dsr import (
    TrialTracker,
    deflated_sharpe_ratio,
    probabilistic_sharpe_ratio,
)
from algosystem.validation.domain.statistics.signal_analyzer import SignalAnalysisReport
from algosystem.validation.domain.statistics.walkforward import walk_forward_analysis
from algosystem.validation.domain.strategy import ParameterGrid, StrategySpec


class SignalAnalyzer:
    """
    Analyze a strategy with N signal parameters for overfitting.

    Runner and renderer dependencies are injected so the use case can orchestrate
    validation without choosing concrete infrastructure adapters.
    """

    def __init__(
        self,
        runner: PassRunner,
        backtest_fn: StrategyEvaluator,
        returns: npt.NDArray[np.float64] | Sequence[float],
        signal_params: Mapping[str, Sequence[object]],
        strategy_name: str = "strategy",
        n_reps: int = 500,
        shuffle_method: str = "complete",
        seed: int = 42,
        chart_renderer: ChartRenderer | None = None,
    ) -> None:
        self._runner = runner
        self._chart_renderer = chart_renderer
        self.backtest_fn = backtest_fn
        self.returns = np.asarray(returns, dtype=np.float64)
        self.signal_params = {str(key): list(values) for key, values in signal_params.items()}
        self.strategy_name = strategy_name
        self.n_reps = n_reps
        self.shuffle_method = shuffle_method
        self.seed = seed

        self.parameter_grid = ParameterGrid(self.signal_params)
        self.signal_names = list(self.parameter_grid.to_dict().keys())
        self.n_signals = len(self.signal_names)
        self._param_list = [
            parameter_set.to_dict() for parameter_set in self.parameter_grid.combinations()
        ]
        self.total_combinations = len(self._param_list)

        self._overfit_results: Any = None
        self._psr_result: Any = None
        self._dsr_result: Any = None
        self._pbo_result: Any = None
        self._wf_result: Any = None
        self._tracker: Any = None

    def run_detector(self, n_reps: int | None = None) -> Any:
        """Run the permutation-based overfitting detector."""
        strategy = StrategySpec(
            name=self.strategy_name,
            backtest_fn_path=qualified_path_for(self.backtest_fn),
            parameter_grid=self.parameter_grid,
        )
        self._overfit_results = DetectOverfitting(self._runner).execute(
            strategy=strategy,
            returns=self.returns,
            n_reps=self.n_reps if n_reps is None else n_reps,
            shuffle_method=self.shuffle_method,
            seed=self.seed,
        )
        return self._overfit_results

    def compute_psr_dsr(self) -> tuple[Any, Any]:
        """Compute PSR and DSR for the best strategy."""
        if self._overfit_results is None:
            self.run_detector()

        results = self._overfit_results
        self._psr_result = probabilistic_sharpe_ratio(self.returns, sr0=0.0)
        self._dsr_result = deflated_sharpe_ratio(
            returns=self.returns,
            n_trials=results.n_params,
            all_sharpes=results.original_sharpes,
            sr_hat=results.best_sharpe,
        )
        return self._psr_result, self._dsr_result

    def compute_pbo(self, n_splits: int = 10) -> Any:
        """
        Compute Probability of Backtest Overfitting via CSCV.

        Builds a returns matrix by evaluating each parameter configuration on
        each temporal block independently.
        """
        if self._overfit_results is None:
            self.run_detector()

        n = len(self.returns)
        n_configs = len(self._param_list)
        block_size = n // n_splits
        trimmed_length = block_size * n_splits
        returns_matrix = np.zeros((trimmed_length, n_configs))

        for config_index, params in enumerate(self._param_list):
            for block_index in range(n_splits):
                block_start = block_index * block_size
                block_end = block_start + block_size
                block_returns = self.returns[block_start:block_end]
                block_sharpe = self.backtest_fn(params, block_returns)
                scale = np.clip(block_sharpe, -0.9, 5.0) if abs(block_sharpe) > 1e-12 else 0.0
                returns_matrix[block_start:block_end, config_index] = block_returns * (
                    0.5 + 0.5 * scale
                )

        self._pbo_result = compute_pbo(
            returns_matrix,
            n_splits=n_splits,
            seed=self.seed,
        )
        return self._pbo_result

    def compute_walkforward(self, n_folds: int = 5, purge_gap: int = 0) -> Any:
        """Run walk-forward analysis."""
        self._wf_result = walk_forward_analysis(
            backtest_fn=self.backtest_fn,
            returns=self.returns,
            param_grid=self.signal_params,
            n_folds=n_folds,
            purge_gap=purge_gap,
        )
        return self._wf_result

    def run_trial_tracker(self) -> Any:
        """Record all parameter combinations in the trial tracker."""
        if self._overfit_results is None:
            self.run_detector()

        self._tracker = TrialTracker()
        for index, params in enumerate(self._param_list):
            sharpe = float(self._overfit_results.original_sharpes[index])
            self._tracker.record_trial(
                self.returns,
                sharpe,
                params,
                self.strategy_name,
            )
        return self._tracker

    def visualize(self, save_path: str | None = None) -> list[object]:
        """Render analysis charts with the injected renderer, when present."""
        if self._chart_renderer is None:
            return []
        if self._overfit_results is None:
            self.run_detector()
        return [
            self._chart_renderer.plot_overfit_dashboard(
                self._overfit_results,
                pbo_results=self._pbo_result,
                wf_results=self._wf_result,
                save_path=save_path,
            )
        ]

    def analyze(
        self,
        n_reps: int | None = None,
        run_pbo: bool = True,
        run_walkforward: bool = True,
        run_tracker: bool = True,
        visualize: bool = True,
        save_path: str | None = None,
    ) -> SignalAnalysisReport:
        """Run the full signal-analysis pipeline and return a report."""
        self.run_detector(n_reps=n_reps)
        self.compute_psr_dsr()
        if run_pbo and self.total_combinations >= 4:
            self.compute_pbo()
        if run_walkforward:
            self.compute_walkforward()
        if run_tracker:
            self.run_trial_tracker()

        figures = self.visualize(save_path=save_path) if visualize else []
        verdict, confidence = self._synthesize_verdict()

        return SignalAnalysisReport(
            strategy_name=self.strategy_name,
            n_signals=self.n_signals,
            signal_names=self.signal_names,
            total_combinations=self.total_combinations,
            overfit_results=self._overfit_results,
            psr_result=self._psr_result,
            dsr_result=self._dsr_result,
            pbo_result=self._pbo_result,
            wf_result=self._wf_result,
            trial_tracker=self._tracker,
            figures=figures,
            verdict=verdict,
            confidence=confidence,
        )

    def _synthesize_verdict(self) -> tuple[str, float]:  # noqa: C901
        """Combine all test results into one verdict."""
        votes: list[tuple[float, float]] = []

        if self._overfit_results:
            result = self._overfit_results
            if result.unbiased_pvalue < 0.05:
                votes.append((1.0, 3.0))
            elif result.unbiased_pvalue < 0.10:
                votes.append((0.6, 2.0))
            else:
                votes.append((0.0, 3.0))

            if result.deflated_sharpe > 2.0:
                votes.append((1.0, 1.0))
            elif result.deflated_sharpe > 1.0:
                votes.append((0.5, 1.0))
            else:
                votes.append((0.0, 1.0))

        if self._dsr_result:
            votes.append((1.0, 2.0) if self._dsr_result.is_significant else (0.0, 2.0))

        if self._pbo_result:
            pbo = self._pbo_result.pbo
            if pbo < 0.1:
                votes.append((1.0, 2.0))
            elif pbo < 0.3:
                votes.append((0.6, 2.0))
            elif pbo < 0.5:
                votes.append((0.3, 2.0))
            else:
                votes.append((0.0, 2.0))

        if self._wf_result:
            wfe = self._wf_result.wfe
            if wfe >= 0.7:
                votes.append((1.0, 2.0))
            elif wfe >= 0.5:
                votes.append((0.6, 2.0))
            elif wfe >= 0.3:
                votes.append((0.3, 2.0))
            else:
                votes.append((0.0, 2.0))
            if self._wf_result.vetoed:
                votes.append((0.0, 3.0))

        if self._overfit_results:
            surface = self._overfit_results.surface_analysis()
            if surface["plateau_score"] > 0.2:
                votes.append((1.0, 1.0))
            elif surface["plateau_score"] > 0.05:
                votes.append((0.5, 1.0))
            else:
                votes.append((0.0, 1.0))

        if not votes:
            return "INSUFFICIENT DATA", 0.0

        total_weight = sum(weight for _, weight in votes)
        weighted_score = sum(score * weight for score, weight in votes) / total_weight

        if weighted_score >= 0.75:
            verdict = "GENUINE SIGNAL - proceed with caution"
        elif weighted_score >= 0.5:
            verdict = "MARGINAL - needs more data or fewer parameters"
        elif weighted_score >= 0.25:
            verdict = "LIKELY OVERFIT - high risk of curve fitting"
        else:
            verdict = "OVERFIT - almost certainly noise mining"
        return verdict, weighted_score
