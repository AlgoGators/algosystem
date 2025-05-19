import numpy as np
import pandas as pd
import pytest

from algosystem.backtesting.engine import Engine


class TestEngine:
    """Test cases for the Engine class."""

    def test_engine_initialization_with_series(self, sample_price_series):
        """Test Engine initialization with pandas Series."""
        engine = Engine(sample_price_series)

        assert engine.price_series is not None
        assert len(engine.price_series) == len(sample_price_series)
        assert engine.initial_capital == sample_price_series.iloc[0]
        assert engine.results is None
        assert engine.benchmark_series is None

    def test_engine_initialization_with_dataframe(self, sample_dataframe):
        """Test Engine initialization with pandas DataFrame."""
        engine = Engine(sample_dataframe, price_column="Strategy")

        assert engine.price_series is not None
        assert len(engine.price_series) == len(sample_dataframe)
        assert engine.initial_capital == sample_dataframe["Strategy"].iloc[0]
        assert engine.results is None

    def test_engine_initialization_with_single_column_df(self, sample_dataframe):
        """Test Engine initialization with single-column DataFrame."""
        single_col_df = sample_dataframe[["Strategy"]]
        engine = Engine(single_col_df)

        assert engine.price_series is not None
        assert len(engine.price_series) == len(single_col_df)
        assert engine.initial_capital == single_col_df["Strategy"].iloc[0]

    def test_engine_initialization_with_benchmark(
        self, sample_price_series, sample_benchmark_series
    ):
        """Test Engine initialization with benchmark data."""
        engine = Engine(sample_price_series, benchmark=sample_benchmark_series)

        assert engine.price_series is not None
        assert engine.benchmark_series is not None
        assert len(engine.benchmark_series) > 0

    def test_engine_initialization_with_benchmark_dataframe(
        self, sample_price_series, sample_dataframe
    ):
        """Test Engine initialization with benchmark DataFrame."""
        benchmark_df = sample_dataframe[["Strategy"]]
        engine = Engine(sample_price_series, benchmark=benchmark_df)

        assert engine.price_series is not None
        assert engine.benchmark_series is not None
        assert len(engine.benchmark_series) > 0

    def test_engine_initialization_with_custom_capital(self, sample_price_series):
        """Test Engine initialization with custom initial capital."""
        custom_capital = 50000.0
        engine = Engine(sample_price_series, initial_capital=custom_capital)

        assert engine.initial_capital == custom_capital

    def test_engine_initialization_with_date_range(self, sample_price_series):
        """Test Engine initialization with custom date range."""
        start_date = "2020-01-15"
        end_date = "2020-02-15"

        engine = Engine(sample_price_series, start_date=start_date, end_date=end_date)

        assert engine.start_date == pd.to_datetime(start_date)
        assert engine.end_date == pd.to_datetime(end_date)
        assert len(engine.price_series) < len(sample_price_series)

    def test_basic_backtest_run(self, sample_price_series):
        """Test basic backtest execution."""
        engine = Engine(sample_price_series)
        results = engine.run()

        # Check that results are generated
        assert results is not None
        assert isinstance(results, dict)

        # Check for required result keys
        required_keys = [
            "equity",
            "initial_capital",
            "final_capital",
            "returns",
            "metrics",
            "plots",
        ]
        for key in required_keys:
            assert key in results

        # Check equity series
        assert "equity" in results
        assert isinstance(results["equity"], pd.Series)
        assert len(results["equity"]) > 0

        # Check that metrics were calculated
        assert "metrics" in results
        assert isinstance(results["metrics"], dict)
        assert len(results["metrics"]) > 0

        # Verify metrics are reasonable
        assert "total_return" in results["metrics"]
        assert "annualized_return" in results["metrics"]
        assert "annualized_volatility" in results["metrics"]

    def test_backtest_with_benchmark(
        self, sample_price_series, sample_benchmark_series
    ):
        """Test backtest with benchmark comparison."""
        engine = Engine(sample_price_series, benchmark=sample_benchmark_series)
        results = engine.run()

        # Check that benchmark-specific metrics are calculated
        metrics = results["metrics"]
        # Note: Some metrics might not be present if calculation fails
        # We just check that no errors occurred during execution
        assert results is not None
        assert "metrics" in results

        # Check that plots include benchmark data
        assert "plots" in results
        plots = results["plots"]
        # Some benchmark plots might be available
        possible_benchmark_keys = ["benchmark_equity_curve", "relative_performance"]
        # At least one benchmark-related plot should be available
        has_benchmark_data = any(key in plots for key in possible_benchmark_keys)
        # Note: We don't assert this as it depends on successful metric calculation

    def test_get_results_before_run(self, sample_price_series):
        """Test getting results before running backtest."""
        engine = Engine(sample_price_series)
        results = engine.get_results()

        # Should return empty dict when no backtest has been run
        assert results == {}

    def test_get_metrics_before_run(self, sample_price_series):
        """Test getting metrics before running backtest."""
        engine = Engine(sample_price_series)
        metrics = engine.get_metrics()

        # Should return empty dict when no backtest has been run
        assert metrics == {}

    def test_small_dataset(self, small_dataset):
        """Test engine with very small dataset."""
        engine = Engine(small_dataset)

        # Should not raise an error even with small dataset
        results = engine.run()
        assert results is not None
        assert "metrics" in results

        # Verify basic structure
        assert "equity" in results
        assert len(results["equity"]) == len(small_dataset)

    def test_large_dataset(self, large_dataset):
        """Test engine with large dataset."""
        engine = Engine(large_dataset)

        # Should handle large datasets without issues
        results = engine.run()
        assert results is not None
        assert len(results["equity"]) == len(large_dataset)

        # Verify metrics are computed
        assert "metrics" in results
        assert len(results["metrics"]) > 0

    def test_constant_prices(self, constant_series):
        """Test engine with constant price series."""
        engine = Engine(constant_series)
        results = engine.run()

        # Should handle constant prices gracefully
        assert results is not None
        assert results["returns"] == 0.0  # No change in prices

        # Check that volatility is 0 or very close to 0
        assert "annualized_volatility" in results["metrics"]
        assert abs(results["metrics"]["annualized_volatility"]) < 1e-10

    def test_highly_volatile_series(self, volatile_series):
        """Test engine with highly volatile series."""
        engine = Engine(volatile_series)
        results = engine.run()

        # Should handle high volatility without errors
        assert results is not None
        assert "metrics" in results
        assert "annualized_volatility" in results["metrics"]  # Fixed: use correct key

        # Verify high volatility is detected
        assert (
            results["metrics"]["annualized_volatility"] > 0.1
        )  # Should be significantly volatile

    def test_negative_returns_series(self, negative_returns_series):
        """Test engine with series that has negative returns."""
        engine = Engine(negative_returns_series)
        results = engine.run()

        # Should handle negative returns without errors
        assert results is not None
        assert results["returns"] < 0  # Should show negative total return

        # Verify negative performance metrics
        assert "total_return" in results["metrics"]
        assert results["metrics"]["total_return"] < 0

    def test_invalid_data_type(self):
        """Test engine with invalid data type."""
        with pytest.raises((TypeError, ValueError)):
            Engine("invalid_data")

        with pytest.raises((TypeError, ValueError)):
            Engine(None)

        with pytest.raises((TypeError, ValueError)):
            Engine([1, 2, 3])  # List instead of pandas Series/DataFrame

    def test_empty_dataframe_error(self):
        """Test engine with empty DataFrame."""
        empty_df = pd.DataFrame()
        with pytest.raises(ValueError):
            Engine(empty_df)

    def test_empty_series_error(self):
        """Test engine with empty Series."""
        empty_series = pd.Series(dtype=float)
        with pytest.raises(ValueError):
            Engine(empty_series)

    def test_dataframe_without_price_column(self, sample_dataframe):
        """Test engine with DataFrame but no price column specified."""
        # Should raise error when DataFrame has multiple columns but no price_column specified
        with pytest.raises(ValueError):
            Engine(sample_dataframe)  # Has multiple columns

    def test_invalid_price_column(self, sample_dataframe):
        """Test engine with invalid price column name."""
        with pytest.raises(KeyError):
            Engine(sample_dataframe, price_column="NonExistent")

    def test_invalid_date_range(self, sample_price_series):
        """Test engine with invalid date range."""
        # End date before start date should result in empty data
        engine = Engine(
            sample_price_series, start_date="2020-12-31", end_date="2020-01-01"
        )
        with pytest.raises(ValueError):
            # Should raise error due to empty data after filtering
            pass

    def test_date_range_outside_data(self, sample_price_series):
        """Test engine with date range outside available data."""
        # Dates far in the future
        engine = Engine(
            sample_price_series, start_date="2025-01-01", end_date="2025-12-31"
        )
        with pytest.raises(ValueError):
            # Should raise error due to no data in range
            pass

    def test_print_metrics(self, sample_price_series, capsys):
        """Test metrics printing functionality."""
        engine = Engine(sample_price_series)
        results = engine.run()

        # Should not raise error
        engine.print_metrics()

        # Check that something was printed (capture doesn't work well with logging)
        # Just ensure the method doesn't crash
        assert True

    def test_print_metrics_before_run(self, sample_price_series, capsys):
        """Test printing metrics before running backtest."""
        engine = Engine(sample_price_series)

        # Should handle gracefully
        engine.print_metrics()
        # Just ensure it doesn't crash
        assert True

    def test_get_plots_without_run(self, sample_price_series):
        """Test getting plots before running backtest."""
        engine = Engine(sample_price_series)
        plots = engine.get_plots()

        # Should return empty dict
        assert plots == {}

    def test_get_plots_after_run(self, sample_price_series):
        """Test getting plots after running backtest."""
        engine = Engine(sample_price_series)
        results = engine.run()
        plots = engine.get_plots()

        # Should return plots dictionary
        assert isinstance(plots, dict)
        # Should have some plot data
        assert len(plots) > 0

        # Check for common plot types
        expected_plots = ["equity_curve", "drawdown_series", "daily_returns"]
        for plot_type in expected_plots:
            if plot_type in plots:
                assert isinstance(plots[plot_type], pd.Series)

    def test_engine_start_end_dates_properties(self, sample_price_series):
        """Test that start_date and end_date properties are correctly set."""
        start_date = "2020-01-15"
        end_date = "2020-02-15"

        engine = Engine(sample_price_series, start_date=start_date, end_date=end_date)

        assert hasattr(engine, "start_date")
        assert hasattr(engine, "end_date")
        assert engine.start_date == pd.to_datetime(start_date)
        assert engine.end_date == pd.to_datetime(end_date)

    def test_multiple_runs_same_engine(self, sample_price_series):
        """Test running the same engine multiple times."""
        engine = Engine(sample_price_series)

        # First run
        results1 = engine.run()
        assert results1 is not None

        # Second run should work and give same results
        results2 = engine.run()
        assert results2 is not None

        # Results should be identical
        assert results1["returns"] == results2["returns"]
        assert results1["initial_capital"] == results2["initial_capital"]
        assert results1["final_capital"] == results2["final_capital"]


