"""
Complete tests for algosystem.api module.
"""

import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest
import pandas as pd
import numpy as np

from algosystem.api import AlgoSystem, quick_backtest
from algosystem.backtesting.engine import Engine


class TestAlgoSystemAPI:
    """Test the main AlgoSystem API class."""
    
    def test_run_backtest_basic(self, sample_price_series):
        """Test basic backtest functionality."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        
        assert isinstance(engine, Engine)
        assert engine.results is not None
        assert 'metrics' in engine.results
        assert 'equity' in engine.results
    
    def test_run_backtest_with_benchmark(self, sample_price_series, sample_benchmark_series):
        """Test backtest with benchmark."""
        engine = AlgoSystem.run_backtest(
            data=sample_price_series,
            benchmark=sample_benchmark_series
        )
        
        assert isinstance(engine, Engine)
        assert engine.benchmark_series is not None
        assert engine.results is not None
    
    def test_run_backtest_with_date_range(self, sample_price_series):
        """Test backtest with custom date range."""
        engine = AlgoSystem.run_backtest(
            data=sample_price_series,
            start_date='2020-01-15',
            end_date='2020-02-15'
        )
        
        assert isinstance(engine, Engine)
        assert engine.start_date == pd.to_datetime('2020-01-15')
        assert engine.end_date == pd.to_datetime('2020-02-15')
    
    def test_run_backtest_dataframe_input(self, sample_dataframe):
        """Test backtest with DataFrame input."""
        engine = AlgoSystem.run_backtest(
            data=sample_dataframe,
            price_column='Strategy'
        )
        
        assert isinstance(engine, Engine)
        assert engine.results is not None
    
    def test_run_backtest_invalid_input(self):
        """Test backtest with invalid input."""
        with pytest.raises((TypeError, ValueError)):
            AlgoSystem.run_backtest("invalid_data")
        
        with pytest.raises((TypeError, ValueError)):
            AlgoSystem.run_backtest(None)


class TestAlgoSystemResults:
    """Test AlgoSystem results handling."""
    
    def test_print_results_basic(self, sample_price_series, capsys):
        """Test basic results printing."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        
        # Should not raise an error
        AlgoSystem.print_results(engine)
        
        # Test passes if no exception was raised
        assert True
    
    def test_print_results_detailed(self, sample_price_series):
        """Test detailed results printing."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        
        # Should not raise an error
        AlgoSystem.print_results(engine, detailed=True)
        
        # Ensure no exception was raised
        assert True
    
    def test_print_results_no_results(self, sample_price_series):
        """Test printing results when no results available."""
        engine = Engine(sample_price_series)  # Don't run the backtest
        
        AlgoSystem.print_results(engine)
        
        # Should handle gracefully
        assert True
    
    def test_print_results_with_benchmark(self, sample_price_series, sample_benchmark_series):
        """Test printing results with benchmark metrics."""
        engine = AlgoSystem.run_backtest(
            data=sample_price_series,
            benchmark=sample_benchmark_series
        )
        
        AlgoSystem.print_results(engine, detailed=True)
        
        # Should include benchmark metrics
        assert True


class TestAlgoSystemDashboards:
    """Test dashboard generation functionality."""
    
    @patch('algosystem.backtesting.dashboard.dashboard_generator.generate_dashboard')
    def test_generate_dashboard_basic(self, mock_generate, sample_price_series):
        """Test basic dashboard generation."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        mock_generate.return_value = '/fake/path/dashboard.html'
        
        result = AlgoSystem.generate_dashboard(engine)
        
        assert result == '/fake/path/dashboard.html'
        mock_generate.assert_called_once()
    
    @patch('algosystem.backtesting.dashboard.dashboard_generator.generate_standalone_dashboard')
    def test_generate_standalone_dashboard(self, mock_generate, sample_price_series):
        """Test standalone dashboard generation."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        mock_generate.return_value = '/fake/path/standalone.html'
        
        result = AlgoSystem.generate_standalone_dashboard(engine)
        
        assert result == '/fake/path/standalone.html'
        mock_generate.assert_called_once()
    
    def test_generate_dashboard_no_results(self, sample_price_series):
        """Test dashboard generation when no results."""
        engine = Engine(sample_price_series)  # Don't run backtest
        
        # Should auto-run the backtest
        with patch('algosystem.backtesting.dashboard.dashboard_generator.generate_dashboard') as mock_generate:
            mock_generate.return_value = '/fake/path/dashboard.html'
            result = AlgoSystem.generate_dashboard(engine)
            
            assert engine.results is not None  # Should have been run
            assert result == '/fake/path/dashboard.html'


class TestAlgoSystemDataExport:
    """Test data export functionality."""
    
    def test_export_data_csv(self, sample_price_series, temp_directory):
        """Test CSV data export."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        output_path = os.path.join(temp_directory, 'test_export.csv')
        
        result = AlgoSystem.export_data(engine, output_path, format='csv')
        
        assert result == output_path
        assert os.path.exists(output_path)
        
        # Verify the exported data
        exported_df = pd.read_csv(output_path, index_col=0, parse_dates=True)
        assert 'equity' in exported_df.columns
        assert len(exported_df) > 0
    
    def test_export_data_excel(self, sample_price_series, temp_directory):
        """Test Excel data export."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        output_path = os.path.join(temp_directory, 'test_export.xlsx')
        
        result = AlgoSystem.export_data(engine, output_path, format='excel')
        
        assert result == output_path
        assert os.path.exists(output_path)
        
        # Verify the exported data
        exported_df = pd.read_excel(output_path, index_col=0)
        assert 'equity' in exported_df.columns
        assert len(exported_df) > 0
    
    def test_export_data_invalid_format(self, sample_price_series, temp_directory):
        """Test data export with invalid format."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        output_path = os.path.join(temp_directory, 'test_export.txt')
        
        with pytest.raises(ValueError):
            AlgoSystem.export_data(engine, output_path, format='invalid')
    
    def test_export_data_no_results(self, sample_price_series, temp_directory):
        """Test data export when no results available."""
        engine = Engine(sample_price_series)  # Don't run backtest
        output_path = os.path.join(temp_directory, 'test_export.csv')
        
        result = AlgoSystem.export_data(engine, output_path)
        
        assert result is None  # Should return None when no results
    
    @patch('matplotlib.pyplot.savefig')
    @patch('matplotlib.pyplot.show')
    @patch('matplotlib.pyplot.close')
    def test_export_charts(self, mock_close, mock_show, mock_savefig, sample_price_series, temp_directory):
        """Test chart export functionality."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        
        result = AlgoSystem.export_charts(engine, output_dir=temp_directory)
        
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should have called savefig for each chart
        assert mock_savefig.call_count > 0
    
    def test_export_charts_no_results(self, sample_price_series, temp_directory):
        """Test chart export when no results available."""
        engine = Engine(sample_price_series)  # Don't run backtest
        
        result = AlgoSystem.export_charts(engine, output_dir=temp_directory)
        
        assert result == []  # Should return empty list when no results


class TestAlgoSystemConfiguration:
    """Test configuration management."""
    
    def test_load_config_default(self):
        """Test loading default configuration."""
        config = AlgoSystem.load_config()
        
        assert isinstance(config, dict)
        assert 'metrics' in config
        assert 'charts' in config
        assert 'layout' in config
    
    def test_load_config_from_file(self, temp_directory):
        """Test loading configuration from file."""
        test_config = {
            'metrics': [],
            'charts': [],
            'layout': {'max_cols': 2, 'title': 'Test'}
        }
        
        config_path = os.path.join(temp_directory, 'test_config.json')
        with open(config_path, 'w') as f:
            json.dump(test_config, f)
        
        config = AlgoSystem.load_config(config_path)
        
        assert config == test_config
    
    def test_load_config_invalid_file(self, temp_directory):
        """Test loading configuration from invalid file."""
        config_path = os.path.join(temp_directory, 'nonexistent.json')
        
        # Should fall back to default config
        config = AlgoSystem.load_config(config_path)
        
        assert isinstance(config, dict)
        assert 'metrics' in config
    
    def test_save_config(self, temp_directory):
        """Test saving configuration."""
        test_config = {
            'metrics': [],
            'charts': [],
            'layout': {'max_cols': 2, 'title': 'Test'}
        }
        
        config_path = os.path.join(temp_directory, 'saved_config.json')
        result = AlgoSystem.save_config(test_config, config_path)
        
        assert result == config_path
        assert os.path.exists(config_path)
        
        # Verify saved content
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config == test_config
    
    def test_save_config_default_location(self):
        """Test saving configuration to default location."""
        test_config = {
            'metrics': [],
            'charts': [],
            'layout': {'max_cols': 2, 'title': 'Test'}
        }
        
        with patch('os.makedirs'), patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            result = AlgoSystem.save_config(test_config)
            
            assert result is not None
            mock_open.assert_called_once()


class TestAlgoSystemBenchmarks:
    """Test benchmark integration."""
    
    @patch('algosystem.data.benchmark.fetch_benchmark_data')
    def test_get_benchmark(self, mock_fetch):
        """Test getting benchmark data."""
        mock_data = pd.Series([100, 101, 102], index=pd.date_range('2020-01-01', periods=3))
        mock_fetch.return_value = mock_data
        
        result = AlgoSystem.get_benchmark('sp500')
        
        assert isinstance(result, pd.Series)
        assert len(result) == 3
        mock_fetch.assert_called_once_with('sp500', None, None)
    
    @patch('algosystem.api.get_benchmark_list')
    @patch('algosystem.api.get_benchmark_info')
    def test_list_benchmarks(self, mock_info, mock_list):
        """Test listing benchmarks."""
        mock_list.return_value = ['sp500', 'nasdaq']
        mock_info.return_value = pd.DataFrame({
            'Alias': ['sp500', 'nasdaq'],
            'Category': ['Indices', 'Indices'],
            'Description': ['S&P 500', 'NASDAQ']
        })
        
        result = AlgoSystem.list_benchmarks()
        
        assert result == ['sp500', 'nasdaq']
        mock_list.assert_called_once()
        mock_info.assert_called_once()
    
    @patch('algosystem.api.compare_benchmarks')
    @patch('matplotlib.pyplot.show')
    def test_compare_benchmarks(self, mock_show, mock_compare):
        """Test comparing benchmarks."""
        mock_data = pd.DataFrame({
            'sp500': [100, 101, 102],
            'nasdaq': [100, 102, 104]
        }, index=pd.date_range('2020-01-01', periods=3))
        mock_compare.return_value = mock_data
        
        result = AlgoSystem.compare_benchmarks(['sp500', 'nasdaq'], plot=True)
        
        assert isinstance(result, pd.DataFrame)
        assert 'sp500' in result.columns
        assert 'nasdaq' in result.columns
        mock_compare.assert_called_once()
        mock_show.assert_called_once()


class TestQuickBacktest:
    """Test the quick_backtest convenience function."""
    
    def test_quick_backtest_basic(self, sample_price_series):
        """Test basic quick backtest."""
        with patch('algosystem.api.AlgoSystem.print_results') as mock_print:
            engine = quick_backtest(sample_price_series)
            
            assert isinstance(engine, Engine)
            assert engine.results is not None
            mock_print.assert_called_once_with(engine)
    
    def test_quick_backtest_with_benchmark(self, sample_price_series, sample_benchmark_series):
        """Test quick backtest with benchmark."""
        with patch('algosystem.api.AlgoSystem.print_results') as mock_print:
            engine = quick_backtest(sample_price_series, benchmark=sample_benchmark_series)
            
            assert isinstance(engine, Engine)
            assert engine.benchmark_series is not None
            mock_print.assert_called_once_with(engine)
    
    def test_quick_backtest_with_kwargs(self, sample_price_series):
        """Test quick backtest with additional kwargs."""
        with patch('algosystem.api.AlgoSystem.print_results') as mock_print:
            engine = quick_backtest(
                sample_price_series,
                start_date='2020-01-15',
                initial_capital=50000
            )
            
            assert isinstance(engine, Engine)
            assert engine.initial_capital == 50000
            mock_print.assert_called_once_with(engine)


class TestAlgoSystemErrorHandling:
    """Test error handling and edge cases."""
    
    def test_export_charts_with_benchmark(self, sample_price_series, sample_benchmark_series, temp_directory):
        """Test chart export with benchmark data."""
        engine = AlgoSystem.run_backtest(sample_price_series, benchmark=sample_benchmark_series)
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig, \
             patch('matplotlib.pyplot.show'), \
             patch('matplotlib.pyplot.close'):
            
            result = AlgoSystem.export_charts(engine, output_dir=temp_directory)
            
            assert isinstance(result, list)
            assert len(result) > 0
            # Should include benchmark comparison chart
            assert any('benchmark' in path.lower() for path in result)
    
    def test_config_with_malformed_json(self, temp_directory):
        """Test loading malformed JSON config."""
        config_path = os.path.join(temp_directory, 'malformed.json')
        with open(config_path, 'w') as f:
            f.write('{"invalid": json}')
        
        # Should fall back to default config
        config = AlgoSystem.load_config(config_path)
        
        assert isinstance(config, dict)
        assert 'metrics' in config
    
    def test_save_config_permission_error(self, temp_directory):
        """Test saving config with permission error."""
        test_config = {'test': 'config'}
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = AlgoSystem.save_config(test_config, '/invalid/path/config.json')
            
            assert result is None
    
    def test_export_data_with_minimal_results(self, temp_directory):
        """Test data export with minimal backtest results."""
        # Create minimal price series
        minimal_data = pd.Series([100, 101], index=pd.date_range('2020-01-01', periods=2))
        engine = AlgoSystem.run_backtest(minimal_data)
        
        output_path = os.path.join(temp_directory, 'minimal_export.csv')
        result = AlgoSystem.export_data(engine, output_path)
        
        assert result == output_path
        assert os.path.exists(output_path)
    
    def test_benchmark_comparison_empty_list(self):
        """Test benchmark comparison with empty list."""
        with patch('algosystem.api.compare_benchmarks') as mock_compare:
            mock_compare.side_effect = ValueError("Empty benchmark list")
            
            with pytest.raises(ValueError):
                AlgoSystem.compare_benchmarks([])


class TestAlgoSystemIntegration:
    """Test integration scenarios."""
    
    def test_complete_workflow(self, sample_price_series, temp_directory):
        """Test complete workflow from backtest to export."""
        # Step 1: Run backtest
        engine = AlgoSystem.run_backtest(sample_price_series)
        
        # Step 2: Export data
        data_path = os.path.join(temp_directory, 'workflow_data.csv')
        data_result = AlgoSystem.export_data(engine, data_path)
        
        # Step 3: Export charts
        with patch('matplotlib.pyplot.savefig'), \
             patch('matplotlib.pyplot.show'), \
             patch('matplotlib.pyplot.close'):
            charts_result = AlgoSystem.export_charts(engine, temp_directory)
        
        # Step 4: Generate dashboard
        with patch('algosystem.backtesting.dashboard.dashboard_generator.generate_dashboard') as mock_dashboard:
            mock_dashboard.return_value = '/fake/dashboard.html'
            dashboard_result = AlgoSystem.generate_dashboard(engine)
        
        # Verify all steps completed
        assert data_result == data_path
        assert isinstance(charts_result, list)
        assert dashboard_result == '/fake/dashboard.html'
    
    def test_workflow_with_custom_config(self, sample_price_series, temp_directory):
        """Test workflow with custom configuration."""
        # Create custom config
        custom_config = {
            'metrics': [
                {
                    'id': 'total_return',
                    'type': 'Percentage',
                    'title': 'Total Return',
                    'value_key': 'total_return',
                    'position': {'row': 0, 'col': 0}
                }
            ],
            'charts': [],
            'layout': {'max_cols': 1, 'title': 'Custom Dashboard'}
        }
        
        config_path = os.path.join(temp_directory, 'custom_config.json')
        config_result = AlgoSystem.save_config(custom_config, config_path)
        
        # Load and verify config
        loaded_config = AlgoSystem.load_config(config_path)
        
        assert config_result == config_path
        assert loaded_config == custom_config
    
    def test_multiple_backtests_comparison(self, sample_price_series, sample_benchmark_series):
        """Test running and comparing multiple backtests."""
        # Run multiple backtests
        engine1 = AlgoSystem.run_backtest(sample_price_series)
        engine2 = AlgoSystem.run_backtest(sample_benchmark_series)
        
        # Compare results
        metrics1 = engine1.get_metrics()
        metrics2 = engine2.get_metrics()
        
        assert isinstance(metrics1, dict)
        assert isinstance(metrics2, dict)
        assert 'total_return' in metrics1
        assert 'total_return' in metrics2
        
        # Results should be different (different data)
        assert metrics1['total_return'] != metrics2['total_return']


class TestAlgoSystemPerformance:
    """Test performance aspects of API."""
    
    def test_large_dataset_handling(self):
        """Test API with large dataset."""
        # Create large dataset
        dates = pd.date_range('2020-01-01', periods=2000, freq='D')
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, 2000)
        large_data = pd.Series(100 * (1 + pd.Series(returns)).cumprod(), index=dates)
        
        # Should handle large dataset without issues
        engine = AlgoSystem.run_backtest(large_data)
        
        assert engine.results is not None
        assert len(engine.results['equity']) == len(large_data)
    
    def test_multiple_chart_export_performance(self, sample_price_series, temp_directory):
        """Test performance of exporting multiple charts."""
        engine = AlgoSystem.run_backtest(sample_price_series)
        
        import time
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig, \
             patch('matplotlib.pyplot.show'), \
             patch('matplotlib.pyplot.close'):
            
            start_time = time.time()
            result = AlgoSystem.export_charts(engine, temp_directory)
            end_time = time.time()
            
            # Should complete reasonably quickly
            assert (end_time - start_time) < 10  # Less than 10 seconds
            assert len(result) > 0
            assert mock_savefig.call_count > 0


if __name__ == "__main__":
    pytest.main([__file__])