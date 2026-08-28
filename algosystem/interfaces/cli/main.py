"""Click command adapters for AlgoSystem."""

from __future__ import annotations

import ast
import webbrowser
from pathlib import Path
from typing import Optional, Sequence

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from algosystem import __version__
from algosystem.interfaces.api import AlgoSystem
from algosystem.shared.errors import AlgoSystemError
from algosystem.shared.values import RunId

from .loaders import load_benchmark_input, load_prices

console = Console()


@click.group()
@click.version_option(__version__, prog_name="algosystem")
def cli() -> None:
    """AlgoSystem command-line interface."""
    load_dotenv()


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--benchmark", help="Benchmark alias or CSV file.")
@click.option("--start", help="Start date, e.g. 2022-01-01.")
@click.option("--end", help="End date, e.g. 2023-01-01.")
@click.option("--initial-capital", type=float, help="Initial capital.")
@click.option("--price-column", help="Price column for multi-column CSV files.")
@click.option("--detailed", is_flag=True, default=False, help="Print all available metrics.")
def backtest(
    input_file: Path,
    benchmark: Optional[str],
    start: Optional[str],
    end: Optional[str],
    initial_capital: Optional[float],
    price_column: Optional[str],
    detailed: bool,
) -> None:
    """Run a backtest from a CSV file."""
    try:
        prices = load_prices(input_file)
        benchmark_prices = load_benchmark_input(benchmark, start=start, end=end)
        algo = AlgoSystem()
        result = algo.backtest(
            prices,
            benchmark=benchmark_prices,
            start=start,
            end=end,
            initial_capital=initial_capital,
            price_column=price_column,
        )
        algo.print_summary(result, detailed=detailed)
    except (AlgoSystemError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--output", "-o", type=click.Path(dir_okay=False, path_type=Path), default="tearsheet.html"
)
@click.option("--title", help="Tearsheet title.")
@click.option("--mode", type=click.Choice(["html", "full", "basic"]), default="html")
@click.option("--benchmark", help="Benchmark alias or CSV file.")
@click.option("--start", help="Start date, e.g. 2022-01-01.")
@click.option("--end", help="End date, e.g. 2023-01-01.")
@click.option("--initial-capital", type=float, help="Initial capital.")
@click.option("--price-column", help="Price column for multi-column CSV files.")
@click.option("--open", "open_browser", is_flag=True, default=False, help="Open the output file.")
def tearsheet(
    input_file: Path,
    output: Path,
    title: Optional[str],
    mode: str,
    benchmark: Optional[str],
    start: Optional[str],
    end: Optional[str],
    initial_capital: Optional[float],
    price_column: Optional[str],
    open_browser: bool,
) -> None:
    """Run a backtest and render a quantstats tearsheet."""
    try:
        prices = load_prices(input_file)
        benchmark_prices = load_benchmark_input(benchmark, start=start, end=end)
        algo = AlgoSystem()
        result = algo.backtest(
            prices,
            benchmark=benchmark_prices,
            start=start,
            end=end,
            initial_capital=initial_capital,
            price_column=price_column,
        )
        rendered = algo.tearsheet(result, output=output, title=title, mode=mode)
        console.print(f"Rendered tearsheet: {rendered}")
        if open_browser:
            webbrowser.open(Path(rendered).resolve().as_uri())
    except (AlgoSystemError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--strategy",
    default="momentum",
    show_default=True,
    help="Shipped name or module:function path.",
)
@click.option(
    "--param",
    "params",
    multiple=True,
    help="Parameter override as KEY=V1,V2,V3. May be repeated.",
)
@click.option("--reps", type=int, default=1000, show_default=True, help="Permutation replications.")
@click.option(
    "--shuffle",
    type=click.Choice(["complete", "cyclic", "block"]),
    default="complete",
    show_default=True,
)
@click.option("--seed", type=int, help="Random seed.")
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), help="HTML report path.")
@click.option("--open", "open_browser", is_flag=True, default=False, help="Open the HTML report.")
@click.option("--start", help="Start date, e.g. 2022-01-01.")
@click.option("--end", help="End date, e.g. 2023-01-01.")
@click.option("--price-column", help="Price/equity column for multi-column CSV files.")
def validate(
    input_file: Path,
    strategy: str,
    params: Sequence[str],
    reps: int,
    shuffle: str,
    seed: Optional[int],
    output: Optional[Path],
    open_browser: bool,
    start: Optional[str],
    end: Optional[str],
    price_column: Optional[str],
) -> None:
    """Run overfitting validation from a CSV price/equity series."""
    try:
        prices = load_prices(input_file)
        series = _select_price_series(prices, price_column=price_column, start=start, end=end)
        from algosystem.backtesting.domain.equity_curve import EquityCurve

        equity_curve = EquityCurve.from_series(series)
        param_grid = _parse_param_options(params)
        algo = AlgoSystem()
        with console.status(f"Running {reps} validation permutations for {strategy}..."):
            results = algo.detect_overfitting(
                strategy=strategy,
                returns=equity_curve,
                param_grid=param_grid or None,
                n_reps=reps,
                seed=seed,
                shuffle_method=shuffle,
                n_workers=1,
            )
        _print_validation_summary(results)

        report_path = output or (Path("overfit.html") if open_browser else None)
        if report_path is not None:
            rendered = algo.validation_report(
                results,
                output=report_path,
                open_browser=open_browser,
            )
            console.print(f"Rendered validation report: {rendered}")
    except (AlgoSystemError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command("validate-strategies")
def validate_strategies() -> None:
    """List shipped validation strategy archetypes and default grids."""
    from algosystem.validation.infrastructure.strategies import STRATEGY_REGISTRY

    table = Table(title="Validation Strategy Archetypes")
    table.add_column("Name", style="green")
    table.add_column("Parameter Grid", style="cyan")
    for name, spec in sorted(STRATEGY_REGISTRY.items()):
        table.add_row(name, _format_param_grid(spec.parameter_grid.to_dict()))
    console.print(table)


@cli.command()
def benchmarks() -> None:
    """List available benchmark aliases."""
    from algosystem.marketdata import get_benchmark_info

    info = get_benchmark_info()
    table = Table(title="Available Benchmark Aliases")
    table.add_column("Category", style="cyan")
    table.add_column("Alias", style="green")
    table.add_column("Ticker", style="magenta")
    table.add_column("Description", style="yellow")
    for _, row in info.iterrows():
        table.add_row(row["Category"], row["Alias"], row["Ticker/Symbol"], row["Description"])
    console.print(table)


@cli.group()
def db() -> None:
    """Persist and inspect backtest runs."""


@db.command("save")
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--name", required=True, help="Stored run name.")
@click.option("--description", default="", help="Stored run description.")
@click.option("--benchmark", help="Benchmark alias or CSV file.")
@click.option("--start", help="Start date, e.g. 2022-01-01.")
@click.option("--end", help="End date, e.g. 2023-01-01.")
@click.option("--initial-capital", type=float, help="Initial capital.")
@click.option("--price-column", help="Price column for multi-column CSV files.")
@click.option("--overwrite", is_flag=True, default=False, help="Overwrite an existing run id.")
def db_save(
    input_file: Path,
    name: str,
    description: str,
    benchmark: Optional[str],
    start: Optional[str],
    end: Optional[str],
    initial_capital: Optional[float],
    price_column: Optional[str],
    overwrite: bool,
) -> None:
    """Backtest a CSV file and archive the run."""
    try:
        repository = _repository()
        algo = AlgoSystem(repository=repository)
        result = algo.backtest(
            load_prices(input_file),
            benchmark=load_benchmark_input(benchmark, start=start, end=end),
            start=start,
            end=end,
            initial_capital=initial_capital,
            price_column=price_column,
        )
        run_id = algo.save(result, name=name, description=description, overwrite=overwrite)
        console.print(f"Saved run: {run_id.value}")
    except (AlgoSystemError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@db.command("list")
@click.option("--limit", type=int, default=20, show_default=True)
@click.option("--offset", type=int, default=0, show_default=True)
def db_list(limit: int, offset: int) -> None:
    """List saved runs."""
    try:
        rows = _repository().list_runs(limit=limit, offset=offset)
        table = Table(title="Saved Backtest Runs")
        table.add_column("Run ID", style="green")
        table.add_column("Start")
        table.add_column("End")
        table.add_column("Total Return", justify="right")
        for row in rows:
            table.add_row(
                row.run_id.value,
                row.date_range.start.strftime("%Y-%m-%d"),
                row.date_range.end.strftime("%Y-%m-%d"),
                _format_percent(row.total_return.as_fraction),
            )
        console.print(table)
    except AlgoSystemError as exc:
        raise click.ClickException(str(exc)) from exc


@db.command("show")
@click.argument("run_id")
def db_show(run_id: str) -> None:
    """Show one saved run."""
    try:
        result = AlgoSystem(repository=_repository()).load(RunId(run_id))
        AlgoSystem().print_summary(result, detailed=True)
    except AlgoSystemError as exc:
        raise click.ClickException(str(exc)) from exc


@db.command("compare")
@click.argument("run_ids", nargs=-1, required=True)
def db_compare(run_ids: Sequence[str]) -> None:
    """Compare saved runs."""
    try:
        comparison = AlgoSystem(repository=_repository()).compare(list(run_ids))
        table = Table(title="Run Comparison")
        table.add_column("Run ID", style="green")
        table.add_column("Final Equity", justify="right")
        for column in comparison.columns:
            table.add_row(str(column), f"{comparison[column].iloc[-1]:,.2f}")
        console.print(table)
    except (AlgoSystemError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@db.command("delete")
@click.argument("run_id")
def db_delete(run_id: str) -> None:
    """Delete a saved run."""
    try:
        _repository().delete(RunId(run_id))
        console.print(f"Deleted run: {run_id}")
    except AlgoSystemError as exc:
        raise click.ClickException(str(exc)) from exc


@db.command("init")
def db_init() -> None:
    """Create database schema and tables."""
    try:
        from sqlalchemy import create_engine

        from algosystem.backtesting.infrastructure.persistence import DatabaseConfig, schema

        config = DatabaseConfig.from_env()
        engine = create_engine(config.url(), pool_size=config.pool_size)
        schema.create_all(engine, config.schema)
        console.print(f"Initialized database schema: {config.schema}")
    except AlgoSystemError as exc:
        raise click.ClickException(str(exc)) from exc


def _repository() -> object:
    from algosystem.backtesting.infrastructure.persistence import (
        DatabaseConfig,
        PostgresBacktestRunRepository,
    )

    return PostgresBacktestRunRepository(DatabaseConfig.from_env())


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def _select_price_series(
    prices,
    *,
    price_column: Optional[str],
    start: Optional[str],
    end: Optional[str],
):
    frame = prices
    if start is not None or end is not None:
        frame = frame.loc[start:end]
    if frame.empty:
        raise ValueError("selected validation date range is empty")
    if price_column is not None:
        if price_column not in frame.columns:
            raise ValueError(f"price column not found: {price_column}")
        return frame[price_column]

    numeric = frame.select_dtypes(include="number")
    if numeric.shape[1] != 1:
        raise ValueError("use --price-column when the CSV has multiple numeric columns")
    return numeric.iloc[:, 0]


def _parse_param_options(params: Sequence[str]) -> dict[str, list[object]]:
    parsed: dict[str, list[object]] = {}
    for item in params:
        key, separator, raw_values = item.partition("=")
        if not separator or not key.strip():
            raise ValueError(f"invalid --param value: {item}")
        values = [_parse_param_value(value.strip()) for value in raw_values.split(",")]
        if not values or any(value == "" for value in values):
            raise ValueError(f"invalid --param value: {item}")
        parsed[key.strip()] = values
    return parsed


def _parse_param_value(value: str) -> object:
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return value


def _format_param_grid(grid: dict[str, list[object]]) -> str:
    return "; ".join(f"{name}={values}" for name, values in grid.items())


def _print_validation_summary(results: object) -> None:
    table = Table(title="Validation Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green", justify="right")
    table.add_row("Parameter combinations", str(results.n_params))
    table.add_row("Permutation replications", str(results.n_reps))
    table.add_row("Best Sharpe", f"{results.best_sharpe:.6f}")
    table.add_row("Unbiased p-value", f"{results.unbiased_pvalue:.12f}")
    table.add_row("Probability overfit", f"{results.prob_overfit:.12f}")
    table.add_row("Deflated Sharpe", f"{results.deflated_sharpe:.6f}")
    console.print(table)
    console.print(Panel("\n".join(results.summary()), title="Permutation Report", expand=False))


__all__ = ["cli"]


if __name__ == "__main__":
    cli()
