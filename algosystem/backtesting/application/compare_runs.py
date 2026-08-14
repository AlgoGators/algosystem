"""Compare-runs use case."""

from __future__ import annotations

import pandas as pd

from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.backtesting.domain.ports import BacktestRunRepository
from algosystem.shared.errors import RepositoryError
from algosystem.shared.values import RunId

from .dto import CompareRunsRequest, CompareRunsResponse


class CompareRuns:
    """Use case for comparing persisted runs."""

    def __init__(self, repository: BacktestRunRepository) -> None:
        self._repository = repository

    def execute(self, request: CompareRunsRequest) -> CompareRunsResponse:
        """Load selected runs and return summaries plus aligned equity curves."""
        if not request.run_ids:
            raise RepositoryError("No run IDs provided for comparison")

        results = [self._repository.get(_coerce_run_id(run_id)) for run_id in request.run_ids]
        summaries = [_summary(result) for result in results]
        equity_curves = _aligned_equity_curves(results)
        return CompareRunsResponse(summaries=summaries, equity_curves=equity_curves)


def _summary(result: BacktestResult) -> dict[str, object]:
    summary = result.summary()
    summary.update(result.metrics.to_dict())
    return summary


def _aligned_equity_curves(results: list[BacktestResult]) -> pd.DataFrame:
    columns = {}
    for index, result in enumerate(results):
        if result.run_id is not None:
            name = result.run_id.value
        else:
            name = f"run_{index + 1}"
        columns[name] = result.equity_curve.values.copy()
    return pd.concat(columns, axis=1, join="inner")


def _coerce_run_id(run_id: object) -> RunId:
    if isinstance(run_id, RunId):
        return run_id
    return RunId(str(run_id))
