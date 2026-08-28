"""PostgreSQL backtest run repository."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Mapping, Optional, Sequence

import pandas as pd
from sqlalchemy import cast, create_engine, delete, func, insert, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import String as SqlString

from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.domain.metrics import PerformanceMetrics
from algosystem.backtesting.domain.ports import RunSummary
from algosystem.shared.errors import DuplicateRunError, RepositoryError, RunNotFoundError
from algosystem.shared.metric_key import MetricKey
from algosystem.shared.values import DateRange, Money, Percent, RunId

from . import schema
from .config import DatabaseConfig


class PostgresBacktestRunRepository:
    """SQLAlchemy-backed repository for persisted backtest runs."""

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self.engine = create_engine(config.url(), pool_size=config.pool_size)
        self._engine = self.engine.execution_options(
            schema_translate_map={schema.DEFAULT_SCHEMA: config.schema}
        )

    def save(
        self,
        result: BacktestResult,
        overwrite: bool = False,
        name: Optional[str] = None,
        description: str = "",
        hyperparameters: Optional[Mapping[str, object]] = None,
    ) -> RunId:
        """Persist a result to Postgres."""
        assigned_run_id = result.run_id or RunId.generate()
        run_id = assigned_run_id.value
        result_to_save = replace(result, run_id=assigned_run_id)
        try:
            with self._engine.begin() as connection:
                exists = self._run_exists(connection, run_id)
                if exists and not overwrite:
                    raise DuplicateRunError(run_id)
                if exists:
                    self._delete_run(connection, run_id)
                self._insert_result(
                    connection,
                    result_to_save,
                    name=name or run_id,
                    description=description,
                    hyperparameters=hyperparameters,
                )
            return assigned_run_id
        except DuplicateRunError:
            raise
        except IntegrityError as exc:
            raise DuplicateRunError(run_id) from exc
        except Exception as exc:
            raise RepositoryError("failed to save backtest run") from exc

    def get(self, run_id: RunId) -> BacktestResult:
        """Load a run from Postgres."""
        run_id_value = _run_id_value(run_id)
        try:
            with self._engine.connect() as connection:
                return self._load_result(connection, run_id_value)
        except RunNotFoundError:
            raise
        except Exception as exc:
            raise RepositoryError("failed to load backtest run") from exc

    def delete(self, run_id: RunId) -> None:
        """Delete a run from Postgres."""
        run_id_value = _run_id_value(run_id)
        try:
            with self._engine.begin() as connection:
                if not self._run_exists(connection, run_id_value):
                    raise RunNotFoundError(run_id_value)
                self._delete_run(connection, run_id_value)
        except RunNotFoundError:
            raise
        except Exception as exc:
            raise RepositoryError("failed to delete backtest run") from exc

    def list_runs(self, limit: int, offset: int) -> list[RunSummary]:
        """List saved runs newest first."""
        _validate_page(limit, offset)
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    select(schema.RunMetadata.run_id)
                    .order_by(schema.RunMetadata.date_inserted.desc())
                    .limit(limit)
                    .offset(offset)
                ).fetchall()
                return [self._load_summary(connection, row._mapping["run_id"]) for row in rows]
        except Exception as exc:
            raise RepositoryError("failed to list backtest runs") from exc

    def find_best(self, metric: MetricKey, limit: int) -> list[RunSummary]:
        """Find runs sorted by a MetricKey."""
        if limit < 1:
            raise RepositoryError("limit must be positive")
        metric_key = _coerce_metric_key(metric)
        metric_column = getattr(schema.Result, metric_key.value)
        order_clause = metric_column.asc() if _sorts_ascending(metric_key) else metric_column.desc()
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    select(schema.Result.run_id)
                    .where(metric_column.isnot(None))
                    .order_by(order_clause)
                    .limit(limit)
                ).fetchall()
                return [self._load_summary(connection, row._mapping["run_id"]) for row in rows]
        except Exception as exc:
            raise RepositoryError("failed to find best backtest runs") from exc

    def search(self, query: str, field: str) -> list[RunSummary]:
        """Search runs by case-insensitive substring."""
        search_column = _search_column(field)
        pattern = f"%{query}%"
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    select(schema.RunMetadata.run_id)
                    .select_from(schema.RunMetadata)
                    .join(
                        schema.Result,
                        schema.RunMetadata.run_id == schema.Result.run_id,
                        isouter=True,
                    )
                    .where(cast(search_column, SqlString).ilike(pattern))
                    .order_by(schema.RunMetadata.date_inserted.desc())
                ).fetchall()
                return [self._load_summary(connection, row._mapping["run_id"]) for row in rows]
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError("failed to search backtest runs") from exc

    def get_backtest_stats(self) -> dict[str, object]:
        """Return aggregate database statistics."""
        try:
            with self._engine.connect() as connection:
                stats: dict[str, object] = {}
                stats["total_backtests"] = connection.execute(
                    select(func.count()).select_from(schema.RunMetadata)
                ).scalar_one()
                stats["unique_names"] = connection.execute(
                    select(func.count(func.distinct(schema.RunMetadata.name)))
                ).scalar_one()

                first_date, last_date = connection.execute(
                    select(
                        func.min(schema.RunMetadata.date_inserted),
                        func.max(schema.RunMetadata.date_inserted),
                    )
                ).one()
                if first_date is not None and last_date is not None:
                    stats["first_backtest"] = first_date
                    stats["last_backtest"] = last_date
                    stats["days_span"] = (last_date - first_date).days

                stats["equity_curve_records"] = connection.execute(
                    select(func.count()).select_from(schema.EquityCurve)
                ).scalar_one()
                stats["position_records"] = connection.execute(
                    select(func.count()).select_from(schema.FinalPosition)
                ).scalar_one()
                stats["pnl_records"] = connection.execute(
                    select(func.count()).select_from(schema.SymbolPnl)
                ).scalar_one()

                total_return = getattr(schema.Result, MetricKey.TOTAL_RETURN.value)
                sharpe_ratio = getattr(schema.Result, MetricKey.SHARPE_RATIO.value)
                max_drawdown = getattr(schema.Result, MetricKey.MAX_DRAWDOWN.value)
                row = connection.execute(
                    select(
                        func.avg(total_return),
                        func.min(total_return),
                        func.max(total_return),
                        func.avg(sharpe_ratio),
                        func.avg(max_drawdown),
                    ).where(total_return.isnot(None))
                ).one()
                avg_return, min_return, max_return, avg_sharpe, avg_drawdown = row
                if avg_return is not None:
                    stats["avg_return"] = float(avg_return)
                    stats["min_return"] = float(min_return)
                    stats["max_return"] = float(max_return)
                    stats["avg_sharpe"] = float(avg_sharpe) if avg_sharpe is not None else None
                    stats["avg_drawdown"] = (
                        float(avg_drawdown) if avg_drawdown is not None else None
                    )
                return stats
        except Exception as exc:
            raise RepositoryError("failed to get backtest stats") from exc

    def compare_backtests(self, run_ids: Sequence[object]) -> dict[str, object]:
        """Compare selected runs using parameterized SQLAlchemy clauses."""
        if not run_ids:
            raise RepositoryError("No run IDs provided for comparison")
        run_id_values = [_run_id_value(run_id) for run_id in run_ids]
        try:
            with self._engine.connect() as connection:
                rows = connection.execute(
                    select(
                        schema.RunMetadata.run_id,
                        schema.RunMetadata.name,
                        schema.RunMetadata.date_inserted,
                        getattr(schema.Result, MetricKey.TOTAL_RETURN.value).label(
                            MetricKey.TOTAL_RETURN.value
                        ),
                        getattr(schema.Result, MetricKey.SHARPE_RATIO.value).label(
                            MetricKey.SHARPE_RATIO.value
                        ),
                        getattr(schema.Result, MetricKey.MAX_DRAWDOWN.value).label(
                            MetricKey.MAX_DRAWDOWN.value
                        ),
                        getattr(schema.Result, MetricKey.BETA.value).label(MetricKey.BETA.value),
                    )
                    .select_from(schema.RunMetadata)
                    .join(schema.Result, schema.RunMetadata.run_id == schema.Result.run_id)
                    .where(schema.RunMetadata.run_id.in_(run_id_values))
                    .order_by(schema.RunMetadata.date_inserted.desc())
                ).fetchall()
                if not rows:
                    raise RepositoryError("No matching backtests found with the provided run IDs")

                backtests = [dict(row._mapping) for row in rows]
                equity_curves = {}
                for run_id_value in run_id_values:
                    equity_curve = self._load_equity_series(connection, run_id_value)
                    if equity_curve is not None:
                        equity_curves[run_id_value] = equity_curve
                return {"backtests": backtests, "equity_curves": equity_curves}
        except RepositoryError:
            raise
        except Exception as exc:
            raise RepositoryError("failed to compare backtests") from exc

    def get_backtest_summary(self, run_id: object) -> Optional[dict[str, object]]:
        """Return a full dictionary summary for a run."""
        run_id_value = _run_id_value(run_id)
        try:
            with self._engine.connect() as connection:
                metadata = connection.execute(
                    select(schema.RunMetadata.__table__).where(
                        schema.RunMetadata.run_id == run_id_value
                    )
                ).first()
                if metadata is None:
                    return None
                result = connection.execute(
                    select(schema.Result.__table__).where(schema.Result.run_id == run_id_value)
                ).first()
                summary = dict(metadata._mapping)
                if result is not None:
                    summary.update(dict(result._mapping))
                summary["equity_points"] = connection.execute(
                    select(func.count())
                    .select_from(schema.EquityCurve)
                    .where(schema.EquityCurve.run_id == run_id_value)
                ).scalar_one()
                summary["position_count"] = connection.execute(
                    select(func.count())
                    .select_from(schema.FinalPosition)
                    .where(schema.FinalPosition.run_id == run_id_value)
                ).scalar_one()
                summary["symbol_pnl_count"] = connection.execute(
                    select(func.count())
                    .select_from(schema.SymbolPnl)
                    .where(schema.SymbolPnl.run_id == run_id_value)
                ).scalar_one()
                return summary
        except Exception as exc:
            raise RepositoryError("failed to get backtest summary") from exc

    def get_equity_curve(self, run_id: object) -> Optional[pd.Series]:
        """Return a run's equity curve, or None if it is missing."""
        run_id_value = _run_id_value(run_id)
        try:
            with self._engine.connect() as connection:
                return self._load_equity_series(connection, run_id_value)
        except Exception as exc:
            raise RepositoryError("failed to get equity curve") from exc

    def _insert_result(
        self,
        connection: Connection,
        result: BacktestResult,
        name: str,
        description: str,
        hyperparameters: Optional[Mapping[str, object]],
    ) -> None:
        run_id = _require_run_id(result).value
        connection.execute(
            insert(schema.RunMetadata).values(
                run_id=run_id,
                name=name,
                description=description,
                hyperparameters=dict(hyperparameters) if hyperparameters is not None else None,
                date_inserted=datetime.utcnow(),
            )
        )
        result_values = {
            "run_id": run_id,
            "start_date": result.date_range.start.date(),
            "end_date": result.date_range.end.date(),
            "config": None,
        }
        for metric_key in MetricKey:
            result_values[metric_key.value] = result.metrics.get(metric_key)
        connection.execute(insert(schema.Result).values(**result_values))
        equity_rows = [
            {
                "run_id": run_id,
                "timestamp": pd.Timestamp(timestamp).to_pydatetime(),
                "equity": float(equity),
            }
            for timestamp, equity in result.equity_curve.values.items()
        ]
        if equity_rows:
            connection.execute(insert(schema.EquityCurve), equity_rows)

    def _load_result(self, connection: Connection, run_id: str) -> BacktestResult:
        result_row = connection.execute(
            select(schema.Result.__table__).where(schema.Result.run_id == run_id)
        ).first()
        if result_row is None:
            raise RunNotFoundError(run_id)
        equity_series = self._load_equity_series(connection, run_id)
        if equity_series is None:
            raise RepositoryError(f"persisted run has no equity curve: {run_id}")

        metrics = PerformanceMetrics.from_dict(
            {
                metric_key: result_row._mapping[metric_key.value]
                for metric_key in MetricKey
                if result_row._mapping[metric_key.value] is not None
            }
        )
        initial_capital = Money(float(equity_series.iloc[0]))
        final_capital = Money(float(equity_series.iloc[-1]))
        total_return_value = metrics.get(MetricKey.TOTAL_RETURN)
        if total_return_value is None:
            total_return_value = (final_capital.amount - initial_capital.amount) / (
                initial_capital.amount
            )
        return BacktestResult(
            run_id=RunId(run_id),
            equity_curve=EquityCurve.from_series(equity_series),
            benchmark_curve=None,
            metrics=metrics,
            date_range=DateRange(
                result_row._mapping["start_date"], result_row._mapping["end_date"]
            ),
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=Percent(total_return_value),
        )

    def _load_summary(self, connection: Connection, run_id: str) -> RunSummary:
        result = self._load_result(connection, run_id)
        return RunSummary(
            run_id=result.run_id,
            date_range=result.date_range,
            initial_capital=result.initial_capital,
            final_capital=result.final_capital,
            total_return=result.total_return,
            metrics=result.metrics,
        )

    def _load_equity_series(self, connection: Connection, run_id: str) -> Optional[pd.Series]:
        rows = connection.execute(
            select(schema.EquityCurve.timestamp, schema.EquityCurve.equity)
            .where(schema.EquityCurve.run_id == run_id)
            .order_by(schema.EquityCurve.timestamp)
        ).fetchall()
        if not rows:
            return None
        data = [(row._mapping["timestamp"], row._mapping["equity"]) for row in rows]
        timestamps = [timestamp for timestamp, _ in data]
        values = [float(value) for _, value in data]
        return pd.Series(values, index=pd.DatetimeIndex(timestamps), name="equity")

    def _run_exists(self, connection: Connection, run_id: str) -> bool:
        return (
            connection.execute(
                select(schema.RunMetadata.run_id).where(schema.RunMetadata.run_id == run_id)
            ).first()
            is not None
        )

    def _delete_run(self, connection: Connection, run_id: str) -> None:
        for table in (
            schema.EquityCurve,
            schema.FinalPosition,
            schema.SymbolPnl,
            schema.Result,
            schema.RunMetadata,
        ):
            connection.execute(delete(table).where(table.run_id == run_id))


