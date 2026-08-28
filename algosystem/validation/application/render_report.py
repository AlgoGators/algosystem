"""Render validation reports through an injected report renderer."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from algosystem.validation.domain.ports import ReportRenderer


class RenderValidationReport:
    """Use case for rendering validation reports."""

    def __init__(self, renderer: ReportRenderer) -> None:
        self._renderer = renderer

    def execute(
        self,
        results: object,
        output: Path,
        *,
        pbo_results: object | None = None,
        wf_results: object | None = None,
        ac_diagnostic: object | None = None,
        robustness: Mapping[str, object] | None = None,
        title: str = "Overfitting Detection Report",
        open_browser: bool = False,
    ) -> Path:
        """Render a validation report and return the output path."""
        return self._renderer.render(
            results,
            output_path=output,
            pbo_results=pbo_results,
            wf_results=wf_results,
            ac_diagnostic=ac_diagnostic,
            robustness=robustness,
            title=title,
            open_browser=open_browser,
        )
