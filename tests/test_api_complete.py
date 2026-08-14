import sys
import types
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

import algosystem
from algosystem import AlgoSystem, quick_backtest, run_backtest
from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.backtesting.infrastructure.fake_calculator import FakeMetricsCalculator
from algosystem.backtesting.infrastructure.persistence import InMemoryBacktestRunRepository
from algosystem.shared.errors import ConfigurationError, InvalidPriceSeriesError
from algosystem.shared.metric_key import MetricKey


class TestPackageExports:
    def test_package_exports_new_facade(self):
        assert algosystem.AlgoSystem is AlgoSystem
        assert algosystem.run_backtest is run_backtest
        assert algosystem.quick_backtest is quick_backtest
        assert "AlgoSystem" in algosystem.__all__
        assert "run_backtest" in algosystem.__all__
        assert "quick_backtest" in algosystem.__all__
        assert "ValidationMetricKey" in algosystem.__all__
        assert "OverfitResults" in algosystem.__all__
        assert "ParameterGrid" in algosystem.__all__
        assert "StrategySpec" in algosystem.__all__
        assert hasattr(AlgoSystem, "backtest")
        assert hasattr(AlgoSystem, "tearsheet")
        assert hasattr(AlgoSystem, "detect_overfitting")
        assert hasattr(AlgoSystem, "validation_report")
        assert hasattr(AlgoSystem, "save")
        assert hasattr(AlgoSystem, "load")
        assert hasattr(AlgoSystem, "compare")
        assert hasattr(AlgoSystem, "print_summary")
        assert hasattr(AlgoSystem, "export_data")


class TestAlgoSystemAPI:
    def test_backtest_basic(self, sample_price_series):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(sample_price_series)

        assert isinstance(result, BacktestResult)
        assert result.metrics.get(MetricKey.TOTAL_RETURN) == 0.23
        assert len(result.equity_curve) == len(sample_price_series)

    def test_backtest_with_benchmark(self, sample_price_series, sample_benchmark_series):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(
            data=sample_price_series, benchmark=sample_benchmark_series
        )

        assert isinstance(result, BacktestResult)
        assert result.benchmark_curve is not None

    def test_backtest_with_date_range(self, sample_price_series):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(
            data=sample_price_series,
            start="2020-01-15",
            end="2020-02-15",
        )

        assert result.date_range.start == pd.to_datetime("2020-01-15")
        assert result.date_range.end == pd.to_datetime("2020-02-15")

    def test_backtest_dataframe_input(self, sample_dataframe):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(
            data=sample_dataframe, price_column="Strategy"
        )

        assert isinstance(result, BacktestResult)
        assert len(result.equity_curve) == len(sample_dataframe)

    def test_backtest_invalid_input(self):
        algo = AlgoSystem(calculator=FakeMetricsCalculator())

        with pytest.raises(InvalidPriceSeriesError):
            algo.backtest("invalid_data")

        with pytest.raises(InvalidPriceSeriesError):
            algo.backtest(None)

    def test_module_run_backtest_uses_new_facade(self, sample_price_series):
        with patch(
            "algosystem.interfaces.api._default_calculator",
            return_value=FakeMetricsCalculator(),
        ):
            result = run_backtest(sample_price_series)

        assert isinstance(result, BacktestResult)

    def test_deprecated_class_run_backtest_warns(self, sample_price_series):
        with pytest.warns(DeprecationWarning):
            result = AlgoSystem.run_backtest(
                sample_price_series, calculator=FakeMetricsCalculator()
            )

        assert isinstance(result, BacktestResult)

    def test_validation_facade_methods(self, sample_price_series, tmp_path):
        from algosystem.backtesting.domain.equity_curve import EquityCurve

        curve = EquityCurve.from_series(sample_price_series)
        algo = AlgoSystem(calculator=FakeMetricsCalculator())

        report = algo.detect_overfitting(
            strategy="momentum",
            returns=curve,
            param_grid={"lookback": [3], "threshold": [0.0]},
            n_reps=2,
            n_workers=1,
            seed=7,
        )
        output = algo.validation_report(report, output=tmp_path / "overfit.html")

        assert report.n_reps == 2
        assert output.exists()


