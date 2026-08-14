import pandas as pd
import pytest

from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.domain.metrics import PerformanceMetrics
from algosystem.backtesting.infrastructure.persistence.in_memory_repository import (
    InMemoryBacktestRunRepository,
)
from algosystem.shared.errors import DuplicateRunError, RunNotFoundError
from algosystem.shared.metric_key import MetricKey
from algosystem.shared.values import Percent, RunId


def make_result(run_id, values, metrics):
    equity_curve = EquityCurve.from_series(
        pd.Series(values, index=pd.date_range("2020-01-01", periods=len(values), freq="D"))
    )
    return BacktestResult(
        run_id=RunId(run_id),
        equity_curve=equity_curve,
        benchmark_curve=None,
        metrics=PerformanceMetrics.from_dict(metrics),
        date_range=equity_curve.date_range,
        initial_capital=equity_curve.initial_value,
        final_capital=equity_curve.final_value,
        total_return=Percent((values[-1] - values[0]) / values[0]),
    )


def test_in_memory_repository_save_get_duplicate_and_overwrite(monkeypatch):
    monkeypatch.delenv("DB_HOST", raising=False)
    repository = InMemoryBacktestRunRepository()
    first = make_result("run-one", [100, 110], {MetricKey.SHARPE_RATIO: 1.0})
    replacement = make_result("run-one", [100, 120], {MetricKey.SHARPE_RATIO: 2.0})

    assert repository.save(first) == RunId("run-one")
    loaded = repository.get(RunId("run-one"))
    assert loaded.run_id == RunId("run-one")
    assert loaded.final_capital.amount == 110.0

    with pytest.raises(DuplicateRunError):
        repository.save(replacement)

    repository.save(replacement, overwrite=True)
    assert repository.get(RunId("run-one")).final_capital.amount == 120.0

    with pytest.raises(RunNotFoundError):
        repository.get(RunId("missing"))


def test_in_memory_repository_find_best_uses_metric_sort_rules():
    repository = InMemoryBacktestRunRepository()
    repository.save(
        make_result(
            "run-a",
            [100, 105],
            {
                MetricKey.SHARPE_RATIO: 1.0,
                MetricKey.MAX_DRAWDOWN: -0.1,
                MetricKey.ANNUALIZED_VOLATILITY: 0.2,
            },
        )
    )
    repository.save(
        make_result(
            "run-b",
            [100, 115],
            {
                MetricKey.SHARPE_RATIO: 2.0,
                MetricKey.MAX_DRAWDOWN: -0.2,
                MetricKey.ANNUALIZED_VOLATILITY: 0.1,
            },
        )
    )

    assert [summary.run_id for summary in repository.find_best(MetricKey.SHARPE_RATIO, 2)] == [
        RunId("run-b"),
        RunId("run-a"),
    ]
    assert [summary.run_id for summary in repository.find_best(MetricKey.MAX_DRAWDOWN, 2)] == [
        RunId("run-b"),
        RunId("run-a"),
    ]
    assert [
        summary.run_id for summary in repository.find_best(MetricKey.ANNUALIZED_VOLATILITY, 2)
    ] == [RunId("run-b"), RunId("run-a")]


def test_in_memory_repository_search_and_compare_are_case_insensitive():
    repository = InMemoryBacktestRunRepository()
    repository.save(
        make_result(
            "Alpha-Run",
            [100, 103],
            {
                MetricKey.TOTAL_RETURN: 0.03,
                MetricKey.SHARPE_RATIO: 1.3,
                MetricKey.MAX_DRAWDOWN: -0.05,
                MetricKey.BETA: 0.8,
            },
        )
    )

    matches = repository.search("alpha", "run_id")
    assert [summary.run_id for summary in matches] == [RunId("Alpha-Run")]

    comparison = repository.compare_backtests([RunId("Alpha-Run")])
    assert comparison["backtests"][0]["run_id"] == "Alpha-Run"
    assert "Alpha-Run" in comparison["equity_curves"]
