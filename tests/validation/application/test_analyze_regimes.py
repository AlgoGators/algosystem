"""Tests for the AnalyzeRegimes use case."""

import numpy as np
import pandas as pd
import pytest

from algosystem.shared.errors import ValidationError
from algosystem.validation.application.analyze_regimes import AnalyzeRegimes
from algosystem.validation.domain.statistics.robustness import regime_conditional_performance
from algosystem.validation.domain.validation_metric import ValidationMetricKey
from tests.validation.conftest import regime_curve, regime_levels, regime_returns

VOL_WINDOW = 21

_returns = regime_returns
_levels = regime_levels
_curve = regime_curve


class TestInputCoercion:
    def test_array_input_matches_the_domain_function(self):
        returns = _returns()

        result = AnalyzeRegimes().execute(returns, vol_window=VOL_WINDOW)
        expected = regime_conditional_performance(returns, vol_window=VOL_WINDOW)

        assert result == expected

    def test_equity_curve_input_is_converted_to_returns(self):
        """An EquityCurve holds levels; the use case must not treat them as returns."""
        returns = _returns()
        curve = _curve(returns)

        result = AnalyzeRegimes().execute(curve, vol_window=VOL_WINDOW)

        assert sum(result.regime_counts) == len(returns) - VOL_WINDOW
        direct = regime_conditional_performance(returns, vol_window=VOL_WINDOW)
        assert result.regime_counts == direct.regime_counts
        assert result.regime_sharpes == pytest.approx(direct.regime_sharpes, rel=1e-9)
        assert result.regime_names == ["low_vol", "med_vol", "high_vol"]

    def test_series_of_levels_needs_the_explicit_input_kind(self):
        returns = _returns()
        levels = pd.Series(_levels(returns))

        as_levels = AnalyzeRegimes().execute(levels, input_kind="levels", vol_window=VOL_WINDOW)
        direct = regime_conditional_performance(returns, vol_window=VOL_WINDOW)

        assert as_levels.overall_sharpe == pytest.approx(direct.overall_sharpe, rel=1e-9)

    def test_returns_are_the_default_interpretation(self):
        returns = _returns()

        default = AnalyzeRegimes().execute(returns, vol_window=VOL_WINDOW)
        explicit = AnalyzeRegimes().execute(returns, input_kind="returns", vol_window=VOL_WINDOW)

        assert default == explicit

    def test_sequence_input_is_accepted(self):
        returns = _returns()

        result = AnalyzeRegimes().execute(list(returns), vol_window=VOL_WINDOW)

        assert (
            result.regime_counts
            == regime_conditional_performance(returns, vol_window=VOL_WINDOW).regime_counts
        )


class TestMarketReturns:
    def test_market_series_defines_the_regimes(self):
        rng = np.random.default_rng(13)
        strategy = rng.normal(0.0005, 0.01, size=600)
        market = _returns()

        on_strategy = AnalyzeRegimes().execute(strategy, vol_window=VOL_WINDOW)
        on_market = AnalyzeRegimes().execute(strategy, market_returns=market, vol_window=VOL_WINDOW)

        assert on_strategy.regime_sharpes != on_market.regime_sharpes

    def test_market_equity_curve_is_converted_the_same_way(self):
        strategy = _returns(seed=2)
        market = _returns(seed=9)

        from_curve = AnalyzeRegimes().execute(
            _curve(strategy), market_returns=_curve(market), vol_window=VOL_WINDOW
        )
        from_arrays = AnalyzeRegimes().execute(
            np.asarray(_curve(strategy).returns()),
            market_returns=np.asarray(_curve(market).returns()),
            vol_window=VOL_WINDOW,
        )

        assert from_curve == from_arrays

    def test_length_mismatch_raises(self):
        with pytest.raises(ValidationError, match="same length"):
            AnalyzeRegimes().execute(_returns(size=600), market_returns=_returns(size=400))


