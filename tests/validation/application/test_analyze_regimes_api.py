"""Tests for regime analysis reached through the public AlgoSystem facade."""

from pathlib import Path

import numpy as np
import pytest

from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.infrastructure.fake_calculator import FakeMetricsCalculator
from algosystem.interfaces.api import AlgoSystem
from algosystem.shared.errors import ValidationError
from algosystem.validation.domain.statistics.robustness import (
    RegimeResult,
    regime_conditional_performance,
)
from tests.validation.conftest import regime_curve, regime_levels, regime_returns

VOL_WINDOW = 21

_returns = regime_returns
_levels = regime_levels
_curve = regime_curve


class StubTearsheetRenderer:
    """Satisfies the TearsheetRenderer port without importing quantstats."""

    def render(self, result, output_path, title, mode="html", rf=0.0, periods_per_year=252):
        return Path(output_path)


@pytest.fixture
def algo():
    """AlgoSystem with vendor adapters stubbed, so the facade is testable offline."""
    return AlgoSystem(calculator=FakeMetricsCalculator(), renderer=StubTearsheetRenderer())


def test_facade_returns_a_regime_result(algo):
    result = algo.analyze_regimes(_returns(), vol_window=VOL_WINDOW)

    assert isinstance(result, RegimeResult)
    assert result.regime_names == ["low_vol", "med_vol", "high_vol"]


def test_facade_matches_the_domain_function(algo):
    returns = _returns()

    result = algo.analyze_regimes(returns, vol_window=VOL_WINDOW)

    assert result == regime_conditional_performance(returns, vol_window=VOL_WINDOW)


def test_facade_accepts_an_equity_curve(algo):
    returns = _returns()

    result = algo.analyze_regimes(_curve(returns), vol_window=VOL_WINDOW)

    assert sum(result.regime_counts) == len(returns) - VOL_WINDOW


def test_facade_forwards_every_option(algo):
    returns = _returns()

    result = algo.analyze_regimes(returns, n_regimes=4, vol_window=10, annualize=52.0)
    expected = regime_conditional_performance(returns, n_regimes=4, vol_window=10, annualize=52.0)

    assert result == expected
    assert result.regime_names == ["regime_0", "regime_1", "regime_2", "regime_3"]


def test_facade_forwards_the_market_series(algo):
    strategy = _returns(seed=2)
    market = _returns(seed=9)

    result = algo.analyze_regimes(strategy, market_returns=market, vol_window=VOL_WINDOW)

    assert result == regime_conditional_performance(
        strategy, market_returns=market, vol_window=VOL_WINDOW
    )


def test_facade_supports_mixed_input_kinds(algo):
    strategy = _returns(seed=2)
    market = _returns(seed=9)
    levels = np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + strategy)])

    result = algo.analyze_regimes(
        levels,
        market_returns=market,
        input_kind="levels",
        market_input_kind="returns",
        vol_window=VOL_WINDOW,
    )

    assert (
        result.regime_counts
        == regime_conditional_performance(
            strategy, market_returns=market, vol_window=VOL_WINDOW
        ).regime_counts
    )


def test_facade_surfaces_validation_errors(algo):
    with pytest.raises(ValidationError, match="n_regimes must be at least 2"):
        algo.analyze_regimes(_returns(), n_regimes=1)


def test_facade_rejects_a_series_too_short_to_classify(algo):
    with pytest.raises(ValidationError, match="more than vol_window"):
        algo.analyze_regimes(np.full(15, 0.001), vol_window=VOL_WINDOW)
