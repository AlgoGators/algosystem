import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from datetime import datetime, timedelta


@pytest.fixture
def sample_price_series():
    """Create a sample price series for testing."""
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 100)
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    prices.name = "Test Strategy"
    return prices


@pytest.fixture
def sample_benchmark_series():
    """Create a sample benchmark series for testing."""
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    np.random.seed(123)
    returns = np.random.normal(0.0005, 0.015, 100)
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    prices.name = "Test Benchmark"
    return prices


@pytest.fixture
def sample_dataframe():
    """Create a sample DataFrame with multiple columns."""
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    np.random.seed(42)
    data = pd.DataFrame({
        'Strategy': 100 * (1 + pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)).cumprod(),
        'Other_Column': np.random.normal(0, 1, 100)
    }, index=dates)
    return data


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_csv_file(sample_price_series, temp_directory):
    """Create a temporary CSV file with sample data."""
    csv_path = os.path.join(temp_directory, 'test_data.csv')
    sample_price_series.to_csv(csv_path)
    return csv_path


@pytest.fixture
def small_dataset():
    """Create a very small dataset for edge case testing."""
    dates = pd.date_range('2020-01-01', periods=5, freq='D')
    prices = pd.Series([100, 101, 99, 102, 98], index=dates)
    return prices


@pytest.fixture
def large_dataset():
    """Create a larger dataset for performance testing."""
    dates = pd.date_range('2020-01-01', periods=2000, freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.015, 2000)
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    return prices


@pytest.fixture
def missing_data_series():
    """Create a series with missing values."""
    dates = pd.date_range('2020-01-01', periods=50, freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, 50)
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    # Add some NaN values
    prices.iloc[10:15] = np.nan
    prices.iloc[30] = np.nan
    return prices


@pytest.fixture
def constant_series():
    """Create a series with constant values."""
    dates = pd.date_range('2020-01-01', periods=50, freq='D')
    prices = pd.Series([100] * 50, index=dates)
    return prices


@pytest.fixture
def volatile_series():
    """Create a highly volatile series."""
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.002, 0.08, 100)  # High volatility
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    return prices


@pytest.fixture
def negative_returns_series():
    """Create a series with mostly negative returns."""
    dates = pd.date_range('2020-01-01', periods=100, freq='D')
    np.random.seed(42)
    returns = np.random.normal(-0.002, 0.02, 100)  # Negative drift
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    return prices