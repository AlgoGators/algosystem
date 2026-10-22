"""Tests for volatility-regime classification and regime-conditional performance."""

import dataclasses

import numpy as np
import pytest

from algosystem.validation.domain.statistics.robustness import (
    RegimeResult,
    regime_conditional_performance,
)
from algosystem.validation.domain.validation_metric import ValidationMetricKey

VOL_WINDOW = 21
CALM_END = 300


def _regime_labels(returns: np.ndarray, *, vol_window: int) -> np.ndarray:
    """Recompute the classifier's labels so tests can inspect what landed where."""
    n = len(returns)
    rolling = np.full(n, np.nan)
    for i in range(vol_window, n):
        rolling[i] = np.std(returns[i - vol_window : i], ddof=1)
    valid = ~np.isnan(rolling)
    thresholds = np.percentile(rolling[valid], [100 / 3, 200 / 3])
    labels = np.full(n, -1, dtype=int)
    labels[valid] = np.searchsorted(thresholds, rolling[valid], side="left")
    return labels


def _calm_then_stormy(seed: int = 7) -> np.ndarray:
    """Returns with a sharp volatility break: calm for 300 steps, then stormy."""
    rng = np.random.default_rng(seed)
    calm = rng.normal(0.0, 0.001, size=CALM_END)
    stormy = rng.normal(0.0, 0.02, size=CALM_END)
    return np.concatenate([calm, stormy])


class TestRegimeClassification:
    def test_names_are_low_med_high_for_three_regimes(self):
        result = regime_conditional_performance(_calm_then_stormy(), vol_window=VOL_WINDOW)

        assert result.regime_names == ["low_vol", "med_vol", "high_vol"]

    def test_names_are_indexed_when_not_three_regimes(self):
        result = regime_conditional_performance(
            _calm_then_stormy(), n_regimes=4, vol_window=VOL_WINDOW
        )

        assert result.regime_names == ["regime_0", "regime_1", "regime_2", "regime_3"]

    def test_counts_cover_every_observation_past_the_warmup(self):
        returns = _calm_then_stormy()

        result = regime_conditional_performance(returns, vol_window=VOL_WINDOW)

        assert sum(result.regime_counts) == len(returns) - VOL_WINDOW

    def test_time_fractions_sum_to_one(self):
        result = regime_conditional_performance(_calm_then_stormy(), vol_window=VOL_WINDOW)

        assert sum(result.regime_frac) == pytest.approx(1.0)

    def test_low_and_high_regimes_track_the_actual_volatility_break(self):
        """
        The calm half must land in low_vol and the stormy half in high_vol.

        Asserting bucket sizes proves nothing — terciles are a third each by
        construction, even on IID noise with no regime structure at all. So this
        measures the realized volatility inside each bucket instead.
        """
        returns = _calm_then_stormy()

        result = regime_conditional_performance(returns, vol_window=VOL_WINDOW)
        labels = _regime_labels(returns, vol_window=VOL_WINDOW)

        assert result.regime_counts == [int(np.count_nonzero(labels == i)) for i in range(3)]

        low_vol = float(np.std(returns[labels == 0], ddof=1))
        high_vol = float(np.std(returns[labels == 2], ddof=1))

        # The fixture's halves differ in sigma by 20x (0.001 vs 0.02), but the
        # classifier is causal: the label at i comes from returns before i, so
        # the low bucket legitimately holds the ~21 stormy returns whose
        # preceding window was still calm. That caps realized separation near 8x.
        assert high_vol > 5 * low_vol
        # The extreme buckets must be drawn from one side of the break each.
        assert np.mean(np.flatnonzero(labels == 0) < CALM_END) > 0.95
        assert np.mean(np.flatnonzero(labels == 2) >= CALM_END) > 0.95

    def test_regimes_can_be_defined_by_a_separate_market_series(self):
        """Passing market_returns classifies on the market, not the strategy."""
        rng = np.random.default_rng(11)
        strategy = rng.normal(0.0, 0.01, size=600)
        market = _calm_then_stormy()

        on_strategy = regime_conditional_performance(strategy, vol_window=VOL_WINDOW)
        on_market = regime_conditional_performance(
            strategy, market_returns=market, vol_window=VOL_WINDOW
        )

        assert on_strategy.regime_sharpes != on_market.regime_sharpes


class TestRegimeVerdict:
    def test_calm_only_edge_is_flagged_regime_dependent(self):
        """A strategy that earns only in calm markets must not pass."""
        rng = np.random.default_rng(5)
        market = _calm_then_stormy()
        strategy = np.concatenate(
            [
                rng.normal(0.002, 0.001, size=CALM_END),  # earns while calm
                rng.normal(-0.002, 0.001, size=CALM_END),  # bleeds once vol arrives
            ]
        )

        result = regime_conditional_performance(
            strategy, market_returns=market, vol_window=VOL_WINDOW
        )

        assert result.works_in_all_regimes is False
        assert result.worst_regime_name == "high_vol"
        assert result.worst_regime_sharpe < 0

    def test_uniformly_profitable_strategy_works_in_all_regimes(self):
        rng = np.random.default_rng(3)
        market = _calm_then_stormy()
        strategy = rng.normal(0.002, 0.001, size=600)

        result = regime_conditional_performance(
            strategy, market_returns=market, vol_window=VOL_WINDOW
        )

        assert result.works_in_all_regimes is True
        assert all(sharpe > 0 for sharpe in result.regime_sharpes)