class TestAlgoSystemResults:
    def test_print_summary_basic(self, sample_price_series):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(sample_price_series)

        AlgoSystem(calculator=FakeMetricsCalculator()).print_summary(result)

    def test_print_results_deprecated_shim(self, sample_price_series):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(sample_price_series)

        with pytest.warns(DeprecationWarning):
            AlgoSystem.print_results(result, detailed=True)

    def test_print_results_no_result(self):
        with pytest.warns(DeprecationWarning):
            AlgoSystem.print_results(object())


class TestAlgoSystemDataExport:
    def test_export_data_csv(self, sample_price_series, temp_directory):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(sample_price_series)
        output_path = Path(temp_directory) / "test_export.csv"

        exported = AlgoSystem(calculator=FakeMetricsCalculator()).export_data(
            result, output_path, format="csv"
        )

        assert exported == output_path
        assert output_path.exists()
        exported_df = pd.read_csv(output_path, index_col=0, parse_dates=True)
        assert "equity" in exported_df.columns
        assert "returns" in exported_df.columns

    def test_export_data_excel(self, sample_price_series, temp_directory):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(sample_price_series)
        output_path = Path(temp_directory) / "test_export.xlsx"

        exported = AlgoSystem(calculator=FakeMetricsCalculator()).export_data(
            result, output_path, format="excel"
        )

        assert exported == output_path
        assert output_path.exists()
        exported_df = pd.read_excel(output_path, index_col=0)
        assert "equity" in exported_df.columns

    def test_export_data_invalid_format(self, sample_price_series, temp_directory):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(sample_price_series)
        output_path = Path(temp_directory) / "test_export.txt"

        with pytest.raises(ValueError):
            AlgoSystem(calculator=FakeMetricsCalculator()).export_data(
                result, output_path, format="invalid"
            )


class TestAlgoSystemPersistence:
    def test_save_load_and_compare(self, sample_price_series, sample_benchmark_series):
        repository = InMemoryBacktestRunRepository()
        algo = AlgoSystem(calculator=FakeMetricsCalculator(), repository=repository)
        first = algo.backtest(sample_price_series)
        second = algo.backtest(sample_benchmark_series)

        first_id = algo.save(first, name="first")
        second_id = algo.save(second, name="second")
        loaded = algo.load(first_id)
        comparison = algo.compare([first_id, second_id])

        assert loaded.run_id == first_id
        assert list(comparison.columns) == [first_id.value, second_id.value]

    def test_repository_required_for_persistence(self, sample_price_series):
        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(sample_price_series)
        algo = AlgoSystem(calculator=FakeMetricsCalculator())

        with pytest.raises(ConfigurationError):
            algo.save(result)


class TestAlgoSystemBenchmarks:
    def test_get_benchmark(self, monkeypatch):
        mock_fetch = Mock(
            return_value=pd.Series([100, 101, 102], index=pd.date_range("2020-01-01", periods=3))
        )
        _install_fake_benchmark_module(monkeypatch, fetch_benchmark_data=mock_fetch)

        result = AlgoSystem.get_benchmark("sp500")

        assert isinstance(result, pd.Series)
        assert len(result) == 3
        mock_fetch.assert_called_once_with("sp500", None, None)

    def test_list_benchmarks(self, monkeypatch):
        mock_list = Mock(return_value=["sp500", "nasdaq"])
        mock_info = Mock(
            return_value=pd.DataFrame(
                {
                    "Alias": ["sp500", "nasdaq"],
                    "Category": ["Indices", "Indices"],
                    "Description": ["S&P 500", "NASDAQ"],
                }
            )
        )
        _install_fake_benchmark_module(
            monkeypatch,
            get_benchmark_list=mock_list,
            get_benchmark_info=mock_info,
        )

        result = AlgoSystem.list_benchmarks()

        assert result == ["sp500", "nasdaq"]
        mock_list.assert_called_once()
        mock_info.assert_called_once()

    def test_compare_benchmarks(self, monkeypatch):
        mock_compare = Mock(
            return_value=pd.DataFrame(
                {"sp500": [100, 101, 102], "nasdaq": [100, 102, 104]},
                index=pd.date_range("2020-01-01", periods=3),
            )
        )
        _install_fake_benchmark_module(monkeypatch, compare_benchmarks=mock_compare)

        result = AlgoSystem.compare_benchmarks(["sp500", "nasdaq"], plot=False)

        assert isinstance(result, pd.DataFrame)
        assert "sp500" in result.columns
        assert "nasdaq" in result.columns
        mock_compare.assert_called_once_with(["sp500", "nasdaq"], None, None)

    def test_benchmark_comparison_empty_list(self, monkeypatch):
        mock_compare = Mock(side_effect=ValueError("Empty benchmark list"))
        _install_fake_benchmark_module(monkeypatch, compare_benchmarks=mock_compare)

        with pytest.raises(ValueError):
            AlgoSystem.compare_benchmarks([], plot=False)


