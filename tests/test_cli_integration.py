import pandas as pd
from click.testing import CliRunner

from algosystem.interfaces.cli.main import cli


def test_benchmark_list_command(monkeypatch):
    monkeypatch.setattr(
        "algosystem.marketdata.get_benchmark_info",
        lambda: pd.DataFrame(
            {
                "Category": ["Stock indices", "Stock indices"],
                "Alias": ["nasdaq", "sp500"],
                "Ticker/Symbol": ["^IXIC", "^GSPC"],
                "Description": ["NASDAQ", "S&P 500"],
            }
        ),
    )

    result = CliRunner().invoke(cli, ["benchmarks"])

    assert result.exit_code == 0
    assert "nasdaq" in result.output
    assert "sp500" in result.output


def test_backtest_command_uses_facade(monkeypatch, sample_csv_file):
    calls = {}

    class FakeAlgoSystem:
        def backtest(self, prices, **kwargs):
            calls["prices"] = prices
            calls["kwargs"] = kwargs
            return object()

        def print_summary(self, result, detailed=False):
            calls["summary"] = (result, detailed)

    monkeypatch.setattr("algosystem.interfaces.cli.main.AlgoSystem", FakeAlgoSystem)

    result = CliRunner().invoke(
        cli,
        [
            "backtest",
            sample_csv_file,
            "--start",
            "2020-01-02",
            "--end",
            "2020-01-05",
            "--initial-capital",
            "5000",
            "--detailed",
        ],
    )

    assert result.exit_code == 0
    assert calls["prices"].index[0] == pd.Timestamp("2020-01-01")
    assert calls["kwargs"]["start"] == "2020-01-02"
    assert calls["kwargs"]["end"] == "2020-01-05"
    assert calls["kwargs"]["initial_capital"] == 5000
    assert calls["summary"][1] is True
