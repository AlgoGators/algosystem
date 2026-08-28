"""Public Python facade for AlgoSystem."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Mapping, Optional, Sequence

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from algosystem.backtesting.application import (
    ArchiveRun,
    ArchiveRunRequest,
    CompareRuns,
    CompareRunsRequest,
    GenerateTearsheet,
    GenerateTearsheetRequest,
    LoadRun,
    LoadRunRequest,
    RunBacktest,
    RunBacktestRequest,
    RunBacktestResponse,
)
from algosystem.backtesting.domain.backtest import BacktestResult
from algosystem.backtesting.domain.equity_curve import EquityCurve
from algosystem.backtesting.domain.metrics import PerformanceMetrics
from algosystem.backtesting.domain.ports import (
    BacktestRunRepository,
    MetricsCalculator,
    TearsheetRenderer,
)
from algosystem.shared.errors import ConfigurationError
from algosystem.shared.metric_key import MetricKey
from algosystem.shared.values import RunId

console = Console()


class AlgoSystem:
    """Ergonomic facade over the backtesting application use cases."""

    def __init__(
        self,
        calculator: Optional[MetricsCalculator] = None,
        repository: Optional[BacktestRunRepository] = None,
        renderer: Optional[TearsheetRenderer] = None,
    ) -> None:
        self._calculator = calculator or _default_calculator()
        self._repository = repository
        self._renderer = renderer or _default_renderer()
        self._run_backtest = RunBacktest(self._calculator)
        self._generate_tearsheet = GenerateTearsheet(self._renderer)

    def backtest(
        self,
        data: object,
        benchmark: object = None,
        start: object = None,
        end: object = None,
        initial_capital: object = None,
        price_column: Optional[str] = None,
    ) -> BacktestResult:
        """Run a backtest and return a BacktestResult."""
        response = self._run_backtest.execute(
            RunBacktestRequest(
                data=data,
                benchmark=benchmark,
                start=start,
                end=end,
                initial_capital=initial_capital,
                price_column=price_column,
            )
        )
        return _result_from_run_response(response)

    def tearsheet(
        self,
        result: BacktestResult,
        output: object = "tearsheet.html",
        title: Optional[str] = None,
        mode: str = "html",
        rf: float = 0.0,
        periods_per_year: int = 252,
    ) -> Path:
        """Render a quantstats tearsheet for a backtest result."""
        response = self._generate_tearsheet.execute(
            GenerateTearsheetRequest(
                result=result,
                output=Path(output),
                title=title or _default_title(result),
                mode=mode,
                rf=rf,
                periods_per_year=periods_per_year,
            )
        )
        return response.output

    def detect_overfitting(
        self,
        *,
        strategy: object = "momentum",
        returns: object,
        param_grid: Optional[Mapping[str, Sequence[object]]] = None,
        n_reps: int = 1000,
        seed: Optional[int] = None,
        shuffle_method: str = "complete",
        n_workers: Optional[int] = None,
    ) -> object:
        """Run validation over a re-runnable strategy and return overfit results."""
        from algosystem.validation.facade import detect_overfitting

        return detect_overfitting(
            strategy=strategy,
            returns=returns,
            param_grid=param_grid,
            n_reps=n_reps,
            seed=seed,
            shuffle_method=shuffle_method,
            n_workers=n_workers,
        )

    def validation_report(
        self,
        report: object,
        output: object = "overfit.html",
        *,
        title: str = "Overfitting Detection Report",
        open_browser: bool = False,
    ) -> Path:
        """Render a validation HTML report."""
        from algosystem.validation.application.render_report import RenderValidationReport
        from algosystem.validation.infrastructure.html_report import HtmlReportRenderer

        results = getattr(report, "overfit_results", report)
        return RenderValidationReport(HtmlReportRenderer()).execute(
            results,
            Path(output),
            title=title,
            open_browser=open_browser,
        )

    def save(
        self,
        result: BacktestResult,
        name: Optional[str] = None,
        description: str = "",
        hyperparameters: Optional[Mapping[str, object]] = None,
        overwrite: bool = False,
    ) -> RunId:
        """Persist a backtest result and return its run id."""
        archive = ArchiveRun(self._required_repository())
        response = archive.execute(
            ArchiveRunRequest(
                result=result,
                name=name,
                description=description,
                hyperparameters=hyperparameters,
                overwrite=overwrite,
            )
        )
        return response.run_id

    def load(self, run_id: object) -> BacktestResult:
        """Load a persisted run."""
        loader = LoadRun(self._required_repository())
        return loader.execute(LoadRunRequest(run_id=_coerce_run_id(run_id))).result

    def compare(self, run_ids: Sequence[object]) -> pd.DataFrame:
        """Return aligned equity curves for selected persisted runs."""
        comparer = CompareRuns(self._required_repository())
        return comparer.execute(CompareRunsRequest(run_ids=run_ids)).equity_curves

    def print_summary(self, result: BacktestResult, detailed: bool = False) -> None:
        """Print a rich summary table for a backtest result."""
        _print_summary(result, detailed=detailed)

    def export_data(
        self,
        result: BacktestResult,
        output_path: object,
        format: str = "csv",
    ) -> Path:
        """Export a result's equity and returns time series to CSV or Excel."""
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "equity": result.equity_curve.values,
            "returns": result.equity_curve.returns(),
        }
        if result.benchmark_curve is not None:
            data["benchmark"] = result.benchmark_curve.values
            data["benchmark_returns"] = result.benchmark_curve.returns()

        frame = pd.DataFrame(data)
        if format.lower() == "csv":
            frame.to_csv(output)
        elif format.lower() in {"excel", "xlsx"}:
            frame.to_excel(output)
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'csv' or 'excel'.")
        return output

    @staticmethod
    def get_benchmark(
        benchmark_alias: Optional[str] = None,
        start_date: object = None,
        end_date: object = None,
    ) -> pd.Series:
        """Fetch benchmark price data by alias."""
        from algosystem.marketdata.benchmark import DEFAULT_BENCHMARK, fetch_benchmark_data

        alias = benchmark_alias or DEFAULT_BENCHMARK
        return fetch_benchmark_data(alias, start_date, end_date)

    @staticmethod
    def list_benchmarks() -> list[str]:
        """List available benchmark aliases and print their descriptions."""
        from algosystem.marketdata.benchmark import get_benchmark_info, get_benchmark_list

        benchmarks = get_benchmark_list()
        info = get_benchmark_info()

        table = Table(title="Available Benchmark Aliases")
        table.add_column("Category", style="cyan")
        table.add_column("Alias", style="green")
        table.add_column("Description", style="yellow")

        for category in info["Category"].unique():
            category_info = info[info["Category"] == category]
            for row_index, (_, row) in enumerate(category_info.iterrows()):
                table.add_row(
                    category if row_index == 0 else "",
                    row["Alias"],
                    row["Description"],
                )

        console.print(table)
        return benchmarks

    @staticmethod
    def compare_benchmarks(
        benchmarks: Sequence[str],
        start_date: object = None,
        end_date: object = None,
        plot: bool = True,
    ) -> pd.DataFrame:
        """Compare normalized benchmark price series over the same period."""
        from algosystem.marketdata.benchmark import compare_benchmarks as compare_market_benchmarks

        comparison = compare_market_benchmarks(benchmarks, start_date, end_date)

        if plot:
            import matplotlib.pyplot as plt

            plt.figure(figsize=(12, 6))
            for column in comparison.columns:
                plt.plot(comparison.index, comparison[column], label=column)
            plt.title("Benchmark Comparison (Normalized to 100)")
            plt.xlabel("Date")
            plt.ylabel("Value")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.gcf().autofmt_xdate()
            plt.show()

        return comparison

    @classmethod
    def run_backtest(
        cls,
        data: object,
        benchmark: object = None,
        start_date: object = None,
        end_date: object = None,
        initial_capital: object = None,
        price_column: Optional[str] = None,
        **kwargs: object,
    ) -> BacktestResult:
        """Deprecated class entry point for running a backtest."""
        warnings.warn(
            "AlgoSystem.run_backtest() is deprecated; instantiate AlgoSystem "
            "and call .backtest().",
            DeprecationWarning,
            stacklevel=2,
        )
        start = kwargs.pop("start", start_date)
        end = kwargs.pop("end", end_date)
        calculator = kwargs.pop("calculator", None)
        repository = kwargs.pop("repository", None)
        renderer = kwargs.pop("renderer", None)
        if kwargs:
            unknown = ", ".join(sorted(str(key) for key in kwargs))
            raise TypeError(f"unexpected keyword argument(s): {unknown}")
        return cls(
            calculator=calculator,  # type: ignore[arg-type]
            repository=repository,  # type: ignore[arg-type]
            renderer=renderer,  # type: ignore[arg-type]
        ).backtest(
            data=data,
            benchmark=benchmark,
            start=start,
            end=end,
            initial_capital=initial_capital,
            price_column=price_column,
        )

    @classmethod
    def print_results(cls, result: object, detailed: bool = False) -> None:
        """Deprecated class entry point for printing a result summary."""
        warnings.warn(
            "AlgoSystem.print_results() is deprecated; instantiate AlgoSystem "
            "and call .print_summary().",
            DeprecationWarning,
            stacklevel=2,
        )
        backtest_result = _coerce_result(result)
        if backtest_result is None:
            console.print("[bold red]No results available. Run the backtest first.[/bold red]")
            return
        _print_summary(backtest_result, detailed=detailed)

    def _required_repository(self) -> BacktestRunRepository:
        if self._repository is None:
            raise ConfigurationError(
                "repository is required for save, load, and compare operations"
            )
        return self._repository


