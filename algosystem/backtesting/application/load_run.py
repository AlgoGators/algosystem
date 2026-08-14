"""Load-run use case."""

from __future__ import annotations

from algosystem.backtesting.domain.ports import BacktestRunRepository
from algosystem.shared.values import RunId

from .dto import LoadRunRequest, LoadRunResponse


class LoadRun:
    """Use case for loading a persisted backtest run."""

    def __init__(self, repository: BacktestRunRepository) -> None:
        self._repository = repository

    def execute(self, request: LoadRunRequest) -> LoadRunResponse:
        """Load and return a persisted backtest result."""
        return LoadRunResponse(result=self._repository.get(_coerce_run_id(request.run_id)))


def _coerce_run_id(run_id: object) -> RunId:
    if isinstance(run_id, RunId):
        return run_id
    return RunId(str(run_id))
