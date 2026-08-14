import pandas as pd
import pytest

from algosystem.backtesting.domain.backtest import Backtest, BacktestResult
from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.infrastructure.fake_calculator import FakeMetricsCalculator
from algosystem.shared.errors import InvalidCapitalError, InvalidDateRangeError
from algosystem.shared.metric_key import MetricKey
from algosystem.shared.values import DateRange, Money, Percent, RunId


def curve(values=None, start="2020-01-01") -> EquityCurve:
    prices = values or [100.0, 102.0, 104.0, 103.0, 105.0]
    return EquityCurve.from_series(
        pd.Series(prices, index=pd.date_range(start, periods=len(prices), freq="D"))
    )


def test_construct_defaults_to_strategy_range_and_initial_capital():
    equity = curve()

    backtest = Backtest(equity)

    assert backtest.equity_curve.values.equals(equity.values)
    assert backtest.benchmark_curve is None
    assert backtest.date_range == equity.date_range
    assert backtest.initial_capital == Money(100)
    assert backtest.run_id is None


def test_construct_slices_to_date_range():
    backtest = Backtest(curve(), date_range=DateRange("2020-01-02", "2020-01-04"))

    assert backtest.equity_curve.values.index.tolist() == list(
        pd.date_range("2020-01-02", periods=3)
    )
    assert backtest.date_range == DateRange("2020-01-02", "2020-01-04")


def test_construct_rejects_empty_strategy_slice_and_non_positive_capital():
    with pytest.raises(InvalidDateRangeError):
        Backtest(curve(), date_range=DateRange("2021-01-01", "2021-01-02"))
    with pytest.raises(InvalidCapitalError):
        Backtest(curve(), initial_capital=Money(0))


def test_construct_aligns_benchmark_to_overlap():
    benchmark = EquityCurve.from_series(
        pd.Series(
            [200.0, 201.0, 202.0],
            index=pd.date_range("2020-01-03", periods=3, freq="D"),
        )
    )

    backtest = Backtest(curve(), benchmark=benchmark)

    assert backtest.benchmark_curve is not None
    assert backtest.equity_curve.values.index.tolist() == list(
        pd.date_range("2020-01-03", periods=3)
    )
    assert (
        backtest.benchmark_curve.values.index.tolist()
        == backtest.equity_curve.values.index.tolist()
    )


def test_construct_ignores_benchmark_with_no_overlap():
    backtest = Backtest(curve(), benchmark=curve(start="2021-01-01"))

    assert backtest.benchmark_curve is None
    assert backtest.equity_curve.values.index.tolist() == list(
        pd.date_range("2020-01-01", periods=5)
    )


def test_run_rebases_to_initial_capital_and_is_idempotent():
    backtest = Backtest(curve(), initial_capital=Money(1000), run_id=RunId("run-1"))
    calculator = FakeMetricsCalculator()

    first = backtest.run(calculator)
    second = backtest.run(calculator)

    assert isinstance(first, BacktestResult)
    assert first == second
    assert first.run_id == RunId("run-1")
    assert first.equity_curve.initial_value == Money(1000)
    assert first.final_capital == Money(1050)
    assert first.total_return == Percent(0.05)
    assert first.metrics.get(MetricKey.SHARPE_RATIO) == 1.5


def test_result_summary_and_legacy_dict_shape():
    result = Backtest(curve(), initial_capital=Money(1000)).run(FakeMetricsCalculator())

    summary = result.summary()
    legacy = result.to_legacy_dict()

    assert summary["initial_capital"] == 1000.0
    assert set(legacy) == {
        "equity",
        "initial_capital",
        "final_capital",
        "returns",
        "data",
        "start_date",
        "end_date",
        "metrics",
        "plots",
    }
    assert legacy["initial_capital"] == 1000.0
    assert legacy["final_capital"] == 1050.0
    assert legacy["returns"] == pytest.approx(0.05)
    assert legacy["metrics"][MetricKey.SHARPE_RATIO.value] == 1.5
    assert legacy["plots"] == {}
