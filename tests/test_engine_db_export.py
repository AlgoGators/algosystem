from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from algosystem.backtesting.engine import Engine


class TestEngineDBExport:
    """Test cases for the Engine database export functionality."""

    @pytest.fixture
    def sample_price_series(self):
        """Create a sample price series for testing."""
        dates = pd.date_range("2022-01-01", periods=100, freq="D")
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 100)
        prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
        prices.name = "Test Strategy"
        return prices

    @patch("algosystem.data.connectors.inserter.Inserter")
    def test_export_db_basic(self, mock_inserter_class, sample_price_series):
        """Test basic database export functionality."""
        # Setup mock inserter
        mock_inserter = MagicMock()
        mock_inserter_class.return_value = mock_inserter
        mock_inserter.get_next_run_id.return_value = 123
        mock_inserter.export_backtest_results.return_value = 123

        # Run backtest
        engine = Engine(sample_price_series)
        results = engine.run()

        # Export to database
        run_id = engine.export_db()

        # Verify the mocked methods were called correctly
        mock_inserter_class.assert_called_once()
        mock_inserter.get_next_run_id.assert_called_once()
        mock_inserter.export_backtest_results.assert_called_once()
        assert run_id == 123  # Verify the returned run_id

        # Check that the export_backtest_results method was called with the right arguments
        call_args = mock_inserter.export_backtest_results.call_args[1]
        assert call_args["run_id"] == 123
        assert isinstance(call_args["equity_curve"], pd.Series)
        assert isinstance(call_args["metrics"], dict)
        assert isinstance(call_args["config"], dict)

    @patch("algosystem.data.connectors.inserter.Inserter")
    def test_export_db_with_custom_run_id(
        self, mock_inserter_class, sample_price_series
    ):
        """Test database export with custom run_id."""
        # Setup mock inserter
        mock_inserter = MagicMock()
        mock_inserter_class.return_value = mock_inserter
        mock_inserter.export_backtest_results.return_value = 456

        # Run backtest
        engine = Engine(sample_price_series)
        results = engine.run()

        # Export to database with custom run_id
        custom_run_id = 456
        run_id = engine.export_db(run_id=custom_run_id)

        # Verify the mocked methods were called correctly
        mock_inserter_class.assert_called_once()
        mock_inserter.get_next_run_id.assert_not_called()  # Should not be called when run_id is provided
        mock_inserter.export_backtest_results.assert_called_once()
        assert run_id == 456  # Verify the returned run_id

        # Check that the export_backtest_results method was called with the right arguments
        call_args = mock_inserter.export_backtest_results.call_args[1]
        assert call_args["run_id"] == 456
        assert isinstance(call_args["equity_curve"], pd.Series)
        assert isinstance(call_args["metrics"], dict)
        assert isinstance(call_args["config"], dict)

    @patch("algosystem.data.connectors.inserter.Inserter")
    def test_export_db_with_no_results(self, mock_inserter_class, sample_price_series):
        """Test database export when no results are available."""
        # Setup mock inserter
        mock_inserter = MagicMock()
        mock_inserter_class.return_value = mock_inserter
        mock_inserter.get_next_run_id.return_value = 789
        mock_inserter.export_backtest_results.return_value = 789

        # Create engine but don't run backtest
        engine = Engine(sample_price_series)

        # Mock the run method so it doesn't actually run
        engine.run = MagicMock(return_value=None)
        engine.results = None

        # Export should raise a ValueError when no results available
        with pytest.raises(ValueError):
            engine.export_db()

        # The run method should have been called
        engine.run.assert_called_once()

    @patch("algosystem.data.connectors.inserter.Inserter")
    def test_export_db_with_positions_and_pnl(
        self, mock_inserter_class, sample_price_series
    ):
        """Test database export with positions and symbol PnL data."""
        # Setup mock inserter
        mock_inserter = MagicMock()
        mock_inserter_class.return_value = mock_inserter
        mock_inserter.get_next_run_id.return_value = 123
        mock_inserter.export_backtest_results.return_value = 123

        # Run backtest
        engine = Engine(sample_price_series)
        results = engine.run()

        # Add mock positions and symbol_pnl data
        positions_data = {
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "quantity": [100, 50, 75],
            "average_price": [150.0, 300.0, 2500.0],
            "unrealized_pnl": [5000.0, 2500.0, 7500.0],
            "realized_pnl": [1000.0, 500.0, 1500.0],
        }
        engine.positions = pd.DataFrame(positions_data)

        pnl_data = {
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "pnl": [6000.0, 3000.0, 9000.0],
        }
        engine.symbol_pnl = pd.DataFrame(pnl_data)

        # Export to database
        run_id = engine.export_db()

        # Verify the mocked methods were called correctly
        mock_inserter_class.assert_called_once()
        mock_inserter.get_next_run_id.assert_called_once()
        mock_inserter.export_backtest_results.assert_called_once()
        assert run_id == 123  # Verify the returned run_id

        # Check that the export_backtest_results method was called with the right arguments
        call_args = mock_inserter.export_backtest_results.call_args[1]
        assert call_args["run_id"] == 123
        assert isinstance(call_args["equity_curve"], pd.Series)
        assert isinstance(call_args["final_positions"], pd.DataFrame)
        assert isinstance(call_args["symbol_pnl"], pd.DataFrame)
        assert isinstance(call_args["metrics"], dict)
        assert isinstance(call_args["config"], dict)

    def test_export_db_import_error(self, sample_price_series):
        """Test handling of missing psycopg2 dependency."""
        # Run backtest
        engine = Engine(sample_price_series)
        results = engine.run()

        # Mock import error
        with patch(
            "builtins.__import__", side_effect=ImportError("No module named 'psycopg2'")
        ):
            with pytest.raises(ImportError):
                engine.export_db()

    @patch("algosystem.data.connectors.inserter.Inserter")
    def test_export_db_exclude_positions_and_pnl(
        self, mock_inserter_class, sample_price_series
    ):
        """Test database export with positions and symbol PnL excluded."""
        # Setup mock inserter
        mock_inserter = MagicMock()
        mock_inserter_class.return_value = mock_inserter
        mock_inserter.get_next_run_id.return_value = 123
        mock_inserter.export_backtest_results.return_value = 123

        # Run backtest
        engine = Engine(sample_price_series)
        results = engine.run()

        # Add mock positions and symbol_pnl data
        positions_data = {
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "quantity": [100, 50, 75],
            "average_price": [150.0, 300.0, 2500.0],
            "unrealized_pnl": [5000.0, 2500.0, 7500.0],
            "realized_pnl": [1000.0, 500.0, 1500.0],
        }
        engine.positions = pd.DataFrame(positions_data)

        pnl_data = {
            "symbol": ["AAPL", "MSFT", "GOOGL"],
            "pnl": [6000.0, 3000.0, 9000.0],
        }
        engine.symbol_pnl = pd.DataFrame(pnl_data)

        # Export to database with positions and PnL excluded
        run_id = engine.export_db(include_positions=False, include_pnl=False)

        # Check that the export_backtest_results method was called with the right arguments
        call_args = mock_inserter.export_backtest_results.call_args[1]
        assert call_args["run_id"] == 123
        assert isinstance(call_args["equity_curve"], pd.Series)
        assert (
            call_args["final_positions"] is None
        )  # Should be None when positions are excluded
        assert call_args["symbol_pnl"] is None  # Should be None when PnL is excluded
