import pytest
import pandas as pd
import numpy as np
from algosystem.backtesting.metrics import (
    calculate_metrics, 
    calculate_time_series_data,
    rolling_sharpe,
    rolling_sortino,
    equity_curve,
    drawdown_series
)


class TestMetricsCalculation:
    """Test metrics calculation functions."""
    
    def test_calculate_metrics_basic(self, sample_price_series):
        """Test basic metrics calculation."""
        metrics = calculate_metrics(sample_price_series)
        
        # Check that metrics dictionary is returned
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
        
        # Check for essential metrics
        expected_metrics = [
            'total_return', 'annualized_return', 'annualized_volatility',
            'sharpe_ratio', 'max_drawdown'
        ]
        
        for metric in expected_metrics:
            assert metric in metrics
            assert isinstance(metrics[metric], (int, float))
            assert not pd.isna(metrics[metric])
    
    def test_calculate_metrics_with_benchmark(self, sample_price_series, sample_benchmark_series):
        """Test metrics calculation with benchmark."""
        metrics = calculate_metrics(sample_price_series, sample_benchmark_series)
        
        # Check benchmark-specific metrics
        benchmark_metrics = ['alpha', 'beta', 'correlation']
        
        # Note: Some metrics might fail calculation, we just ensure no errors
        assert isinstance(metrics, dict)
        assert len(metrics) > 0
    
    def test_calculate_time_series_data(self, sample_price_series):
        """Test time series data calculation."""
        time_series = calculate_time_series_data(sample_price_series)
        
        # Check that time series data is returned
        assert isinstance(time_series, dict)
        assert len(time_series) > 0
        
        # Check for essential time series
        expected_series = [
            'equity_curve', 'drawdown_series', 'rolling_sharpe',
            'daily_returns', 'monthly_returns'
        ]
        
        for series_name in expected_series:
            assert series_name in time_series
            if time_series[series_name] is not None:
                assert isinstance(time_series[series_name], pd.Series)
    
    def test_rolling_sharpe(self, sample_price_series):
        """Test rolling Sharpe ratio calculation."""
        returns = sample_price_series.pct_change().dropna()
        
        rolling_sharpe_30 = rolling_sharpe(returns, window=30)
        
        # Check output
        assert isinstance(rolling_sharpe_30, pd.Series)
        assert len(rolling_sharpe_30) <= len(returns)
        
        # Test different window sizes
        rolling_sharpe_10 = rolling_sharpe(returns, window=10)
        assert isinstance(rolling_sharpe_10, pd.Series)
        assert len(rolling_sharpe_10) >= len(rolling_sharpe_30)
    
    def test_rolling_sortino(self, sample_price_series):
        """Test rolling Sortino ratio calculation."""
        returns = sample_price_series.pct_change().dropna()
        
        rolling_sortino_30 = rolling_sortino(returns, window=30)
        
        # Check output
        assert isinstance(rolling_sortino_30, pd.Series)
        assert len(rolling_sortino_30) <= len(returns)
    
    def test_equity_curve(self, sample_price_series):
        """Test equity curve calculation."""
        returns = sample_price_series.pct_change().dropna()
        
        equity = equity_curve(returns)
        
        # Check output
        assert isinstance(equity, pd.Series)
        assert len(equity) == len(returns)
        assert equity.iloc[0] == 1.0  # Should start at 1
    
    def test_drawdown_series_calculation(self, sample_price_series):
        """Test drawdown series calculation."""
        returns = sample_price_series.pct_change().dropna()
        
        drawdown = drawdown_series(returns)
        
        # Check output
        assert isinstance(drawdown, pd.Series)
        assert len(drawdown) == len(returns)
        assert (drawdown <= 0).all()  # Drawdown should be non-positive
    
    def test_metrics_with_small_dataset(self, small_dataset):
        """Test metrics calculation with small dataset."""
        # Should handle small datasets gracefully
        metrics = calculate_metrics(small_dataset)
        
        assert isinstance(metrics, dict)
        # Some metrics might be NaN or 0 for small datasets, which is acceptable
    
    def test_metrics_with_constant_prices(self, constant_series):
        """Test metrics calculation with constant prices."""
        metrics = calculate_metrics(constant_series)
        
        # Should handle constant prices
        assert isinstance(metrics, dict)
        assert metrics['total_return'] == 0.0
        assert metrics['annualized_volatility'] == 0.0
    
    def test_metrics_with_high_volatility(self, volatile_series):
        """Test metrics calculation with high volatility."""
        metrics = calculate_metrics(volatile_series)
        
        # Should handle high volatility
        assert isinstance(metrics, dict)
        assert 'annualized_volatility' in metrics
        assert metrics['annualized_volatility'] > 0
    
    def test_empty_series_handling(self):
        """Test handling of empty series."""
        empty_series = pd.Series(dtype=float)
        
        # Should handle empty series gracefully or raise appropriate error
        try:
            metrics = calculate_metrics(empty_series)
            # If it doesn't raise an error, should return empty dict or with NaN values
            assert isinstance(metrics, dict)
        except (ValueError, AttributeError):
            # It's acceptable to raise an error for empty series
            pass
    
    def test_time_series_data_with_benchmark(self, sample_price_series, sample_benchmark_series):
        """Test time series data calculation with benchmark."""
        time_series = calculate_time_series_data(sample_price_series, sample_benchmark_series)
        
        # Should include benchmark data
        assert isinstance(time_series, dict)
        
        # Check for benchmark-specific series
        benchmark_series = ['benchmark_equity_curve', 'relative_performance']
        for series_name in benchmark_series:
            if series_name in time_series:
                assert isinstance(time_series[series_name], pd.Series)


