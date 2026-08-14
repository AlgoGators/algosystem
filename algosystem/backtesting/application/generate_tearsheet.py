"""Generate-tearsheet use case."""

from __future__ import annotations

from pathlib import Path

from algosystem.backtesting.domain.ports import TearsheetRenderer

from .dto import GenerateTearsheetRequest, GenerateTearsheetResponse


class GenerateTearsheet:
    """Use case for rendering a backtest tearsheet."""

    def __init__(self, renderer: TearsheetRenderer) -> None:
        self._renderer = renderer

    def execute(self, request: GenerateTearsheetRequest) -> GenerateTearsheetResponse:
        """Render a tearsheet through the injected renderer port."""
        output = self._renderer.render(
            request.result,
            output_path=Path(request.output),
            title=request.title,
            mode=request.mode,
            rf=request.rf,
            periods_per_year=request.periods_per_year,
        )
        return GenerateTearsheetResponse(output=output)
