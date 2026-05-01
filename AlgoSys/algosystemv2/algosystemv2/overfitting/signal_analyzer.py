"""
Signal Analyzer — connects strategies with N signals to the overfitting
detection pipeline and routes to the appropriate visualization.

This is the "place a strategy with 3 signals and get a 3D graph" entry point.

Usage:
    from algosystemv2.overfitting.signal_analyzer import SignalAnalyzer

    analyzer = SignalAnalyzer(
        backtest_fn=my_strategy,
        returns=daily_returns,
        signal_params={
            'fast_lookback': [5, 10, 15, 20],
            'slow_lookback': [30, 40, 60, 80],
            'threshold': [0.0, 0.001, 0.002],
        },
    )

    # Run full analysis: permutation test + PSR/DSR + visualization
    report = analyzer.analyze()
    report.show()           # Opens interactive plots
    report.save('output/')  # Saves all artifacts

    # Or step by step:
    analyzer.run_detector(n_reps=500)
    analyzer.compute_psr_dsr()
    analyzer.compute_pbo()
    analyzer.visualize()    # Auto-picks 3D for 3 signals
"""

from __future__ import annotations

import itertools
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np


@dataclass
class SignalAnalysisReport:
    """Complete analysis of a strategy's signal parameter space."""

    # Strategy metadata
    strategy_name: str
    n_signals: int
    signal_names: list[str]
    total_combinations: int

    # Core results (from OverfitDetector)
    overfit_results: Any = None       # OverfitResults

    # PSR/DSR results
    psr_result: Any = None            # PSRResult
    dsr_result: Any = None            # DSRResult

    # PBO results
    pbo_result: Any = None            # PBOResults

    # Walk-forward results
    wf_result: Any = None             # WalkForwardResults

    # Trial tracker
    trial_tracker: Any = None         # TrialTracker

    # Visualization figures
    figures: list = field(default_factory=list)

    # Verdict
    verdict: str = ''
    confidence: float = 0.0

    def show(self):
        """Display all results and open interactive plots."""
        print("=" * 72)
        print(f"SIGNAL ANALYSIS: {self.strategy_name}")
        print(f"  Signals: {self.n_signals} ({', '.join(self.signal_names)})")
        print(f"  Combinations: {self.total_combinations:,}")
        print("=" * 72)

        if self.overfit_results:
            print()
            self.overfit_results.report()
            self.overfit_results.surface_report()

        if self.psr_result:
            print()
            self.psr_result.report()

        if self.dsr_result:
            print()
            self.dsr_result.report()

        if self.pbo_result:
            print()
            print(self.pbo_result.summary())

        if self.wf_result:
            print()
            self.wf_result.report()

        if self.trial_tracker:
            print()
            self.trial_tracker.report()

        print()
        print("=" * 72)
        print(f"VERDICT: {self.verdict}")
        print(f"CONFIDENCE: {self.confidence:.1%}")
        print("=" * 72)

    def save(self, output_dir: str):
        """Save all artifacts to the given directory."""
        import os
        os.makedirs(output_dir, exist_ok=True)

        # Save figures
        for i, fig in enumerate(self.figures):
            if fig is None:
                continue
            if hasattr(fig, 'write_html'):
                fig.write_html(os.path.join(output_dir, f'signal_viz_{i}.html'))
            elif hasattr(fig, 'savefig'):
                fig.savefig(os.path.join(output_dir, f'signal_viz_{i}.png'),
                           dpi=150, bbox_inches='tight')

        # Save text report
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.show()
        report_path = os.path.join(output_dir, 'signal_analysis_report.txt')
        with open(report_path, 'w') as f:
            f.write(buf.getvalue())
        print(f"Report saved to {output_dir}/")


