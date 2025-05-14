import pytest
import tempfile
import os
import json
import shutil
from algosystem.backtesting.engine import Engine
from algosystem.backtesting.dashboard.dashboard_generator import (
    generate_dashboard,
    generate_standalone_dashboard
)


class TestDashboardGeneration:
    """Test dashboard generation functionality."""
    
    def test_generate_basic_dashboard(self, sample_price_series, temp_directory):
        """Test basic dashboard generation."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        # Generate dashboard
        dashboard_path = generate_dashboard(
            engine, 
            output_dir=temp_directory,
            open_browser=False
        )
        
        # Check that files were created
        assert os.path.exists(dashboard_path)
        assert dashboard_path.endswith('dashboard.html')
        
        # Check that supporting files exist
        assert os.path.exists(os.path.join(temp_directory, 'dashboard_data.json'))
        assert os.path.exists(os.path.join(temp_directory, 'css', 'dashboard.css'))
        assert os.path.exists(os.path.join(temp_directory, 'js', 'dashboard.js'))
    
    def test_generate_dashboard_with_benchmark(self, sample_price_series, sample_benchmark_series, temp_directory):
        """Test dashboard generation with benchmark."""
        engine = Engine(sample_price_series, benchmark=sample_benchmark_series)
        results = engine.run()
        
        dashboard_path = generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        # Check that dashboard was created
        assert os.path.exists(dashboard_path)
        
        # Check that data includes benchmark information
        data_path = os.path.join(temp_directory, 'dashboard_data.json')
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        # Should include metrics and charts
        assert 'metrics' in data
        assert 'charts' in data
    
    def test_generate_standalone_dashboard(self, sample_price_series, temp_directory):
        """Test standalone dashboard generation."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        output_path = os.path.join(temp_directory, 'standalone_dashboard.html')
        
        dashboard_path = generate_standalone_dashboard(engine, output_path=output_path)
        
        # Check that file was created
        assert os.path.exists(dashboard_path)
        assert dashboard_path == output_path
        
        # Check that it's a single HTML file
        with open(dashboard_path, 'r') as f:
            content = f.read()
        
        # Should contain HTML, CSS, and JavaScript
        assert '<html' in content
        assert '<style>' in content or 'stylesheet' in content
        assert '<script>' in content or 'text/javascript' in content
    
    def test_generate_dashboard_with_custom_config(self, sample_price_series, temp_directory):
        """Test dashboard generation with custom configuration."""
        # Create a simple custom config
        custom_config = {
            "metrics": [
                {
                    "id": "total_return",
                    "type": "Percentage",
                    "title": "Total Return",
                    "value_key": "total_return",
                    "position": {"row": 0, "col": 0}
                }
            ],
            "charts": [
                {
                    "id": "equity_curve",
                    "type": "LineChart",
                    "title": "Equity Curve",
                    "data_key": "equity_curve",
                    "position": {"row": 1, "col": 0},
                    "config": {"y_axis_label": "Value"}
                }
            ],
            "layout": {
                "max_cols": 1,
                "title": "Test Dashboard"
            }
        }
        
        # Save config to file
        config_path = os.path.join(temp_directory, 'custom_config.json')
        with open(config_path, 'w') as f:
            json.dump(custom_config, f)
        
        # Generate dashboard with custom config
        engine = Engine(sample_price_series)
        results = engine.run()
        
        dashboard_path = generate_dashboard(
            engine,
            output_dir=temp_directory,
            config_path=config_path,
            open_browser=False
        )
        
        # Check that dashboard was created
        assert os.path.exists(dashboard_path)
    
    def test_engine_generate_dashboard_method(self, sample_price_series, temp_directory):
        """Test dashboard generation through Engine method."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        # Use Engine's method
        dashboard_path = engine.generate_dashboard(
            output_dir=temp_directory,
            open_browser=False
        )
        
        assert os.path.exists(dashboard_path)
    
    def test_engine_generate_standalone_method(self, sample_price_series, temp_directory):
        """Test standalone dashboard generation through Engine method."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        output_path = os.path.join(temp_directory, 'engine_standalone.html')
        
        # Use Engine's method
        dashboard_path = engine.generate_standalone_dashboard(output_path)
        
        assert os.path.exists(dashboard_path)
        assert dashboard_path == output_path
    
    def test_dashboard_data_content(self, sample_price_series, temp_directory):
        """Test that dashboard data contains expected content."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        dashboard_path = generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        # Load and check dashboard data
        data_path = os.path.join(temp_directory, 'dashboard_data.json')
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        # Check required sections
        assert 'metadata' in data
        assert 'metrics' in data
        assert 'charts' in data
        
        # Check metadata
        metadata = data['metadata']
        assert 'title' in metadata
        assert 'start_date' in metadata
        assert 'end_date' in metadata
        assert 'total_return' in metadata
        
        # Check that metrics is not empty
        assert len(data['metrics']) > 0
        
        # Check that charts is not empty
        assert len(data['charts']) > 0


class TestDashboardEdgeCases:
    """Test edge cases in dashboard generation."""
    
    def test_dashboard_with_no_results(self, sample_price_series, temp_directory):
        """Test dashboard generation when engine hasn't been run."""
        engine = Engine(sample_price_series)
        # Don't run the engine
        
        # Should either auto-run or raise appropriate error
        try:
            dashboard_path = generate_dashboard(
                engine,
                output_dir=temp_directory,
                open_browser=False
            )
            # If successful, check that files exist
            assert os.path.exists(dashboard_path)
        except ValueError as e:
            # Expected error for unrun engine
            assert "results" in str(e).lower()
    
    def test_dashboard_with_invalid_config(self, sample_price_series, temp_directory):
        """Test dashboard generation with invalid configuration."""
        # Create invalid config
        invalid_config = {
            "metrics": [],  # Empty metrics
            "charts": [],   # Empty charts
            # Missing layout
        }
        
        config_path = os.path.join(temp_directory, 'invalid_config.json')
        with open(config_path, 'w') as f:
            json.dump(invalid_config, f)
        
        engine = Engine(sample_price_series)
        results = engine.run()
        
        # Should handle invalid config gracefully or raise appropriate error
        try:
            dashboard_path = generate_dashboard(
                engine,
                output_dir=temp_directory,
                config_path=config_path,
                open_browser=False
            )
            # If it succeeds, check that files exist
            assert os.path.exists(dashboard_path)
        except (ValueError, KeyError):
            # Expected for invalid config
            pass
    
    def test_dashboard_with_nonexistent_config(self, sample_price_series, temp_directory):
        """Test dashboard generation with non-existent config file."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        nonexistent_config = os.path.join(temp_directory, 'nonexistent.json')
        
        # Should handle gracefully or use default config
        dashboard_path = generate_dashboard(
            engine,
            output_dir=temp_directory,
            config_path=nonexistent_config,
            open_browser=False
        )
        
        # Should still create dashboard (with default config)
        assert os.path.exists(dashboard_path)
    
    def test_dashboard_output_permissions(self, sample_price_series):
        """Test dashboard generation with permission issues."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        # Try to write to a read-only location (if possible)
        try:
            import stat
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create a read-only directory
                readonly_dir = os.path.join(tmpdir, 'readonly')
                os.makedirs(readonly_dir)
                os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                
                try:
                    dashboard_path = generate_dashboard(
                        engine,
                        output_dir=readonly_dir,
                        open_browser=False
                    )
                except (PermissionError, OSError):
                    # Expected error for permission issues
                    pass
                finally:
                    # Restore permissions for cleanup
                    os.chmod(readonly_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        except (ImportError, OSError):
            # Skip test if we can't create read-only directory
            pass
    
    def test_dashboard_with_extreme_data(self, temp_directory):
        """Test dashboard generation with extreme data values."""
        # Create data with extreme values
        import pandas as pd
        import numpy as np
        dates = pd.date_range('2020-01-01', periods=10, freq='D')
        extreme_data = pd.Series([1e-10, 1e10, 1e-5, 1e8, 0.001, 1e6, 1e-8, 1e9, 0.1, 1e7], index=dates)
        
        engine = Engine(extreme_data)
        results = engine.run()
        
        # Should handle extreme values without crashing
        dashboard_path = generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        assert os.path.exists(dashboard_path)
    
    def test_multiple_dashboard_generations(self, sample_price_series, temp_directory):
        """Test generating multiple dashboards in the same directory."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        # Generate first dashboard
        dashboard_path1 = generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        # Generate second dashboard (should overwrite)
        dashboard_path2 = generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        # Both should point to the same location
        assert dashboard_path1 == dashboard_path2
        assert os.path.exists(dashboard_path2)


class TestDashboardFiles:
    """Test individual dashboard files and components."""
    
    def test_html_file_structure(self, sample_price_series, temp_directory):
        """Test that generated HTML file has proper structure."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        dashboard_path = generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        # Read and check HTML content
        with open(dashboard_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Check for essential HTML elements
        assert '<!DOCTYPE html>' in html_content
        assert '<html' in html_content
        assert '<head>' in html_content
        assert '<body>' in html_content
        assert '</html>' in html_content
        
        # Check for dashboard-specific elements
        assert 'dashboard' in html_content.lower()
        assert 'chart' in html_content.lower()
        assert 'metric' in html_content.lower()
    
    def test_css_file_generation(self, sample_price_series, temp_directory):
        """Test that CSS file is generated properly."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        css_path = os.path.join(temp_directory, 'css', 'dashboard.css')
        assert os.path.exists(css_path)
        
        # Check CSS content
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Should contain CSS rules
        assert '{' in css_content and '}' in css_content
    
    def test_js_file_generation(self, sample_price_series, temp_directory):
        """Test that JavaScript files are generated properly."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        # Check for JavaScript files
        js_files = ['dashboard.js', 'chart_factory.js', 'metric_factory.js']
        
        for js_file in js_files:
            js_path = os.path.join(temp_directory, 'js', js_file)
            if os.path.exists(js_path):  # Some files might be auto-generated
                with open(js_path, 'r') as f:
                    js_content = f.read()
                
                # Should contain JavaScript code
                assert 'function' in js_content or 'var' in js_content or 'let' in js_content or 'const' in js_content
    
    def test_data_json_structure(self, sample_price_series, temp_directory):
        """Test the structure of dashboard data JSON."""
        engine = Engine(sample_price_series)
        results = engine.run()
        
        generate_dashboard(
            engine,
            output_dir=temp_directory,
            open_browser=False
        )
        
        data_path = os.path.join(temp_directory, 'dashboard_data.json')
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        # Check top-level structure
        assert isinstance(data, dict)
        assert 'metadata' in data
        assert 'metrics' in data
        assert 'charts' in data
        
        # Check metadata structure
        metadata = data['metadata']
        assert isinstance(metadata, dict)
        assert 'title' in metadata
        assert 'start_date' in metadata
        assert 'end_date' in metadata
        
        # Check metrics structure
        metrics = data['metrics']
        assert isinstance(metrics, dict)
        
        # Check charts structure
        charts = data['charts']
        assert isinstance(charts, dict)
        
        # Each metric should have required fields
        for metric_id, metric_data in metrics.items():
            assert 'title' in metric_data
            assert 'type' in metric_data
            assert 'value' in metric_data
        
        # Each chart should have required fields
        for chart_id, chart_data in charts.items():
            assert 'title' in chart_data
            assert 'type' in chart_data
            assert 'data' in chart_data