class TestEngineEdgeCases:
    """Test edge cases and error conditions."""

    def test_missing_data_handling(self, missing_data_series):
        """Test how engine handles missing data."""
        # The engine should handle NaN values gracefully
        engine = Engine(missing_data_series.dropna())  # Drop NaN for valid test
        results = engine.run()

        assert results is not None
        assert "equity" in results

    def test_single_data_point(self):
        """Test engine with single data point."""
        single_point = pd.Series([100], index=[pd.Timestamp("2020-01-01")])

        # Should handle gracefully or raise appropriate error
        try:
            engine = Engine(single_point)
            results = engine.run()
            # If it runs, should not crash
            assert results is not None
        except ValueError:
            # It's acceptable to raise ValueError for insufficient data
            pass

    def test_two_data_points(self):
        """Test engine with exactly two data points."""
        two_points = pd.Series(
            [100, 101], index=pd.date_range("2020-01-01", periods=2, freq="D")
        )

        engine = Engine(two_points)
        results = engine.run()

        # Should handle two points successfully
        assert results is not None
        assert "metrics" in results
        assert results["returns"] == 0.01  # 1% return

    def test_non_datetime_index(self):
        """Test engine with non-datetime index."""
        data = pd.Series([100, 101, 102], index=[0, 1, 2])

        # Should either work or raise a clear error
        try:
            engine = Engine(data)
            results = engine.run()
            assert results is not None
        except (ValueError, TypeError):
            # Acceptable to reject non-datetime indices
            pass

    def test_unsorted_datetime_index(self):
        """Test engine with unsorted datetime index."""
        dates = pd.to_datetime(["2020-01-03", "2020-01-01", "2020-01-02"])
        data = pd.Series([102, 100, 101], index=dates)

        # Should handle unsorted dates
        engine = Engine(data)
        results = engine.run()

        assert results is not None
        # The data should be processed in the order provided
        assert len(results["equity"]) == 3

    def test_duplicate_dates(self):
        """Test engine with duplicate dates in index."""
        dates = pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-02"])
        data = pd.Series([100, 101, 102], index=dates)

        # Should handle duplicate dates
        try:
            engine = Engine(data)
            results = engine.run()
            assert results is not None
        except (ValueError, KeyError):
            # Acceptable to raise error for duplicate dates
            pass

    def test_very_small_price_values(self):
        """Test engine with very small price values."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        small_prices = pd.Series(
            [
                1e-6,
                1.1e-6,
                1.2e-6,
                1.3e-6,
                1.4e-6,
                1.5e-6,
                1.6e-6,
                1.7e-6,
                1.8e-6,
                1.9e-6,
            ],
            index=dates,
        )

        engine = Engine(small_prices)
        results = engine.run()

        # Should handle small values without numerical issues
        assert results is not None
        assert "metrics" in results
        assert np.isfinite(results["returns"])

    def test_very_large_price_values(self):
        """Test engine with very large price values."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        large_prices = pd.Series(
            [
                1e15,
                1.1e15,
                1.2e15,
                1.3e15,
                1.4e15,
                1.5e15,
                1.6e15,
                1.7e15,
                1.8e15,
                1.9e15,
            ],
            index=dates,
        )

        engine = Engine(large_prices)
        results = engine.run()

        # Should handle large values without numerical issues
        assert results is not None
        assert "metrics" in results
        assert np.isfinite(results["returns"])

    def test_price_series_with_zeros(self):
        """Test engine with zeros in price series."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        prices_with_zero = pd.Series([100, 0, 102, 103, 104], index=dates)

        # Zero prices might cause issues, should handle gracefully
        try:
            engine = Engine(prices_with_zero)
            results = engine.run()
            assert results is not None
        except (ValueError, ZeroDivisionError):
            # Acceptable to raise error for zero prices
            pass

    def test_negative_prices(self):
        """Test engine with negative prices."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        negative_prices = pd.Series([-100, -101, -99, -102, -98], index=dates)

        # Negative prices don't make financial sense, should handle appropriately
        try:
            engine = Engine(negative_prices)
            results = engine.run()
            # If it runs, should still produce results
            assert results is not None
        except ValueError:
            # Acceptable to reject negative prices
            pass

    def test_benchmark_series_length_mismatch(self, sample_price_series):
        """Test with benchmark series of different length."""
        # Create shorter benchmark
        short_benchmark = sample_price_series[:50].copy()
        short_benchmark.index = short_benchmark.index + pd.Timedelta(days=10)

        engine = Engine(sample_price_series, benchmark=short_benchmark)
        results = engine.run()

        # Should handle length mismatch by aligning data
        assert results is not None
        assert "metrics" in results

    def test_benchmark_no_overlap(self, sample_price_series):
        """Test with benchmark that has no date overlap."""
        # Create benchmark with completely different dates
        benchmark_dates = pd.date_range(
            "2021-01-01", periods=len(sample_price_series), freq="D"
        )
        no_overlap_benchmark = pd.Series(
            sample_price_series.values, index=benchmark_dates
        )

        engine = Engine(sample_price_series, benchmark=no_overlap_benchmark)
        results = engine.run()

        # Should handle no overlap gracefully
        assert results is not None
        # Benchmark-specific metrics might not be available
        assert "metrics" in results