def run_backtest(data: object, benchmark: object = None, **kwargs: object) -> BacktestResult:
    """Run a backtest with default adapters and return a BacktestResult."""
    if "start_date" in kwargs and "start" not in kwargs:
        kwargs["start"] = kwargs.pop("start_date")
    if "end_date" in kwargs and "end" not in kwargs:
        kwargs["end"] = kwargs.pop("end_date")
    return AlgoSystem().backtest(data, benchmark=benchmark, **kwargs)


def detect_overfitting(**kwargs: object) -> object:
    """Run validation with default adapters and return overfit results."""
    return AlgoSystem().detect_overfitting(**kwargs)


def quick_backtest(data: object, benchmark: object = None, **kwargs: object) -> BacktestResult:
    """Deprecated convenience wrapper that runs and prints a backtest."""
    warnings.warn(
        "quick_backtest() is deprecated; use run_backtest() and AlgoSystem.print_summary().",
        DeprecationWarning,
        stacklevel=2,
    )
    result = run_backtest(data, benchmark=benchmark, **kwargs)
    AlgoSystem().print_summary(result)
    return result


def _default_calculator() -> MetricsCalculator:
    from algosystem.backtesting import infrastructure

    return infrastructure.QuantStatsMetricsCalculator()


def _default_renderer() -> TearsheetRenderer:
    from algosystem.backtesting import infrastructure

    return infrastructure.QuantStatsTearsheetRenderer()


