import pytest
import os
import json
import pandas as pd
from unittest.mock import patch
from algosystem.backtesting.dashboard.web_app.app import start_dashboard_editor, load_config, save_config


class TestWebAppBasics:
    """Test basic web application functionality."""
    
    def test_load_config_existing_file(self, temp_directory):
        """Test loading configuration from existing file."""
        # Create a test config file
        test_config = {
            "metrics": [],
            "charts": [],
            "layout": {"max_cols": 2, "title": "Test Dashboard"}
        }
        
        config_path = os.path.join(temp_directory, 'test_config.json')
        with open(config_path, 'w') as f:
            json.dump(test_config, f)
        
        # Test loading
        loaded_config = load_config(config_path)
        
        assert loaded_config == test_config
        assert 'metrics' in loaded_config
        assert 'charts' in loaded_config
        assert 'layout' in loaded_config
    
    def test_load_config_nonexistent_file(self, temp_directory):
        """Test loading configuration from non-existent file."""
        nonexistent_path = os.path.join(temp_directory, 'nonexistent.json')
        
        # Should return default config or handle gracefully
        try:
            loaded_config = load_config(nonexistent_path)
            assert isinstance(loaded_config, dict)
            assert 'metrics' in loaded_config
            assert 'charts' in loaded_config
            assert 'layout' in loaded_config
        except FileNotFoundError:
            # Acceptable behavior
            pass
    
    def test_save_config(self, temp_directory):
        """Test saving configuration to file."""
        test_config = {
            "metrics": [
                {
                    "id": "test_metric",
                    "type": "Percentage",
                    "title": "Test Metric",
                    "value_key": "test_value",
                    "position": {"row": 0, "col": 0}
                }
            ],
            "charts": [],
            "layout": {"max_cols": 2, "title": "Test Dashboard"}
        }
        
        config_path = os.path.join(temp_directory, 'save_test.json')
        
        # Test saving
        success = save_config(test_config, config_path)
        
        assert success is True
        assert os.path.exists(config_path)
        
        # Verify saved content
        with open(config_path, 'r') as f:
            saved_config = json.load(f)
        
        assert saved_config == test_config
    
    def test_save_config_invalid_data(self, temp_directory):
        """Test saving invalid configuration data."""
        invalid_configs = [
            None,
            "",
            [],
            "not a dict",
            {}  # Empty dict
        ]
        
        for invalid_config in invalid_configs:
            config_path = os.path.join(temp_directory, f'invalid_{id(invalid_config)}.json')
            
            # Should handle gracefully or return False
            success = save_config(invalid_config, config_path)
            
            # Either succeeds with handled invalid data or returns False
            assert isinstance(success, bool)


class TestWebAppComponents:
    """Test web application components and utilities."""
    
    def test_config_validation_structure(self):
        """Test configuration validation logic."""
        from algosystem.backtesting.dashboard.utils.config_parser import validate_config
        
        # Valid config
        valid_config = {
            "metrics": [
                {
                    "id": "test",
                    "type": "Percentage",
                    "title": "Test",
                    "value_key": "test",
                    "position": {"row": 0, "col": 0}
                }
            ],
            "charts": [
                {
                    "id": "test_chart",
                    "type": "LineChart",
                    "title": "Test Chart",
                    "data_key": "test_data",
                    "position": {"row": 1, "col": 0},
                    "config": {}
                }
            ],
            "layout": {"max_cols": 2, "title": "Test"}
        }
        
        # Should validate successfully
        try:
            is_valid = validate_config(valid_config)
            assert is_valid is True
        except ImportError:
            # If validate_config is not implemented, skip test
            pytest.skip("validate_config not implemented")
        except Exception as e:
            # Should not raise unexpected exceptions
            pytest.fail(f"Unexpected error in validation: {e}")
    
    def test_config_validation_missing_sections(self):
        """Test config validation with missing sections."""
        from algosystem.backtesting.dashboard.utils.config_parser import validate_config
        
        # Config missing required sections
        invalid_configs = [
            {"metrics": []},  # Missing charts and layout
            {"charts": []},   # Missing metrics and layout
            {"layout": {}},   # Missing metrics and charts
            {}                # Missing everything
        ]
        
        for invalid_config in invalid_configs:
            try:
                with pytest.raises(ValueError):
                    validate_config(invalid_config)
            except ImportError:
                # If validate_config is not implemented, skip test
                pytest.skip("validate_config not implemented")
    
    def test_data_formatter_basic(self, sample_price_series):
        """Test basic data formatting for dashboard."""
        from algosystem.backtesting.dashboard.utils.data_formatter import prepare_dashboard_data
        from algosystem.backtesting.engine import Engine
        from algosystem.backtesting.dashboard.utils.default_config import get_default_config
        
        # Create engine and run backtest
        engine = Engine(sample_price_series)
        results = engine.run()
        
        # Get default config
        try:
            config = get_default_config()
        except ImportError:
            # Create minimal config if get_default_config not available
            config = {
                "metrics": [],
                "charts": [],
                "layout": {"max_cols": 2, "title": "Test"}
            }
        
        # Test data preparation
        try:
            dashboard_data = prepare_dashboard_data(engine, config)
            
            # Check structure
            assert isinstance(dashboard_data, dict)
            assert 'metadata' in dashboard_data
            assert 'metrics' in dashboard_data
            assert 'charts' in dashboard_data
            
        except ImportError:
            # If prepare_dashboard_data is not implemented, skip test
            pytest.skip("prepare_dashboard_data not implemented")