def _coerce_metric_key(metric: MetricKey) -> MetricKey:
    if not isinstance(metric, MetricKey):
        raise RepositoryError("metric must be a MetricKey")
    return metric


def _run_id_value(run_id: object) -> str:
    if isinstance(run_id, RunId):
        return run_id.value
    return str(run_id)


def _require_run_id(result: BacktestResult) -> RunId:
    if result.run_id is None:
        raise RepositoryError("persisted backtest result is missing a run id")
    return result.run_id


def _search_column(field: str) -> object:
    metadata_columns = {
        "run_id": schema.RunMetadata.run_id,
        "name": schema.RunMetadata.name,
        "description": schema.RunMetadata.description,
    }
    if field in metadata_columns:
        return metadata_columns[field]

    result_columns = {
        "start_date": schema.Result.start_date,
        "end_date": schema.Result.end_date,
    }
    if field in result_columns:
        return result_columns[field]

    try:
        metric_key = MetricKey(field)
    except ValueError as exc:
        raise RepositoryError(f"unsupported search field: {field}") from exc
    return getattr(schema.Result, metric_key.value)


def _sorts_ascending(metric_key: MetricKey) -> bool:
    return metric_key in {
        MetricKey.MAX_DRAWDOWN,
        MetricKey.ANNUALIZED_VOLATILITY,
        MetricKey.MONTHLY_VOLATILITY,
    }


def _validate_page(limit: int, offset: int) -> None:
    if limit < 1:
        raise RepositoryError("limit must be positive")
    if offset < 0:
        raise RepositoryError("offset must be non-negative")