def _result_from_run_response(response: RunBacktestResponse) -> BacktestResult:
    return BacktestResult(
        equity_curve=EquityCurve.from_series(response.equity),
        benchmark_curve=(
            EquityCurve.from_series(response.benchmark) if response.benchmark is not None else None
        ),
        metrics=PerformanceMetrics.from_dict(response.metrics),
        date_range=response.date_range,
        initial_capital=response.initial_capital,
        final_capital=response.final_capital,
        total_return=response.total_return,
        run_id=response.run_id,
    )


def _coerce_result(result: object) -> Optional[BacktestResult]:
    if isinstance(result, BacktestResult):
        return result
    backtest_result = getattr(result, "backtest_result", None)
    if isinstance(backtest_result, BacktestResult):
        return backtest_result
    return None


def _coerce_run_id(run_id: object) -> RunId:
    if isinstance(run_id, RunId):
        return run_id
    return RunId(str(run_id))


def _default_title(result: BacktestResult) -> str:
    if result.run_id is None:
        return "AlgoSystem Tearsheet"
    return f"AlgoSystem Tearsheet: {result.run_id.value}"


def _print_summary(result: BacktestResult, detailed: bool = False) -> None:
    console.print(
        Panel(
            f"[bold blue]Backtest Summary[/bold blue]\n"
            f"Period: {result.date_range.start.strftime('%Y-%m-%d')} "
            f"to {result.date_range.end.strftime('%Y-%m-%d')}\n"
            f"Initial Capital: {result.initial_capital}\n"
            f"Final Capital: {result.final_capital}\n"
            f"Total Return: {result.total_return}",
            title="AlgoSystem Results",
            expand=False,
        )
    )

    table = Table(title="Performance Metrics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    essential_metrics = [
        MetricKey.TOTAL_RETURN,
        MetricKey.ANNUALIZED_RETURN,
        MetricKey.SHARPE_RATIO,
        MetricKey.MAX_DRAWDOWN,
        MetricKey.ANNUALIZED_VOLATILITY,
    ]
    for metric_key in essential_metrics:
        value = result.metrics.get(metric_key)
        if value is not None:
            table.add_row(metric_key.label(), _format_metric(metric_key, value))

    for metric_key in (MetricKey.ALPHA, MetricKey.BETA):
        value = result.metrics.get(metric_key)
        if value is not None:
            table.add_row(metric_key.label(), _format_metric(metric_key, value))

    console.print(table)

    if detailed:
        shown = set(essential_metrics)
        shown.update({MetricKey.ALPHA, MetricKey.BETA})
        detailed_table = Table(title="Detailed Metrics")
        detailed_table.add_column("Metric", style="cyan")
        detailed_table.add_column("Value", style="green")
        for metric_key in MetricKey:
            if metric_key in shown:
                continue
            value = result.metrics.get(metric_key)
            if value is not None:
                detailed_table.add_row(metric_key.label(), _format_metric(metric_key, value))
        console.print(detailed_table)


def _format_metric(metric_key: MetricKey, value: float) -> str:
    if metric_key in {
        MetricKey.TOTAL_RETURN,
        MetricKey.ANNUALIZED_RETURN,
        MetricKey.ANNUALIZED_VOLATILITY,
        MetricKey.MAX_DRAWDOWN,
        MetricKey.DOWNSIDE_DEVIATION,
        MetricKey.VAR_95,
        MetricKey.VAR_99,
        MetricKey.CVAR_95,
        MetricKey.BEST_MONTH,
        MetricKey.WORST_MONTH,
        MetricKey.AVG_MONTHLY_RETURN,
        MetricKey.MONTHLY_VOLATILITY,
        MetricKey.ALPHA,
        MetricKey.TRACKING_ERROR,
    }:
        return f"{value * 100:.2f}%"
    return f"{value:.4f}"


__all__ = ["AlgoSystem", "detect_overfitting", "quick_backtest", "run_backtest"]
