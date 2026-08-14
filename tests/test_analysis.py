import numpy as np
import pandas as pd
import pytest

from algosystem.portfolio.optimization import (
    calculate_efficient_frontier,
    calculate_portfolio_return,
    calculate_portfolio_std,
    calculate_portfolio_variance,
    calculate_sharpe_ratio,
    optimize_portfolio,
)


@pytest.fixture
def sample_returns_data():
    dates = pd.date_range("2020-01-01", periods=100, freq="D")
    np.random.seed(42)
    return pd.DataFrame(
        {
            "Asset_A": np.random.normal(0.001, 0.02, 100),
            "Asset_B": np.random.normal(0.0008, 0.015, 100),
            "Asset_C": np.random.normal(0.0012, 0.025, 100),
        },
        index=dates,
    )


def test_calculate_portfolio_return(sample_returns_data):
    weights = np.array([0.4, 0.3, 0.3])

    portfolio_return = calculate_portfolio_return(weights, sample_returns_data)

    expected_return = (weights * sample_returns_data.mean()).sum()
    assert isinstance(portfolio_return, float)
    assert abs(portfolio_return - expected_return) < 1e-10


def test_calculate_portfolio_variance_and_std(sample_returns_data):
    weights = np.array([0.4, 0.3, 0.3])
    cov_matrix = sample_returns_data.cov()

    portfolio_var = calculate_portfolio_variance(weights, cov_matrix)
    portfolio_std = calculate_portfolio_std(weights, cov_matrix)

    assert portfolio_var >= 0
    assert portfolio_std >= 0
    assert abs(portfolio_std - np.sqrt(portfolio_var)) < 1e-10


def test_calculate_sharpe_ratio_portfolio(sample_returns_data):
    weights = np.array([0.4, 0.3, 0.3])
    cov_matrix = sample_returns_data.cov()

    sharpe = calculate_sharpe_ratio(weights, sample_returns_data, cov_matrix)

    assert isinstance(sharpe, float)
    assert np.isfinite(sharpe)


def test_optimize_portfolio(sample_returns_data):
    optimal_weights, performance = optimize_portfolio(sample_returns_data)

    assert isinstance(optimal_weights, np.ndarray)
    assert len(optimal_weights) == len(sample_returns_data.columns)
    assert abs(optimal_weights.sum() - 1.0) < 1e-6
    assert (optimal_weights >= 0).all()
    assert set(performance) == {"sharpe_ratio", "expected_return", "volatility"}


def test_calculate_efficient_frontier(sample_returns_data):
    returns, volatilities, weights = calculate_efficient_frontier(
        sample_returns_data, num_points=10
    )

    assert isinstance(returns, np.ndarray)
    assert isinstance(volatilities, np.ndarray)
    assert isinstance(weights, list)
    assert len(returns) == 10
    assert len(volatilities) == 10
    assert len(weights) == 10
