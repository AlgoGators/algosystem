"""In-memory backtest run repository."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Dict, Iterable, Mapping, Optional, Sequence

import pandas as pd

from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.domain.metrics import PerformanceMetrics
from algosystem.backtesting.domain.ports import RunSummary
from algosystem.shared.errors import DuplicateRunError, RepositoryError, RunNotFoundError
from algosystem.shared.metric_key import MetricKey
from algosystem.shared.values import DateRange, Money, Percent, RunId


@dataclass(frozen=True)
class _Metadata:
    name: str
    description: str
    hyperparameters: Optional[dict[str, object]]
    date_inserted: datetime


class InMemoryBacktestRunRepository:
    """Dictionary-backed repository with production-equivalent semantics."""

    def __init__(self) -> None:
        self._runs: Dict[str, BacktestResult] = {}
        self._metadata: Dict[str, _Metadata] = {}

    def save(
        self,
        result: BacktestResult,
        overwrite: bool = False,
        name: Optional[str] = None,
        description: str = "",
        hyperparameters: Optional[Mapping[str, object]] = None,
    ) -> RunId:
        """Persist a result in memory."""
        assigned_run_id = result.run_id or RunId.generate()
        run_id = assigned_run_id.value
        if run_id in self._runs and not overwrite:
            raise DuplicateRunError(run_id)

        result_to_store = replace(result, run_id=assigned_run_id)
        self._runs[run_id] = _clone_result(result_to_store)
        self._metadata[run_id] = _Metadata(
            name=name or run_id,
            description=description,
            hyperparameters=dict(hyperparameters) if hyperparameters is not None else None,
            date_inserted=datetime.utcnow(),
        )
        return assigned_run_id

    def get(self, run_id: RunId) -> BacktestResult:
        """Load a stored result."""
        run_id_value = _run_id_value(run_id)
        try:
            result = self._runs[run_id_value]
        except KeyError as exc:
            raise RunNotFoundError(run_id_value) from exc
        return _clone_result(result)

    def delete(self, run_id: RunId) -> None:
        """Delete a stored result."""
        run_id_value = _run_id_value(run_id)
        if run_id_value not in self._runs:
            raise RunNotFoundError(run_id_value)
        del self._runs[run_id_value]
        del self._metadata[run_id_value]

    def list_runs(self, limit: int, offset: int) -> list[RunSummary]:
        """List stored runs newest first."""
        self._validate_page(limit, offset)
        run_ids = self._ordered_run_ids()
        return [self._summary(self._runs[run_id]) for run_id in run_ids[offset : offset + limit]]

    def find_best(self, metric: MetricKey, limit: int) -> list[RunSummary]:
        """Find runs sorted by a metric."""
        if limit < 1:
            raise RepositoryError("limit must be positive")
        metric_key = _coerce_metric_key(metric)
        candidates = [
            result for result in self._runs.values() if result.metrics.get(metric_key) is not None
        ]
        candidates.sort(
            key=lambda result: result.metrics.get(metric_key),
            reverse=not _sorts_ascending(metric_key),
        )
        return [self._summary(result) for result in candidates[:limit]]

    def search(self, query: str, field: str) -> list[RunSummary]:
        """Search runs by case-insensitive substring on a supported field."""
        needle = str(query).lower()
        matches = [
            result
            for result in self._runs.values()
            if needle in self._search_value(result, field).lower()
        ]
        matches.sort(
            key=lambda result: self._metadata[_require_run_id(result).value].date_inserted,
            reverse=True,
        )
        return [self._summary(result) for result in matches]

    def get_backtest_stats(self) -> dict[str, object]:
        """Return aggregate statistics for stored runs."""
        stats: dict[str, object] = {
            "total_backtests": len(self._runs),
            "unique_names": len({metadata.name for metadata in self._metadata.values()}),
            "equity_curve_records": sum(len(result.equity_curve) for result in self._runs.values()),
            "position_records": 0,
            "pnl_records": 0,
        }
        if self._metadata:
            inserted = [metadata.date_inserted for metadata in self._metadata.values()]
            first_date = min(inserted)
            last_date = max(inserted)
            stats["first_backtest"] = first_date
            stats["last_backtest"] = last_date
            stats["days_span"] = (last_date - first_date).days

        total_returns = _metric_values(self._runs.values(), MetricKey.TOTAL_RETURN)
        sharpe_ratios = _metric_values(self._runs.values(), MetricKey.SHARPE_RATIO)
        drawdowns = _metric_values(self._runs.values(), MetricKey.MAX_DRAWDOWN)
        if total_returns:
            stats["avg_return"] = sum(total_returns) / len(total_returns)
            stats["min_return"] = min(total_returns)
            stats["max_return"] = max(total_returns)
            stats["avg_sharpe"] = sum(sharpe_ratios) / len(sharpe_ratios) if sharpe_ratios else None
            stats["avg_drawdown"] = sum(drawdowns) / len(drawdowns) if drawdowns else None
        return stats

    def compare_backtests(self, run_ids: Sequence[object]) -> dict[str, object]:
        """Compare selected runs and return summary rows plus equity curves."""
        if not run_ids:
            raise RepositoryError("No run IDs provided for comparison")

        rows = []
        equity_curves = {}
        for run_id in run_ids:
            run_id_value = _run_id_value(run_id)
            result = self._runs.get(run_id_value)
            if result is None:
                continue
            metadata = self._metadata[run_id_value]
            rows.append(
                {
                    "run_id": run_id_value,
                    "name": metadata.name,
                    "date_inserted": metadata.date_inserted,
                    MetricKey.TOTAL_RETURN.value: result.metrics.get(MetricKey.TOTAL_RETURN),
                    MetricKey.SHARPE_RATIO.value: result.metrics.get(MetricKey.SHARPE_RATIO),
                    MetricKey.MAX_DRAWDOWN.value: result.metrics.get(MetricKey.MAX_DRAWDOWN),
                    MetricKey.BETA.value: result.metrics.get(MetricKey.BETA),
                }
            )
            equity_curves[run_id_value] = result.equity_curve.values.copy()

        if not rows:
            raise RepositoryError("No matching backtests found with the provided run IDs")
        rows.sort(key=lambda row: row["date_inserted"], reverse=True)
        return {"backtests": rows, "equity_curves": equity_curves}

    def get_backtest_summary(self, run_id: object) -> Optional[dict[str, object]]:
        """Return a dictionary summary for a run, or None if it is missing."""
        run_id_value = _run_id_value(run_id)
        result = self._runs.get(run_id_value)
        if result is None:
            return None
        metadata = self._metadata[run_id_value]
        summary = {
            "run_id": run_id_value,
            "name": metadata.name,
            "description": metadata.description,
            "hyperparameters": metadata.hyperparameters,
            "date_inserted": metadata.date_inserted,
            "start_date": result.date_range.start.date(),
            "end_date": result.date_range.end.date(),
            "config": None,
            "initial_capital": result.initial_capital.amount,
            "final_capital": result.final_capital.amount,
            "equity_points": len(result.equity_curve),
            "position_count": 0,
            "symbol_pnl_count": 0,
        }
        summary.update(result.metrics.to_dict())
        return summary

    def get_equity_curve(self, run_id: object) -> Optional[pd.Series]:
        """Return a copy of a run's equity curve, or None if it is missing."""
        run_id_value = _run_id_value(run_id)
        result = self._runs.get(run_id_value)
        if result is None:
            return None
        return result.equity_curve.values.copy()

    def _ordered_run_ids(self) -> list[str]:
        return sorted(
            self._runs,
            key=lambda run_id: self._metadata[run_id].date_inserted,
            reverse=True,
        )

    def _summary(self, result: BacktestResult) -> RunSummary:
        return RunSummary(
            run_id=_require_run_id(result),
            date_range=result.date_range,
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            total_return=result.total_return,
            metrics=result.metrics,
        )

    def _search_value(self, result: BacktestResult, field: str) -> str:
        run_id = _require_run_id(result)
        metadata = self._metadata[run_id.value]
        if field == "run_id":
            return run_id.value
        if field == "name":
            return metadata.name
        if field == "description":
            return metadata.description
        if field == "start_date":
            return str(result.date_range.start.date())
        if field == "end_date":
            return str(result.date_range.end.date())
        if field == "initial_capital":
            return str(result.initial_capital.amount)
        if field == "final_capital":
            return str(result.final_capital.amount)
        if field == MetricKey.TOTAL_RETURN.value:
            return str(result.total_return.as_fraction)
        try:
            metric_key = MetricKey(field)
        except ValueError as exc:
            raise RepositoryError(f"unsupported search field: {field}") from exc
        value = result.metrics.get(metric_key)
        return "" if value is None else str(value)

    @staticmethod
    def _validate_page(limit: int, offset: int) -> None:
        if limit < 1:
            raise RepositoryError("limit must be positive")
        if offset < 0:
            raise RepositoryError("offset must be non-negative")


