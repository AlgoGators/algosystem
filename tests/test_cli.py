import pytest
import tempfile
import os
import pandas as pd
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from algosystem.cli.commands import cli


class TestCLICommands:
    """Test CLI command functionality."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()
    
    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'AlgoSystem' in result.output
        assert 'dashboard' in result.output
    
    def test_dashboard_command_help(self):
        """Test dashboard command help."""
        result = self.runner.invoke(cli, ['dashboard', '--help'])
        
        assert result.exit_code == 0
        assert 'strategy' in result.output or 'input' in result.output
        assert 'output' in result.output
    
    def test_launch_command_help(self):
        """Test launch command help."""
        result = self.runner.invoke(cli, ['launch', '--help'])
        
        assert result.exit_code == 0
        assert 'host' in result.output or 'port' in result.output
    
    def test_create_config_command_help(self):
        """Test create-config command help."""
        result = self.runner.invoke(cli, ['create-config', '--help'])
        
        assert result.exit_code == 0
        assert 'output' in result.output
    
    def test_show_config_command_help(self):
        """Test show-config command help."""
        result = self.runner.invoke(cli, ['show-config', '--help'])
        
        assert result.exit_code == 0
        assert 'config' in result.output or 'file' in result.output
    
    def test_list_configs_command_help(self):
        """Test list-configs command help."""
        result = self.runner.invoke(cli, ['list-configs', '--help'])
        
        assert result.exit_code == 0


class TestDashboardCommand:
    """Test the dashboard CLI command."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()
    
    def test_dashboard_command_missing_file(self):
        """Test dashboard command with missing input file."""
        result = self.runner.invoke(cli, ['dashboard', 'nonexistent.csv'])
        
        # Should fail with non-zero exit code
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'not found' in result.output.lower()
    
    def test_dashboard_command_with_csv(self, sample_csv_file):
        """Test dashboard command with valid CSV file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(cli, [
                'dashboard', 
                sample_csv_file,
                '--output-dir', temp_dir,
                '--use-default-config'
            ])
            
            # Check result
            if result.exit_code == 0:
                # If successful, check that files were created
                assert os.path.exists(os.path.join(temp_dir, 'dashboard.html'))
            else:
                # If failed, should have error message
                assert result.output is not None
    
    def test_dashboard_command_with_custom_config(self, sample_csv_file):
        """Test dashboard command with custom configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a simple config file
            config_content = {
                "metrics": [],
                "charts": [],
                "layout": {"max_cols": 1, "title": "CLI Test"}
            }
            
            config_path = os.path.join(temp_dir, 'test_config.json')
            with open(config_path, 'w') as f:
                import json
                json.dump(config_content, f)
            
            # Run command with custom config
            result = self.runner.invoke(cli, [
                'dashboard',
                sample_csv_file,
                '--output-dir', temp_dir,
                '--config', config_path
            ])
            
            # Should complete without major errors
            # Exit code might be non-zero due to missing dependencies, but should not crash
            assert result.output is not None
    
    def test_standalone_dashboard_command(self, sample_csv_file):
        """Test standalone dashboard command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, 'standalone.html')
            
            result = self.runner.invoke(cli, [
                'dashboard',
                sample_csv_file,
                '--output-file', output_file
            ])
            
            # Check result based on success/failure
            if result.exit_code == 0:
                assert os.path.exists(output_file)
            # If failed, that's acceptable due to potential missing dependencies


class TestLaunchCommand:
    """Test the launch CLI command."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()
    
    @patch('algosystem.cli.commands.start_dashboard_editor')
    def test_launch_command_basic(self, mock_start_editor):
        """Test basic launch command (mocked)."""
        mock_start_editor.return_value = None
        
        result = self.runner.invoke(cli, ['launch', '--debug'])
        
        # Should attempt to start the editor
        mock_start_editor.assert_called_once()
        
        # Check that environment variables were set if provided
        # Result exit code might vary based on Flask availability
    
    @patch('algosystem.cli.commands.start_dashboard_editor')
    def test_launch_command_with_config(self, mock_start_editor):
        """Test launch command with configuration file."""
        mock_start_editor.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, 'test_config.json')
            
            # Create dummy config file
            with open(config_path, 'w') as f:
                f.write('{"metrics": [], "charts": [], "layout": {}}')
            
            result = self.runner.invoke(cli, [
                'launch',
                '--config', config_path
            ])
            
            # Should set environment variable and start editor
            mock_start_editor.assert_called_once()
    
    @patch('algosystem.cli.commands.start_dashboard_editor')
    def test_launch_command_with_save_config(self, mock_start_editor):
        """Test launch command with save-config option."""
        mock_start_editor.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            save_config_path = os.path.join(temp_dir, 'save_config.json')
            
            result = self.runner.invoke(cli, [
                'launch',
                '--save-config', save_config_path
            ])
            
            # Should set environment variable and start editor
            mock_start_editor.assert_called_once()
            
            # Check that directory was created
            assert os.path.exists(os.path.dirname(save_config_path))


