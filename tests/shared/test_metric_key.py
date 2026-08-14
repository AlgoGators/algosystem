from algosystem.shared.metric_key import LEGACY_ALIASES, MetricKey


def test_metric_key_is_string_compatible():
    assert MetricKey.SHARPE_RATIO == "sharpe_ratio"
    assert str(MetricKey.SHARPE_RATIO) == "MetricKey.SHARPE_RATIO"
    assert MetricKey.SHARPE_RATIO.value == "sharpe_ratio"


def test_every_metric_key_has_a_label():
    for metric_key in MetricKey:
        label = metric_key.label()
        assert label
        assert "_" not in label


def test_benchmark_relative_metrics_are_flagged():
    benchmark_relative = {
        MetricKey.ALPHA,
        MetricKey.BETA,
        MetricKey.CORRELATION,
        MetricKey.TRACKING_ERROR,
        MetricKey.INFORMATION_RATIO,
        MetricKey.CAPTURE_RATIO_UP,
        MetricKey.CAPTURE_RATIO_DOWN,
    }

    for metric_key in MetricKey:
        assert metric_key.is_benchmark_relative() is (metric_key in benchmark_relative)


def test_legacy_aliases_resolve_to_real_members():
    assert LEGACY_ALIASES == {
        "annual_return": MetricKey.ANNUALIZED_RETURN,
        "volatility": MetricKey.ANNUALIZED_VOLATILITY,
    }

    for alias, metric_key in LEGACY_ALIASES.items():
        assert alias != metric_key.value
        assert metric_key in MetricKey