class SignalAnalyzer:
    """
    Analyze a strategy with N signal parameters for overfitting.

    Connects the parameter grid to:
    1. Permutation-based overfitting detection (OverfitDetector)
    2. Probabilistic & Deflated Sharpe Ratio (PSR/DSR)
    3. Probability of Backtest Overfitting (PBO via CSCV)
    4. Walk-forward analysis
    5. Trial tracking (VARRD-style)
    6. N-dimensional visualization (auto-routed by signal count)
    """

    def __init__(
        self,
        backtest_fn: Callable,
        returns: np.ndarray,
        signal_params: Dict[str, list],
        strategy_name: str = 'strategy',
        n_reps: int = 500,
        shuffle_method: str = 'complete',
        n_workers: int = 1,
        seed: int = 42,
    ):
        self.backtest_fn = backtest_fn
        self.returns = np.asarray(returns, dtype=np.float64)
        self.signal_params = signal_params
        self.strategy_name = strategy_name
        self.n_reps = n_reps
        self.shuffle_method = shuffle_method
        self.n_workers = n_workers
        self.seed = seed

        self.signal_names = sorted(signal_params.keys())
        self.n_signals = len(self.signal_names)

        # Build param list
        keys = self.signal_names
        values = [signal_params[k] for k in keys]
        self._param_list = [
            dict(zip(keys, combo))
            for combo in itertools.product(*values)
        ]
        self.total_combinations = len(self._param_list)

        # Results storage
        self._overfit_results = None
        self._psr_result = None
        self._dsr_result = None
        self._pbo_result = None
        self._wf_result = None
        self._tracker = None

    def run_detector(self, n_reps: int | None = None) -> Any:
        """Run the permutation-based overfitting detector."""
        from .detector import OverfitDetector

        detector = OverfitDetector(
            backtest_fn=self.backtest_fn,
            returns=self.returns,
            param_grid=self.signal_params,
            n_reps=n_reps or self.n_reps,
            shuffle_method=self.shuffle_method,
            n_workers=self.n_workers,
            seed=self.seed,
        )
        self._overfit_results = detector.run()
        return self._overfit_results

    def compute_psr_dsr(self) -> tuple:
        """Compute PSR and DSR for the best strategy."""
        from .psr_dsr import probabilistic_sharpe_ratio, deflated_sharpe_ratio

        if self._overfit_results is None:
            self.run_detector()

        results = self._overfit_results

        self._psr_result = probabilistic_sharpe_ratio(
            self.returns, sr0=0.0,
        )

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

        Builds a proper returns matrix by running each config's backtest
        on each temporal block independently, so that different configs
        have genuinely different temporal profiles.
        """
        from .cscv import compute_pbo

        if self._overfit_results is None:
            self.run_detector()

        n = len(self.returns)
        n_configs = len(self._param_list)
        block_size = n // n_splits
        T_trimmed = block_size * n_splits

        if n_configs > 500:
            print(f"PBO: {n_configs} configs x {n_splits} blocks = "
                  f"{n_configs * n_splits} backtests — this may be slow")

        # Build returns matrix by running each config on each block.
        # For each block, run the backtest on the full data up to that
        # block's end, then extract only that block's contribution.
        # Approximation: run backtest on each block independently and
        # use the per-block Sharpe as a representative performance score.
        returns_matrix = np.zeros((T_trimmed, n_configs))

        for ci, params in enumerate(self._param_list):
            for bi in range(n_splits):
                block_start = bi * block_size
                block_end = block_start + block_size
                block_returns = self.returns[block_start:block_end]

                # Run backtest on this block to get its Sharpe
                block_sharpe = self.backtest_fn(params, block_returns)

                # Use the block's actual returns scaled by relative
                # performance direction (positive Sharpe = long bias,
                # negative = inverted) to create differentiated columns
                # Clamp scale to [-0.9, 5.0] so multiplier stays in [0.05, 3.0]
                # This prevents sign-flipping returns while still
                # differentiating configs by their block-level performance
                if abs(block_sharpe) > 1e-12:
                    scale = np.clip(block_sharpe, -0.9, 5.0)
                else:
                    scale = 0.0
                returns_matrix[block_start:block_end, ci] = block_returns * (0.5 + 0.5 * scale)

        self._pbo_result = compute_pbo(
            returns_matrix, n_splits=n_splits, seed=self.seed,
        )
        return self._pbo_result

    def compute_walkforward(self, n_folds: int = 5, purge_gap: int = 0) -> Any:
        """Run walk-forward analysis."""
        from .walkforward import walk_forward_analysis

        self._wf_result = walk_forward_analysis(
            backtest_fn=self.backtest_fn,
            returns=self.returns,
            param_grid=self.signal_params,
            n_folds=n_folds,
            purge_gap=purge_gap,
        )
        return self._wf_result

    def run_trial_tracker(self) -> Any:
        """Run all parameter combos through the trial tracker.

        Reuses Sharpe ratios from the detector if already computed,
        avoiding redundant backtest runs.
        """
        from .psr_dsr import TrialTracker

        if self._overfit_results is None:
            self.run_detector()

        self._tracker = TrialTracker()
        for i, params in enumerate(self._param_list):
            sharpe = float(self._overfit_results.original_sharpes[i])
            self._tracker.record_trial(
                self.returns, sharpe, params, self.strategy_name,
            )
        return self._tracker

    def visualize(
        self,
        save_path: str | None = None,
        interactive: bool = True,
    ) -> list:
        """
        Generate visualizations auto-routed by signal count.

        1 signal  → 1D sensitivity line
        2 signals → 2D heatmap + 3D surface (z = Sharpe)
        3 signals → 3D volume scatter + slider surface
        4+ signals → Parallel coordinates + pairwise 3D surfaces
        """
        from .nd_visualization import plot_parameter_space

        if self._overfit_results is None:
            self.run_detector()

        figs = plot_parameter_space(
            self._overfit_results,
            params=self.signal_names,
            save_path=save_path,
            interactive=interactive,
        )

        if isinstance(figs, list):
            return figs
        return [figs] if figs is not None else []

    def analyze(
        self,
        n_reps: int | None = None,
        run_pbo: bool = True,
        run_walkforward: bool = True,
        run_tracker: bool = True,
        visualize: bool = True,
        save_path: str | None = None,
    ) -> SignalAnalysisReport:
        """
        Run the full analysis pipeline and return a comprehensive report.

        This is the "one-call" entry point that does everything:
        1. Permutation test
        2. PSR / DSR
        3. PBO (optional)
        4. Walk-forward (optional)
        5. Trial tracker (optional)
        6. Visualization (auto-routed by dimension count)
        7. Verdict synthesis
        """
        print(f"Analyzing {self.strategy_name} with {self.n_signals} signals "
              f"({self.total_combinations:,} combinations)...")
        print()

        # 1. Permutation test
        self.run_detector(n_reps=n_reps)

        # 2. PSR / DSR
        self.compute_psr_dsr()

        # 3. PBO
        if run_pbo and self.total_combinations >= 4:
            try:
                self.compute_pbo()
            except Exception as e:
                print(f"PBO skipped: {e}")

        # 4. Walk-forward
        if run_walkforward:
            try:
                self.compute_walkforward()
            except Exception as e:
                print(f"Walk-forward skipped: {e}")

        # 5. Trial tracker
        if run_tracker:
            self.run_trial_tracker()

        # 6. Visualize
        figures = []
        if visualize:
            figures = self.visualize(save_path=save_path)

        # 7. Synthesize verdict
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

    def _synthesize_verdict(self) -> tuple[str, float]:
        """
        Combine all test results into a single verdict.

        Uses a weighted vote across multiple independent tests.
        """
        votes = []  # (score, weight) where score: 0=overfit, 1=genuine

        # Permutation test
        if self._overfit_results:
            r = self._overfit_results
            if r.unbiased_pvalue < 0.05:
                votes.append((1.0, 3.0))   # strong evidence of signal
            elif r.unbiased_pvalue < 0.10:
                votes.append((0.6, 2.0))   # marginal
            else:
                votes.append((0.0, 3.0))   # no evidence

            # Deflated Sharpe from permutation
            if r.deflated_sharpe > 2.0:
                votes.append((1.0, 1.0))
            elif r.deflated_sharpe > 1.0:
                votes.append((0.5, 1.0))
            else:
                votes.append((0.0, 1.0))

        # DSR
        if self._dsr_result:
            if self._dsr_result.is_significant:
                votes.append((1.0, 2.0))
            else:
                votes.append((0.0, 2.0))

        # PBO
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

        # Walk-forward
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
                votes.append((0.0, 3.0))  # catastrophic veto

        # Surface analysis
        if self._overfit_results:
            sa = self._overfit_results.surface_analysis()
            if sa['plateau_score'] > 0.2:
                votes.append((1.0, 1.0))
            elif sa['plateau_score'] > 0.05:
                votes.append((0.5, 1.0))
            else:
                votes.append((0.0, 1.0))

        if not votes:
            return "INSUFFICIENT DATA", 0.0

        total_weight = sum(w for _, w in votes)
        weighted_score = sum(s * w for s, w in votes) / total_weight

        if weighted_score >= 0.75:
            verdict = "GENUINE SIGNAL — proceed with caution"
        elif weighted_score >= 0.5:
            verdict = "MARGINAL — needs more data or fewer parameters"
        elif weighted_score >= 0.25:
            verdict = "LIKELY OVERFIT — high risk of curve fitting"
        else:
            verdict = "OVERFIT — almost certainly noise mining"

        return verdict, weighted_score
