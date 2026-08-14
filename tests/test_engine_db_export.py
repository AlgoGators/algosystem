import pandas as pd

from algosystem.backtesting.domain.backtest import Backtest
from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.infrastructure.fake_calculator import FakeMetricsCalculator
from algosystem.backtesting.infrastructure.persistence.in_memory_repository import (
    InMemoryBacktestRunRepository,
)
from algosystem.shared.metric_key import MetricKey
from algosystem.shared.values import RunId


def test_backtest_result_can_be_persisted_through_repository_port():
    prices = pd.Series([100.0, 101.0, 104.0], index=pd.date_range("2020-01-01", periods=3))
    backtest = Backtest(
        EquityCurve.from_series(prices),
        run_id=RunId("engine-export"),
    )
    result = backtest.run(FakeMetricsCalculator())
    repository = InMemoryBacktestRunRepository()

    saved_run_id = repository.save(result)
    loaded = repository.get(RunId("engine-export"))

    assert saved_run_id == RunId("engine-export")
    assert loaded.metrics.get(MetricKey.SHARPE_RATIO) == result.metrics.get(MetricKey.SHARPE_RATIO)
    assert loaded.equity_curve.values.equals(result.equity_curve.values)