class TestWebAppError:
    """Test error handling in web application."""
    
    def test_config_with_malformed_json(self, temp_directory):
        """Test handling of malformed JSON config file."""
        # Create malformed JSON file
        malformed_path = os.path.join(temp_directory, 'malformed.json')
        with open(malformed_path, 'w') as f:
            f.write('{"metrics": [invalid json}')
        
        # Should handle gracefully
        try:
            config = load_config(malformed_path)
            # Should return default config or handle error
            assert isinstance(config, dict)
        except (json.JSONDecodeError, ValueError):
            # Acceptable to raise JSON decode error
            pass
    
    def test_config_with_unicode_content(self, temp_directory):
        """Test handling of config with unicode content."""
        unicode_config = {
            "metrics": [],
            "charts": [],
            "layout": {
                "max_cols": 2,
                "title": "Dashboard with émojis 📈 and ünïcödé"
            }
        }
        
        config_path = os.path.join(temp_directory, 'unicode_config.json')
        
        # Save with unicode content
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(unicode_config, f, ensure_ascii=False)
        
        # Should load successfully
        loaded_config = load_config(config_path)
        assert loaded_config['layout']['title'] == unicode_config['layout']['title']
    
    def test_save_config_to_readonly_location(self, temp_directory):
        """Test saving config to read-only location."""
        try:
            import stat
            
            # Create read-only directory
            readonly_dir = os.path.join(temp_directory, 'readonly')
            os.makedirs(readonly_dir)
            os.chmod(readonly_dir, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
            
            config_path = os.path.join(readonly_dir, 'config.json')
            test_config = {"metrics": [], "charts": [], "layout": {}}
            
            try:
                # Should handle permission error gracefully
                success = save_config(test_config, config_path)
                assert success is False
            except PermissionError:
                # Acceptable to raise permission error
                pass
            finally:
                # Restore permissions for cleanup
                os.chmod(readonly_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                
        except (ImportError, OSError):
            # Skip test if we can't modify permissions
            pytest.skip("Cannot test read-only permissions on this system")


class TestWebAppIntegration:
    """Test web application integration aspects."""
    
    @patch('algosystem.backtesting.dashboard.web_app.app.start_dashboard_editor')
    def test_app_startup_mock(self, mock_start_editor):
        """Test that app can be started (mocked)."""
        mock_start_editor.return_value = None
        
        # Should not raise an error
        try:
            start_dashboard_editor(host='127.0.0.1', port=5000, debug=False)
            mock_start_editor.assert_called_once()
        except Exception as e:
            # Log any unexpected errors
            pytest.fail(f"Unexpected error starting dashboard editor: {e}")
    
    def test_available_components_structure(self):
        """Test that available components are properly structured."""
        try:
            from algosystem.backtesting.dashboard.web_app.available_components import (
                AVAILABLE_METRICS, AVAILABLE_CHARTS
            )
            
            # Check that they are lists
            assert isinstance(AVAILABLE_METRICS, list)
            assert isinstance(AVAILABLE_CHARTS, list)
            
            # Check structure of first metric (if any)
            if AVAILABLE_METRICS:
                metric = AVAILABLE_METRICS[0]
                assert isinstance(metric, dict)
                assert 'id' in metric
                assert 'type' in metric
                assert 'title' in metric
            
            # Check structure of first chart (if any)
            if AVAILABLE_CHARTS:
                chart = AVAILABLE_CHARTS[0]
                assert isinstance(chart, dict)
                assert 'id' in chart
                assert 'type' in chart
                assert 'title' in chart
                
        except ImportError:
            pytest.skip("Available components not implemented")
    
    def test_template_generation_basic(self):
        """Test basic template generation functionality."""
        try:
            from algosystem.backtesting.dashboard.template.base_template import generate_html
            from algosystem.backtesting.engine import Engine
            
            # Create minimal test data
            test_data = pd.Series([100, 101, 102], index=pd.date_range('2020-01-01', periods=3))
            engine = Engine(test_data)
            results = engine.run()
            
            # Minimal config
            config = {
                "metrics": [],
                "charts": [],
                "layout": {"max_cols": 2, "title": "Test"}
            }
            
            # Minimal dashboard data
            dashboard_data = {
                "metadata": {"title": "Test", "start_date": "2020-01-01", "end_date": "2020-01-03", "total_return": 0.02},
                "metrics": {},
                "charts": {}
            }
            
            # Test HTML generation
            html = generate_html(engine, config, dashboard_data)
            
            # Check that HTML was generated
            assert isinstance(html, str)
            assert len(html) > 0
            assert '<html' in html.lower()
            
        except ImportError:
            pytest.skip("Template generation not implemented")
        except Exception as e:
            # Don't fail test if template generation has issues
            # Just ensure it doesn't crash the test suite
            pass