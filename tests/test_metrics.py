import pandas as pd
import pytest

from algosystem.backtesting.engine import Engine
from algosystem.shared.metric_key import MetricKey


def test_engine_legacy_metrics_dict_contains_canonical_keys(sample_price_series):
    engine = Engine(sample_price_series)

    results = engine.run()
    metrics = results["metrics"]

    assert isinstance(metrics, dict)
    assert MetricKey.TOTAL_RETURN.value in metrics
    assert MetricKey.ANNUALIZED_RETURN.value in metrics
    assert MetricKey.ANNUALIZED_VOLATILITY.value in metrics
    assert "annual_return" not in metrics
    assert "volatility" not in metrics


def test_engine_legacy_results_shape_and_empty_plots(sample_price_series):
    results = Engine(sample_price_series).run()

    assert set(results) == {
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
    assert isinstance(results["equity"], pd.Series)
    assert isinstance(results["data"], pd.Series)
    assert results["plots"] == {}


def test_engine_legacy_metrics_omit_uncomputable_values(constant_series):
    metrics = Engine(constant_series).run()["metrics"]

    assert MetricKey.ANNUALIZED_VOLATILITY.value in metrics
    assert metrics[MetricKey.ANNUALIZED_VOLATILITY.value] == pytest.approx(0.0)
    assert MetricKey.SHARPE_RATIO.value not in metrics


def test_get_metrics_matches_results_metrics(sample_price_series):
    engine = Engine(sample_price_series)
    results = engine.run()

    assert engine.get_metrics() == results["metrics"]