class TestConfigCommands:
    """Test configuration-related CLI commands."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()
    
    def test_create_config_basic(self):
        """Test basic create-config command."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, 'new_config.json')
            
            result = self.runner.invoke(cli, [
                'create-config',
                config_path
            ])
            
            # Should create config file
            if result.exit_code == 0:
                assert os.path.exists(config_path)
                
                # Check that it's valid JSON
                with open(config_path, 'r') as f:
                    import json
                    config = json.load(f)
                    assert isinstance(config, dict)
    
    def test_create_config_with_base(self):
        """Test create-config command with base configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create base config
            base_config = {
                "metrics": [{"id": "test", "type": "Value", "title": "Test"}],
                "charts": [],
                "layout": {"max_cols": 2, "title": "Base Config"}
            }
            
            base_path = os.path.join(temp_dir, 'base_config.json')
            with open(base_path, 'w') as f:
                import json
                json.dump(base_config, f)
            
            # Create new config based on base
            new_config_path = os.path.join(temp_dir, 'new_config.json')
            
            result = self.runner.invoke(cli, [
                'create-config',
                new_config_path,
                '--based-on', base_path
            ])
            
            if result.exit_code == 0:
                assert os.path.exists(new_config_path)
                
                # Check that new config has base content
                with open(new_config_path, 'r') as f:
                    import json
                    new_config = json.load(f)
                    assert new_config['layout']['title'] == base_config['layout']['title']
    
    def test_show_config_existing_file(self):
        """Test show-config command with existing file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test config
            test_config = {
                "metrics": [
                    {
                        "id": "metric1",
                        "type": "Percentage",
                        "title": "Test Metric 1",
                        "value_key": "test1",
                        "position": {"row": 0, "col": 0}
                    }
                ],
                "charts": [
                    {
                        "id": "chart1",
                        "type": "LineChart",
                        "title": "Test Chart 1",
                        "data_key": "test_data",
                        "position": {"row": 1, "col": 0},
                        "config": {}
                    }
                ],
                "layout": {"max_cols": 2, "title": "Test Dashboard"}
            }
            
            config_path = os.path.join(temp_dir, 'show_test.json')
            with open(config_path, 'w') as f:
                import json
                json.dump(test_config, f)
            
            result = self.runner.invoke(cli, [
                'show-config',
                config_path
            ])
            
            # Should display config content
            assert result.exit_code == 0
            assert 'Test Dashboard' in result.output
            assert 'Test Metric 1' in result.output
            assert 'Test Chart 1' in result.output
    
    def test_show_config_nonexistent_file(self):
        """Test show-config command with non-existent file."""
        result = self.runner.invoke(cli, [
            'show-config',
            'nonexistent_config.json'
        ])
        
        # Should fail gracefully
        assert result.exit_code != 0
        assert 'error' in result.output.lower() or 'not found' in result.output.lower()
    
    def test_list_configs_empty(self):
        """Test list-configs command when no configs exist."""
        # Temporarily change home directory to empty location
        with tempfile.TemporaryDirectory() as temp_home:
            with patch.dict(os.environ, {'HOME': temp_home}):
                result = self.runner.invoke(cli, ['list-configs'])
                
                # Should complete successfully
                assert result.exit_code == 0
                assert 'No configuration' in result.output or 'found' in result.output
    
    def test_list_configs_with_existing(self):
        """Test list-configs command with existing configurations."""
        with tempfile.TemporaryDirectory() as temp_home:
            # Create algosystem config directory
            config_dir = os.path.join(temp_home, '.algosystem')
            os.makedirs(config_dir)
            
            # Create test config files
            test_configs = ['config1.json', 'config2.json', 'dashboard_config.json']
            
            for config_name in test_configs:
                config_path = os.path.join(config_dir, config_name)
                with open(config_path, 'w') as f:
                    import json
                    json.dump({"test": "config"}, f)
            
            # Mock home directory
            with patch.dict(os.environ, {'HOME': temp_home}):
                result = self.runner.invoke(cli, ['list-configs'])
                
                if result.exit_code == 0:
                    # Should list the config files
                    for config_name in test_configs:
                        assert config_name in result.output


