import pandas as pd
import pytest

from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.infrastructure.quantstats_calculator import QuantStatsMetricsCalculator
from algosystem.shared.errors import InvalidPriceSeriesError
from algosystem.shared.metric_key import MetricKey


def deterministic_curve(values=None) -> EquityCurve:
    prices = values or [100.0, 101.0, 100.5, 102.0, 103.5, 104.0, 103.0, 105.0]
    return EquityCurve.from_series(
        pd.Series(prices, index=pd.date_range("2020-01-01", periods=len(prices), freq="D"))
    )


def test_calculate_returns_metric_keys_for_deterministic_series():
    calculator = QuantStatsMetricsCalculator()

    metrics = calculator.calculate(deterministic_curve(), None)

    assert metrics.get(MetricKey.TOTAL_RETURN) == pytest.approx(0.05)
    assert metrics.get(MetricKey.ANNUALIZED_RETURN) is not None
    assert metrics.get(MetricKey.MAX_DRAWDOWN) is not None
    assert MetricKey.TOTAL_RETURN.value in metrics.to_dict()


def test_uncomputable_metric_is_none_not_fabricated(monkeypatch):
    def fail_conditional_value_at_risk(*args, **kwargs):
        raise ValueError("cannot calculate")

    monkeypatch.setattr(
        "algosystem.backtesting.infrastructure.quantstats_calculator.qs.stats.conditional_value_at_risk",
        fail_conditional_value_at_risk,
    )
    calculator = QuantStatsMetricsCalculator()

    metrics = calculator.calculate(deterministic_curve(), None)

    assert metrics.get(MetricKey.VAR_95) is not None
    assert metrics.get(MetricKey.CVAR_95) is None


def test_calculate_with_benchmark_adds_relative_metrics():
    calculator = QuantStatsMetricsCalculator()
    benchmark = deterministic_curve([100.0, 100.5, 101.0, 102.0, 102.5, 103.0, 103.5, 104.0])

    metrics = calculator.calculate(deterministic_curve(), benchmark)

    assert metrics.get(MetricKey.CORRELATION) is not None
    assert MetricKey.CORRELATION.value in metrics.to_dict()


def test_time_series_returns_raw_series():
    calculator = QuantStatsMetricsCalculator()

    series = calculator.time_series(deterministic_curve(), None, window=3)

    assert "daily_returns" in series
    assert "rolling_sharpe" in series
    assert "monthly_returns" in series
    assert isinstance(series["daily_returns"], pd.Series)


def test_unrealistic_return_raises_typed_error():
    calculator = QuantStatsMetricsCalculator()

    with pytest.raises(InvalidPriceSeriesError):
        calculator.calculate(deterministic_curve([100.0, 1201.0, 1202.0]), None)