class TestParameterValidation:
    @pytest.mark.parametrize(
        "kwargs, message",
        [
            ({"n_regimes": 1}, "n_regimes must be at least 2"),
            ({"n_regimes": 0}, "n_regimes must be at least 2"),
            ({"vol_window": 1}, "vol_window must be at least 2"),
            ({"annualize": 0.0}, "annualize must be positive"),
            ({"annualize": -252.0}, "annualize must be positive"),
        ],
    )
    def test_out_of_range_parameters_raise(self, kwargs, message):
        with pytest.raises(ValidationError, match=message):
            AnalyzeRegimes().execute(_returns(), **kwargs)

    def test_parameters_are_checked_before_the_series_is_converted(self):
        """A bad parameter must surface as itself, not as a conversion failure."""
        with pytest.raises(ValidationError, match="n_regimes must be at least 2"):
            AnalyzeRegimes().execute([], n_regimes=1)

    @pytest.mark.parametrize(
        "source, message",
        [
            ([], "must not be empty"),
            ([0.01], "at least two observations"),
            ([0.01, np.nan], "finite"),
        ],
    )
    def test_unusable_series_raise(self, source, message):
        with pytest.raises(ValidationError, match=message):
            AnalyzeRegimes().execute(source)

    def test_invalid_input_kind_raises(self):
        with pytest.raises(ValidationError, match="input_kind"):
            AnalyzeRegimes().execute(_returns(), input_kind="prices")


class TestDateAlignment:
    def test_disjoint_dated_series_are_rejected(self):
        """Regimes are assigned positionally, so equal length is not enough."""
        strategy = pd.Series(
            _returns(seed=2), index=pd.date_range("2020-01-01", periods=600, freq="D")
        )
        market = pd.Series(
            _returns(seed=9), index=pd.date_range("2010-01-01", periods=600, freq="D")
        )

        with pytest.raises(ValidationError, match="same dates"):
            AnalyzeRegimes().execute(strategy, market_returns=market)

    def test_shifted_dates_are_rejected(self):
        index = pd.date_range("2020-01-01", periods=600, freq="D")
        strategy = pd.Series(_returns(seed=2), index=index)
        market = pd.Series(_returns(seed=9), index=index.shift(1))

        with pytest.raises(ValidationError, match="same dates"):
            AnalyzeRegimes().execute(strategy, market_returns=market)

    def test_matching_dates_are_accepted(self):
        index = pd.date_range("2020-01-01", periods=600, freq="D")
        strategy = pd.Series(_returns(seed=2), index=index)
        market = pd.Series(_returns(seed=9), index=index)

        result = AnalyzeRegimes().execute(strategy, market_returns=market)

        assert sum(result.regime_counts) == 600 - VOL_WINDOW

    def test_equity_curve_pair_aligns_on_the_shared_dates(self):
        strategy = _returns(seed=2)
        market = _returns(seed=9)

        result = AnalyzeRegimes().execute(_curve(strategy), market_returns=_curve(market))

        assert sum(result.regime_counts) == len(strategy) - VOL_WINDOW

    def test_undated_input_skips_the_date_check(self):
        """Plain arrays carry no dates, so only the length guard can apply."""
        result = AnalyzeRegimes().execute(_returns(seed=2), market_returns=_returns(seed=9))

        assert sum(result.regime_counts) == 600 - VOL_WINDOW


class TestMixedInputKinds:
    def test_market_input_kind_defaults_to_input_kind(self):
        strategy = _returns(seed=2)
        market = _returns(seed=9)

        default = AnalyzeRegimes().execute(strategy, market_returns=market)
        explicit = AnalyzeRegimes().execute(
            strategy, market_returns=market, market_input_kind="returns"
        )

        assert default == explicit

    def test_strategy_levels_can_pair_with_market_returns(self):
        strategy = _returns(seed=2)
        market = _returns(seed=9)

        mixed = AnalyzeRegimes().execute(
            _levels(strategy),
            market_returns=market,
            input_kind="levels",
            market_input_kind="returns",
        )
        plain = AnalyzeRegimes().execute(strategy, market_returns=market)

        assert mixed.regime_counts == plain.regime_counts
        assert mixed.regime_sharpes == pytest.approx(plain.regime_sharpes, rel=1e-9)


