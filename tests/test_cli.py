from click.testing import CliRunner

from algosystem.interfaces.cli.main import cli


def test_cli_help_lists_phase_5_commands():
    result = CliRunner().invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "AlgoSystem" in result.output
    assert "backtest" in result.output
    assert "tearsheet" in result.output
    assert "validate" in result.output
    assert "validate-strategies" in result.output
    assert "benchmarks" in result.output
    assert "db" in result.output


def test_cli_version():
    result = CliRunner().invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert "algosystem" in result.output.lower()


def test_top_level_subcommand_help():
    for command in ("backtest", "tearsheet", "validate", "validate-strategies", "benchmarks", "db"):
        result = CliRunner().invoke(cli, [command, "--help"])

        assert result.exit_code == 0


def test_validate_strategies_lists_shipped_archetypes():
    result = CliRunner().invoke(cli, ["validate-strategies"])

    assert result.exit_code == 0
    assert "momentum" in result.output
    assert "mean_reversion" in result.output
    assert "volatility" in result.output


def test_db_subcommand_help():
    for command in ("save", "list", "show", "compare", "delete", "init"):
        result = CliRunner().invoke(cli, ["db", command, "--help"])

        assert result.exit_code == 0


def test_invalid_command_returns_non_zero():
    result = CliRunner().invoke(cli, ["missing-command"])

    assert result.exit_code != 0
    assert "No such command" in result.output