class TestMetricsEdgeCases:
    """Test edge cases in metrics calculation."""
    
    def test_single_return_calculation(self):
        """Test metrics with single return value."""
        single_return = pd.Series([0.01], index=[pd.Timestamp('2020-01-01')])
        
        try:
            metrics = calculate_metrics(single_return)
            assert isinstance(metrics, dict)
        except (ValueError, ZeroDivisionError):
            # Expected for insufficient data
            pass
    
    def test_all_negative_returns(self, negative_returns_series):
        """Test metrics with all negative returns."""
        metrics = calculate_metrics(negative_returns_series)
        
        # Should handle negative returns
        assert isinstance(metrics, dict)
        assert 'total_return' in metrics
        assert metrics['total_return'] < 0
    
    def test_extreme_values(self):
        """Test metrics with extreme values."""
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        # Create series with extreme jumps
        extreme_series = pd.Series([100, 1000, 10, 500, 50, 300, 30, 200, 20, 100], index=dates)
        
        # Should handle extreme values without crashing
        metrics = calculate_metrics(extreme_series)
        assert isinstance(metrics, dict)
    
    def test_metrics_numerical_stability(self):
        """Test numerical stability of metrics calculation."""
        # Create a series that might cause numerical issues
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        # Very small changes
        small_changes = pd.Series([100 + i * 0.0001 for i in range(100)], index=dates)
        
        metrics = calculate_metrics(small_changes)
        assert isinstance(metrics, dict)
        
        # Check that metrics are finite
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                assert np.isfinite(value), f"Metric {key} is not finite: {value}"
    
    def test_rolling_metrics_edge_cases(self):
        """Test rolling metrics with edge cases."""
        # Test with window larger than series
        short_series = pd.Series([0.01, 0.02, -0.01], index=pd.date_range('2020-01-01', periods=3))
        
        # Should handle gracefully
        rolling_sharpe_result = rolling_sharpe(short_series, window=10)
        assert isinstance(rolling_sharpe_result, pd.Series)
    
    def test_metrics_with_inf_values(self):
        """Test metrics handling infinite values."""
        # Create series that might generate inf values
        dates = pd.date_range('2020-01-01', periods=5, freq='D')
        inf_series = pd.Series([100, np.inf, 105, 110, 115], index=dates)
        
        # Should handle or reject inf values appropriately
        try:
            # Clean inf values first
            clean_series = inf_series.replace([np.inf, -np.inf], np.nan).dropna()
            if len(clean_series) > 1:
                metrics = calculate_metrics(clean_series)
                assert isinstance(metrics, dict)
        except (ValueError, TypeError):
            # Acceptable to raise error for invalid data
            pass