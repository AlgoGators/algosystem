"""Archive-run use case."""

from __future__ import annotations

from algosystem.backtesting.domain.ports import BacktestRunRepository

from .dto import ArchiveRunRequest, ArchiveRunResponse


class ArchiveRun:
    """Use case for persisting a completed backtest run."""

    def __init__(self, repository: BacktestRunRepository) -> None:
        self._repository = repository

    def execute(self, request: ArchiveRunRequest) -> ArchiveRunResponse:
        """Persist a backtest result and return its assigned run id."""
        run_id = self._repository.save(
            request.result,
            overwrite=request.overwrite,
            name=request.name,
            description=request.description,
            hyperparameters=request.hyperparameters,
        )
        return ArchiveRunResponse(run_id=run_id)