class TestDegenerateInput:
    def test_series_shorter_than_the_window_returns_a_single_regime(self):
        returns = np.full(10, 0.001)

        result = regime_conditional_performance(returns, vol_window=VOL_WINDOW)

        assert result.regime_names == ["all"]
        assert result.regime_counts == [10]
        assert result.works_in_all_regimes is False


class TestRegimeResultOutput:
    def test_result_is_frozen(self):
        result = regime_conditional_performance(_calm_then_stormy(), vol_window=VOL_WINDOW)

        assert isinstance(result, RegimeResult)
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.overall_sharpe = 1.0

    def test_summary_returns_lines_and_never_prints(self, capsys):
        result = regime_conditional_performance(_calm_then_stormy(), vol_window=VOL_WINDOW)

        lines = result.summary()

        assert isinstance(lines, list)
        assert all(isinstance(line, str) for line in lines)
        assert capsys.readouterr().out == ""

    def test_summary_warns_when_a_regime_loses_money(self):
        rng = np.random.default_rng(5)
        market = _calm_then_stormy()
        strategy = np.concatenate(
            [
                rng.normal(0.002, 0.001, size=CALM_END),
                rng.normal(-0.002, 0.001, size=CALM_END),
            ]
        )

        lines = regime_conditional_performance(
            strategy, market_returns=market, vol_window=VOL_WINDOW
        ).summary()

        assert any("WARNING" in line for line in lines)
        assert "REGIME-DEPENDENT" in lines[0]

    def test_to_metrics_uses_canonical_validation_metric_names(self):
        result = regime_conditional_performance(_calm_then_stormy(), vol_window=VOL_WINDOW)

        metrics = result.to_metrics()

        assert set(metrics) == {
            ValidationMetricKey.OVERALL_SHARPE.value,
            ValidationMetricKey.REGIME_SHARPES.value,
            ValidationMetricKey.REGIME_FRAC.value,
            ValidationMetricKey.REGIME_COUNTS.value,
            ValidationMetricKey.WORST_REGIME_SHARPE.value,
            ValidationMetricKey.WORST_REGIME_NAME.value,
            ValidationMetricKey.WORKS_IN_ALL_REGIMES.value,
        }
        assert metrics[ValidationMetricKey.OVERALL_SHARPE.value] == result.overall_sharpe
        assert metrics[ValidationMetricKey.REGIME_SHARPES.value] == dict(
            zip(result.regime_names, result.regime_sharpes)
        )
        assert metrics[ValidationMetricKey.REGIME_FRAC.value] == dict(
            zip(result.regime_names, result.regime_frac)
        )
        assert metrics[ValidationMetricKey.REGIME_COUNTS.value] == dict(
            zip(result.regime_names, result.regime_counts)
        )
        assert metrics[ValidationMetricKey.WORST_REGIME_SHARPE.value] == result.worst_regime_sharpe
        assert metrics[ValidationMetricKey.WORST_REGIME_NAME.value] == result.worst_regime_name
        assert (
            metrics[ValidationMetricKey.WORKS_IN_ALL_REGIMES.value] == result.works_in_all_regimes
        )
        assert all(
            type(value) is float
            for value in metrics[ValidationMetricKey.REGIME_FRAC.value].values()
        ), "to_metrics must emit plain floats so results serialize cleanly"
        assert all(
            type(value) is int
            for value in metrics[ValidationMetricKey.REGIME_COUNTS.value].values()
        )

    def test_to_metrics_is_lossless(self):
        """Every RegimeResult field must be recoverable from the mapping."""
        result = regime_conditional_performance(_calm_then_stormy(), vol_window=VOL_WINDOW)

        metrics = result.to_metrics()

        # regime_names is carried by the per-regime dict keys, not its own entry.
        names = list(metrics[ValidationMetricKey.REGIME_SHARPES.value])
        assert names == result.regime_names

        rebuilt = RegimeResult(
            regime_names=names,
            regime_sharpes=[metrics[ValidationMetricKey.REGIME_SHARPES.value][n] for n in names],
            regime_counts=[metrics[ValidationMetricKey.REGIME_COUNTS.value][n] for n in names],
            regime_frac=[metrics[ValidationMetricKey.REGIME_FRAC.value][n] for n in names],
            overall_sharpe=metrics[ValidationMetricKey.OVERALL_SHARPE.value],
            worst_regime_sharpe=metrics[ValidationMetricKey.WORST_REGIME_SHARPE.value],
            worst_regime_name=metrics[ValidationMetricKey.WORST_REGIME_NAME.value],
            works_in_all_regimes=metrics[ValidationMetricKey.WORKS_IN_ALL_REGIMES.value],
        )
        assert rebuilt == result

        # Guard against a field being added later without a matching key.
        assert len(dataclasses.fields(result)) == len(metrics) + 1
