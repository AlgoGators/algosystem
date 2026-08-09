"""Click command adapters for AlgoSystem."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Optional, Sequence

import click
from dotenv import load_dotenv
from rich.console import Console
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


__all__ = ["cli"]


if __name__ == "__main__":
    cli()
