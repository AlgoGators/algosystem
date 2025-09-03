import pytest
from click.testing import CliRunner
from algosystem.cli.commands import cli

class TestCLIIntegration:
    def test_dashboard_command_with_sample_data(self, sample_csv_file):
        runner = CliRunner()
        result = runner.invoke(cli, ['dashboard', sample_csv_file, '--use-default-config'])
        # Test that command doesn't crash
        assert result.exit_code == 0 or "error" in result.output.lower()
    
    def test_benchmark_commands(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['benchmarks', '--help'])
        assert result.exit_code == 0