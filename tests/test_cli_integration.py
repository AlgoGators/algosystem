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


def test_regimes_command_reports_a_volatility_breakdown(tmp_path):
    import numpy as np

    rng = np.random.default_rng(42)
    returns = np.concatenate(
        [rng.normal(0.0005, 0.001, size=300), rng.normal(0.0005, 0.02, size=300)]
    )
    levels = np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + returns)])
    frame = pd.DataFrame(
        {"Strategy": levels},
        index=pd.date_range("2020-01-01", periods=len(levels), freq="D"),
    )
    frame.index.name = "Date"
    csv_path = tmp_path / "strategy.csv"
    frame.to_csv(csv_path)

    result = CliRunner().invoke(cli, ["regimes", str(csv_path), "--price-column", "Strategy"])

    assert result.exit_code == 0, result.output
    assert "low_vol" in result.output
    assert "high_vol" in result.output
    assert "Overall Sharpe" in result.output


def test_regimes_command_rejects_an_unknown_price_column(tmp_path, sample_csv_file):
    result = CliRunner().invoke(cli, ["regimes", sample_csv_file, "--price-column", "Missing"])

    assert result.exit_code != 0
    assert "price column not found" in result.output


def _write_series(path, values, index, column):
    frame = pd.DataFrame({column: values}, index=index)
    frame.index.name = "Date"
    frame.to_csv(path)
    return str(path)


def _regime_levels(seed, size=600):
    import numpy as np

    rng = np.random.default_rng(seed)
    returns = np.concatenate(
        [rng.normal(0.0005, 0.001, size=size // 2), rng.normal(0.0005, 0.02, size=size // 2)]
    )
    return np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + returns)])


def _inverted_regime_levels(seed, size=600):
    """Levels whose volatility break runs stormy-then-calm (opposite of _regime_levels)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    returns = np.concatenate(
        [rng.normal(0.0005, 0.02, size=size // 2), rng.normal(0.0005, 0.001, size=size // 2)]
    )
    return np.concatenate([[100.0], 100.0 * np.cumprod(1.0 + returns)])


def test_regimes_command_accepts_a_benchmark_on_a_different_calendar(tmp_path):
    """A business-day benchmark against a calendar-day strategy must still work."""
    strategy = _regime_levels(seed=3)
    strategy_index = pd.date_range("2020-01-01", periods=len(strategy), freq="D")
    strategy_csv = _write_series(tmp_path / "strategy.csv", strategy, strategy_index, "Strategy")

    business_days = pd.date_range("2020-01-01", periods=len(strategy), freq="B")
    benchmark = _regime_levels(seed=8, size=len(business_days) - 1)
    benchmark_csv = _write_series(tmp_path / "benchmark.csv", benchmark, business_days, "Benchmark")

    result = CliRunner().invoke(
        cli,
        ["regimes", strategy_csv, "--price-column", "Strategy", "--benchmark", benchmark_csv],
    )

    assert result.exit_code == 0, result.output
    assert "low_vol" in result.output
    assert "high_vol" in result.output


def test_regimes_command_actually_classifies_on_the_benchmark(tmp_path):
    """
    Without this, the --benchmark flag could be ignored and the happy-path test
    would still pass. The benchmark's volatility break runs opposite to the
    strategy's, so classifying on it must move the worst regime.
    """
    strategy = _regime_levels(seed=3)
    index = pd.date_range("2020-01-01", periods=len(strategy), freq="D")
    strategy_csv = _write_series(tmp_path / "strategy.csv", strategy, index, "Strategy")
    benchmark = _inverted_regime_levels(seed=8, size=len(strategy) - 1)
    benchmark_csv = _write_series(tmp_path / "benchmark.csv", benchmark, index, "Benchmark")

    base = CliRunner().invoke(cli, ["regimes", strategy_csv, "--price-column", "Strategy"])
    with_benchmark = CliRunner().invoke(
        cli,
        ["regimes", strategy_csv, "--price-column", "Strategy", "--benchmark", benchmark_csv],
    )

    assert base.exit_code == 0, base.output
    assert with_benchmark.exit_code == 0, with_benchmark.output
    assert base.output != with_benchmark.output, "--benchmark did not change the classification"


def test_regimes_command_rejects_a_non_overlapping_benchmark(tmp_path):
    strategy = _regime_levels(seed=3)
    strategy_csv = _write_series(
        tmp_path / "strategy.csv",
        strategy,
        pd.date_range("2020-01-01", periods=len(strategy), freq="D"),
        "Strategy",
    )
    benchmark = _regime_levels(seed=8)
    benchmark_csv = _write_series(
        tmp_path / "benchmark.csv",
        benchmark,
        pd.date_range("1990-01-01", periods=len(benchmark), freq="D"),
        "Benchmark",
    )

    result = CliRunner().invoke(
        cli,
        ["regimes", strategy_csv, "--price-column", "Strategy", "--benchmark", benchmark_csv],
    )

    assert result.exit_code != 0
    assert "fewer than two dates" in result.output


def test_regimes_command_rejects_a_series_too_short_to_classify(tmp_path):
    """A short series must not print a confident all-zero verdict."""
    levels = [100.0 + i for i in range(15)]
    csv_path = _write_series(
        tmp_path / "short.csv",
        levels,
        pd.date_range("2020-01-01", periods=len(levels), freq="D"),
        "Strategy",
    )

    result = CliRunner().invoke(cli, ["regimes", csv_path, "--price-column", "Strategy"])

    assert result.exit_code != 0
    assert "vol_window" in result.output


def test_regimes_command_honours_the_regime_and_window_options(tmp_path):
    strategy = _regime_levels(seed=3)
    csv_path = _write_series(
        tmp_path / "strategy.csv",
        strategy,
        pd.date_range("2020-01-01", periods=len(strategy), freq="D"),
        "Strategy",
    )

    result = CliRunner().invoke(
        cli,
        [
            "regimes",
            csv_path,
            "--price-column",
            "Strategy",
            "--regimes",
            "4",
            "--vol-window",
            "10",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "regime_0" in result.output
    assert "regime_3" in result.output