def _clone_result(result: BacktestResult) -> BacktestResult:
    return BacktestResult(
        equity_curve=EquityCurve.from_series(result.equity_curve.values.copy()),
        benchmark_curve=(
            EquityCurve.from_series(result.benchmark_curve.values.copy())
            if result.benchmark_curve is not None
            else None
        ),
        metrics=PerformanceMetrics.from_dict(result.metrics.to_dict()),
        date_range=DateRange(result.date_range.start, result.date_range.end),
        initial_capital=Money(result.initial_capital.amount, result.initial_capital.currency),
        final_capital=Money(result.final_capital.amount, result.final_capital.currency),
        total_return=Percent(result.total_return.as_fraction),
        run_id=RunId(result.run_id.value) if result.run_id is not None else None,
    )


def _coerce_metric_key(metric: MetricKey) -> MetricKey:
    if not isinstance(metric, MetricKey):
        raise RepositoryError("metric must be a MetricKey")
    return metric


def _metric_values(results: Iterable[BacktestResult], metric_key: MetricKey) -> list[float]:
    values = []
    for result in results:
        value = result.metrics.get(metric_key)
        if value is not None:
            values.append(value)
    return values


def _run_id_value(run_id: object) -> str:
    if isinstance(run_id, RunId):
        return run_id.value
    return str(run_id)


def _require_run_id(result: BacktestResult) -> RunId:
    if result.run_id is None:
        raise RepositoryError("persisted backtest result is missing a run id")
    return result.run_id


def _sorts_ascending(metric_key: MetricKey) -> bool:
    return metric_key in {
        MetricKey.MAX_DRAWDOWN,
        MetricKey.ANNUALIZED_VOLATILITY,
        MetricKey.MONTHLY_VOLATILITY,
    }