class TestQuickBacktest:
    def test_quick_backtest_basic(self, sample_price_series):
        with (
            patch(
                "algosystem.interfaces.api._default_calculator",
                return_value=FakeMetricsCalculator(),
            ),
            patch("algosystem.interfaces.api.AlgoSystem.print_summary") as mock_print,
        ):
            with pytest.warns(DeprecationWarning):
                result = quick_backtest(sample_price_series)

        assert isinstance(result, BacktestResult)
        mock_print.assert_called_once_with(result)

    def test_quick_backtest_with_kwargs(self, sample_price_series):
        with (
            patch(
                "algosystem.interfaces.api._default_calculator",
                return_value=FakeMetricsCalculator(),
            ),
            patch("algosystem.interfaces.api.AlgoSystem.print_summary") as mock_print,
        ):
            with pytest.warns(DeprecationWarning):
                result = quick_backtest(
                    sample_price_series, start_date="2020-01-15", initial_capital=50000
                )

        assert isinstance(result, BacktestResult)
        assert result.initial_capital.amount == 50000
        mock_print.assert_called_once_with(result)


class TestAlgoSystemIntegration:
    def test_complete_workflow(self, sample_price_series, temp_directory):
        algo = AlgoSystem(calculator=FakeMetricsCalculator())
        result = algo.backtest(sample_price_series)
        data_path = Path(temp_directory) / "workflow_data.csv"

        data_result = algo.export_data(result, data_path)

        assert data_result == data_path
        assert data_path.exists()
        assert MetricKey.TOTAL_RETURN.value in result.metrics.to_dict()

    def test_multiple_backtests_comparison(self, sample_price_series, sample_benchmark_series):
        algo = AlgoSystem(calculator=FakeMetricsCalculator())
        first = algo.backtest(sample_price_series)
        second = algo.backtest(sample_benchmark_series)

        assert first.metrics.to_dict() == second.metrics.to_dict()
        assert first.equity_curve.values.iloc[-1] != second.equity_curve.values.iloc[-1]

    def test_large_dataset_handling(self):
        dates = pd.date_range("2020-01-01", periods=2000, freq="D")
        rng = np.random.default_rng(42)
        returns = rng.normal(0.001, 0.02, 2000)
        large_data = pd.Series(100 * np.cumprod(1 + returns), index=dates)

        result = AlgoSystem(calculator=FakeMetricsCalculator()).backtest(large_data)

        assert len(result.equity_curve) == len(large_data)


def _install_fake_benchmark_module(monkeypatch, **functions):
    module = types.ModuleType("algosystem.marketdata.benchmark")
    module.DEFAULT_BENCHMARK = "sp500"
    module.fetch_benchmark_data = functions.get("fetch_benchmark_data", Mock())
    module.get_benchmark_list = functions.get("get_benchmark_list", Mock(return_value=[]))
    module.get_benchmark_info = functions.get(
        "get_benchmark_info",
        Mock(
            return_value=pd.DataFrame(
                columns=["Alias", "Category", "Description"],
            )
        ),
    )
    module.compare_benchmarks = functions.get("compare_benchmarks", Mock())
    monkeypatch.setitem(sys.modules, "algosystem.marketdata.benchmark", module)
    return module