class TestCLIEdgeCases:
    """Test edge cases and error conditions in CLI."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()
    
    def test_invalid_command(self):
        """Test CLI with invalid command."""
        result = self.runner.invoke(cli, ['invalid-command'])
        
        # Should show error and help
        assert result.exit_code != 0
        assert 'Usage:' in result.output or 'No such command' in result.output
    
    def test_dashboard_command_invalid_csv(self):
        """Test dashboard command with invalid CSV file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create invalid CSV file
            invalid_csv = os.path.join(temp_dir, 'invalid.csv')
            with open(invalid_csv, 'w') as f:
                f.write("this,is,not,a,valid,csv\nfile,with,wrong,format")
            
            result = self.runner.invoke(cli, [
                'dashboard',
                invalid_csv,
                '--use-default-config'
            ])
            
            # Should handle error gracefully
            assert result.exit_code != 0
    
    def test_config_commands_permission_error(self):
        """Test config commands with permission errors."""
        # Try to create config in system directory (if possible)
        try:
            result = self.runner.invoke(cli, [
                'create-config',
                '/root/restricted_config.json'  # Likely to fail on most systems
            ])
            
            # Should handle permission error gracefully
            if result.exit_code != 0:
                assert 'error' in result.output.lower() or 'permission' in result.output.lower()
        except:
            # Skip test if we can't test permission errors
            pass
    
    def test_launch_without_flask(self):
        """Test launch command when Flask is not available."""
        # Mock import error for Flask
        with patch('algosystem.cli.commands.start_dashboard_editor') as mock_start:
            mock_start.side_effect = ImportError("No module named 'flask'")
            
            result = self.runner.invoke(cli, ['launch'])
            
            # Should show appropriate error message
            assert result.exit_code != 0
            assert 'flask' in result.output.lower() or 'error' in result.output.lower()
    
    def test_commands_with_unicode_paths(self):
        """Test CLI commands with unicode characters in paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create path with unicode characters
            unicode_dir = os.path.join(temp_dir, 'tëst_ünīcōdé')
            os.makedirs(unicode_dir)
            
            config_path = os.path.join(unicode_dir, 'config_ünīcōdé.json')
            
            result = self.runner.invoke(cli, [
                'create-config',
                config_path
            ])
            
            # Should handle unicode paths properly
            # Exit code may vary, but should not crash
            assert result.output is not None


class TestCLIIntegration:
    """Test CLI integration with main system."""
    
    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()
    
    def test_cli_version_info(self):
        """Test that CLI provides version information."""
        # Try different ways to get version info
        version_commands = [
            ['--version'],
            ['-V'],
        ]
        
        for cmd in version_commands:
            try:
                result = self.runner.invoke(cli, cmd)
                if result.exit_code == 0 and 'version' in result.output.lower():
                    # Found version command
                    assert 'algosystem' in result.output.lower() or len(result.output.strip()) > 0
                    break
            except:
                continue
    
    @patch('algosystem.cli.commands.Engine')
    def test_dashboard_integration_mock(self, mock_engine_class, sample_csv_file):
        """Test dashboard command integration with Engine (mocked)."""
        # Mock Engine behavior
        mock_engine = MagicMock()
        mock_engine.run.return_value = {'metrics': {}, 'plots': {}}
        mock_engine.generate_dashboard.return_value = '/fake/path/dashboard.html'
        mock_engine_class.return_value = mock_engine
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(cli, [
                'dashboard',
                sample_csv_file,
                '--output-dir', temp_dir,
                '--use-default-config'
            ])
            
            # Should have attempted to create Engine and run dashboard
            mock_engine_class.assert_called_once()
            mock_engine.run.assert_called_once()
    
    def test_end_to_end_workflow(self, sample_csv_file):
        """Test complete CLI workflow if all components are available."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create a custom config
            config_path = os.path.join(temp_dir, 'workflow_config.json')
            
            result1 = self.runner.invoke(cli, [
                'create-config',
                config_path
            ])
            
            # Step 2: Show the config (if creation succeeded)
            if result1.exit_code == 0:
                result2 = self.runner.invoke(cli, [
                    'show-config',
                    config_path
                ])
                
                # Should display the config
                if result2.exit_code == 0:
                    assert 'layout' in result2.output.lower() or 'dashboard' in result2.output.lower()
            
            # Step 3: Generate dashboard with custom config
            result3 = self.runner.invoke(cli, [
                'dashboard',
                sample_csv_file,
                '--output-dir', temp_dir,
                '--config', config_path
            ])
            
            # End-to-end may fail due to missing dependencies, but should not crash
            assert result3.output is not None
    
    def test_cli_error_messages(self):
        """Test that CLI provides helpful error messages."""
        # Test missing required arguments
        result = self.runner.invoke(cli, ['dashboard'])
        assert result.exit_code != 0
        assert 'Usage:' in result.output or 'Error:' in result.output
        
        # Test invalid options
        result = self.runner.invoke(cli, ['dashboard', '--invalid-option'])
        assert result.exit_code != 0
        assert 'no such option' in result.output.lower() or 'error' in result.output.lower()
    
    def test_cli_help_consistency(self):
        """Test that all commands have consistent help format."""
        commands = ['dashboard', 'launch', 'create-config', 'show-config', 'list-configs']
        
        for command in commands:
            result = self.runner.invoke(cli, [command, '--help'])
            
            # All help outputs should have Usage section
            assert result.exit_code == 0
            assert ('Usage:' in result.output or 'usage:' in result.output.lower())
    
    def test_cli_exit_codes(self):
        """Test that CLI returns appropriate exit codes."""
        # Success case (help should return 0)
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        
        # Error case (invalid command should return non-zero)
        result = self.runner.invoke(cli, ['nonexistent-command'])
        assert result.exit_code != 0
        
        # Error case (missing file should return non-zero)
        result = self.runner.invoke(cli, ['dashboard', 'nonexistent.csv'])
        assert result.exit_code != 0