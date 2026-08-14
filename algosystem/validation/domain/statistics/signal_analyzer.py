"""Signal analysis result objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SignalAnalysisReport:
    """Complete analysis of a strategy's signal parameter space."""

    strategy_name: str
    n_signals: int
    signal_names: list[str]
    total_combinations: int
    overfit_results: Any = None
    psr_result: Any = None
    dsr_result: Any = None
    pbo_result: Any = None
    wf_result: Any = None
    trial_tracker: Any = None
    figures: list[object] = field(default_factory=list)
    verdict: str = ""
    confidence: float = 0.0

    def summary(self) -> list[str]:
        """Return all result summaries as formatted lines."""
        lines = [
            "=" * 72,
            f"SIGNAL ANALYSIS: {self.strategy_name}",
            f"  Signals: {self.n_signals} ({', '.join(self.signal_names)})",
            f"  Combinations: {self.total_combinations:,}",
            "=" * 72,
        ]

        if self.overfit_results:
            lines.append("")
            lines.extend(self.overfit_results.summary())
            lines.extend(self.overfit_results.surface_summary())

        if self.psr_result:
            lines.append("")
            lines.extend(self.psr_result.summary())

        if self.dsr_result:
            lines.append("")
            lines.extend(self.dsr_result.summary())

        if self.pbo_result:
            lines.append("")
            lines.extend(self.pbo_result.summary().splitlines())

        if self.wf_result:
            lines.append("")
            lines.extend(self.wf_result.summary())

        if self.trial_tracker:
            lines.append("")
            lines.extend(self.trial_tracker.summary())

        lines.extend(
            [
                "",
                "=" * 72,
                f"VERDICT: {self.verdict}",
                f"CONFIDENCE: {self.confidence:.1%}",
                "=" * 72,
            ]
        )
        return lines

    def artifact_summary(self) -> dict[str, Any]:
        """Return renderable report data without writing files."""
        return {
            "report_lines": self.summary(),
            "figure_count": len([fig for fig in self.figures if fig is not None]),
        }