class TestInsufficientData:
    def test_series_no_longer_than_the_window_is_rejected(self):
        """The domain would quietly collapse to a single 'all' regime scored 0.0."""
        with pytest.raises(ValidationError, match="more than vol_window"):
            AnalyzeRegimes().execute(np.full(15, 0.001), vol_window=VOL_WINDOW)

    def test_series_too_short_to_fill_the_buckets_is_rejected(self):
        """Buckets under five observations score 0.0, which reads as a false verdict."""
        returns = np.linspace(0.001, 0.02, 30)

        with pytest.raises(ValidationError, match="at least 15 observations"):
            AnalyzeRegimes().execute(returns, vol_window=VOL_WINDOW)

    def test_a_shorter_window_makes_the_same_series_classifiable(self):
        returns = np.linspace(0.001, 0.02, 30)

        result = AnalyzeRegimes().execute(returns, vol_window=5)

        assert sum(result.regime_counts) == 25

    def test_thin_buckets_remain_possible_and_are_visible_in_the_counts(self):
        """
        The guard is necessary, not sufficient: percentile thresholds can still
        leave a bucket under five observations, which the domain scores 0.0. The
        counts are what let a caller tell that apart from a real loss, which is
        why to_metrics() carries them.
        """
        result = AnalyzeRegimes().execute(np.linspace(0.001, 0.02, 30), vol_window=5)

        thin = [name for name, count in zip(result.regime_names, result.regime_counts) if count < 5]
        assert thin, "this fixture is chosen to produce a thin bucket"
        for name in thin:
            index = result.regime_names.index(name)
            assert result.regime_sharpes[index] == 0.0
        assert result.to_metrics()[ValidationMetricKey.REGIME_COUNTS.value] == dict(
            zip(result.regime_names, result.regime_counts)
        )


class TestNumericParameterTypes:
    @pytest.mark.parametrize("value", [3.5, "3", None])
    def test_non_integer_n_regimes_raises_a_typed_error(self, value):
        with pytest.raises(ValidationError, match="n_regimes must be an integer"):
            AnalyzeRegimes().execute(_returns(), n_regimes=value)

    @pytest.mark.parametrize("value", [2.5, "21", None])
    def test_non_integer_vol_window_raises_a_typed_error(self, value):
        with pytest.raises(ValidationError, match="vol_window must be an integer"):
            AnalyzeRegimes().execute(_returns(), vol_window=value)

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_non_finite_annualize_raises(self, value):
        """nan slips past a bare `annualize <= 0` check and poisons every Sharpe."""
        with pytest.raises(ValidationError, match="annualize must be finite"):
            AnalyzeRegimes().execute(_returns(), annualize=value)

    def test_annualize_changes_the_reported_sharpe(self):
        returns = _returns()

        daily = AnalyzeRegimes().execute(returns, annualize=1.0, vol_window=VOL_WINDOW)
        annual = AnalyzeRegimes().execute(returns, annualize=252.0, vol_window=VOL_WINDOW)

        assert annual.overall_sharpe == pytest.approx(daily.overall_sharpe * np.sqrt(252.0))


class TestErrorAttribution:
    def test_a_bad_market_series_names_the_offending_argument(self):
        with pytest.raises(ValidationError, match="market_returns:"):
            AnalyzeRegimes().execute(_returns(), market_returns=[0.01, np.nan])

    def test_a_bad_strategy_series_names_the_offending_argument(self):
        with pytest.raises(ValidationError, match="returns:"):
            AnalyzeRegimes().execute([0.01, np.nan])
