from dataclasses import fields

import pytest

from algosystem.backtesting.domain.metrics import PerformanceMetrics
from algosystem.shared.errors import CalculationError
from algosystem.shared.metric_key import LEGACY_ALIASES, MetricKey


def test_has_one_field_per_metric_key_member():
    metric_fields = {field.name for field in fields(PerformanceMetrics)}

    assert metric_fields == {metric_key.value for metric_key in MetricKey}


def test_to_dict_omits_none_values_and_uses_metric_key_values():
    metrics = PerformanceMetrics(
        total_return=0.2,
        annualized_return=None,
        sharpe_ratio=1.1,
    )

    assert metrics.to_dict() == {
        MetricKey.TOTAL_RETURN.value: 0.2,
        MetricKey.SHARPE_RATIO.value: 1.1,
    }


def test_from_dict_accepts_metric_keys_strings_and_legacy_aliases():
    metrics = PerformanceMetrics.from_dict(
        {
            MetricKey.TOTAL_RETURN: 0.2,
            MetricKey.SHARPE_RATIO.value: 1.5,
            "annual_return": 0.12,
            "volatility": 0.08,
        }
    )

    assert metrics.get(MetricKey.TOTAL_RETURN) == 0.2
    assert metrics.get(MetricKey.SHARPE_RATIO) == 1.5
    assert metrics.get(LEGACY_ALIASES["annual_return"]) == 0.12
    assert metrics.get(LEGACY_ALIASES["volatility"]) == 0.08


def test_get_accepts_metric_key_canonical_string_and_legacy_alias():
    metrics = PerformanceMetrics.from_dict(
        {
            MetricKey.SHARPE_RATIO: 1.5,
            MetricKey.ANNUALIZED_RETURN: 0.12,
        }
    )

    assert metrics.get(MetricKey.SHARPE_RATIO) == 1.5
    assert metrics.get(MetricKey.SHARPE_RATIO.value) == 1.5
    assert metrics.get("annual_return") == 0.12


def test_get_rejects_unknown_string_with_valid_keys():
    metrics = PerformanceMetrics()

    with pytest.raises(KeyError) as exc_info:
        metrics.get("unknown")

    message = str(exc_info.value)
    assert "unknown" in message
    assert MetricKey.SHARPE_RATIO.value in message
    assert "annual_return" in message


def test_from_dict_rejects_unknown_or_non_numeric_metric_values():
    with pytest.raises(CalculationError):
        PerformanceMetrics.from_dict({"unknown": 1.0})
    with pytest.raises(CalculationError):
        PerformanceMetrics.from_dict({MetricKey.TOTAL_RETURN: "not numeric"})


def test_getitem_warns_but_resolves_legacy_strings():
    metrics = PerformanceMetrics.from_dict({"annual_return": 0.12})

    with pytest.warns(DeprecationWarning):
        assert metrics["annual_return"] == 0.12
    with pytest.warns(DeprecationWarning):
        assert "annual_return" in metrics


def test_contains_returns_false_for_none_or_unknown_metrics():
    metrics = PerformanceMetrics()

    with pytest.warns(DeprecationWarning):
        assert MetricKey.SHARPE_RATIO.value not in metrics
    with pytest.warns(DeprecationWarning):
        assert "missing" not in metrics


def test_benchmark_relative_returns_only_benchmark_dependent_keys():
    metrics = PerformanceMetrics.from_dict(
        {
            MetricKey.ALPHA: 0.01,
            MetricKey.BETA: 1.2,
            MetricKey.TOTAL_RETURN: 0.2,
        }
    )

    relative = metrics.benchmark_relative()

    assert set(relative) == {key for key in MetricKey if key.is_benchmark_relative()}
    assert relative[MetricKey.ALPHA] == 0.01
    assert relative[MetricKey.BETA] == 1.2
    assert MetricKey.TOTAL_RETURN not in relative
