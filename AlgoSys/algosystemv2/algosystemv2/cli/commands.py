"""
Streamlined CLI for AlgoSystemV2.
Simplified command set: dashboard, test, benchmarks, compare-benchmarks.
"""

import os
import sys
import traceback
from datetime import datetime, timedelta

import click
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algosystemv2.data.benchmark import (
    DEFAULT_BENCHMARK,
    fetch_benchmark_data,
    get_benchmark_info,
    get_benchmark_list,
)


def _load_benchmark(benchmark, data, start_date, end_date, force_refresh=False):
    """Helper to load benchmark data from file path or alias."""
    if benchmark is None:
        # Default to S&P 500
        try:
            click.echo("Loading default benchmark (S&P 500)...")
            benchmark_data = fetch_benchmark_data(
                DEFAULT_BENCHMARK,
                start_date=data.index[0] if not start_date else start_date,
                end_date=data.index[-1] if not end_date else end_date,
                force_refresh=force_refresh,
            )
            click.echo(f"Loaded S&P 500 benchmark data with {len(benchmark_data)} rows")
            return benchmark_data
        except Exception as e:
            click.echo(f"Warning: Error fetching S&P 500 benchmark data: {str(e)}")
            click.echo("Continuing without benchmark data...")
            return None

    # Check if it's a file path
    if os.path.exists(benchmark):
        click.echo(f"Loading benchmark data from file: {benchmark}...")
        benchmark_data = pd.read_csv(benchmark, index_col=0, parse_dates=True)
        if isinstance(benchmark_data, pd.DataFrame) and benchmark_data.shape[1] > 1:
            benchmark_data = benchmark_data.iloc[:, 0]
        click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")
        return benchmark_data

    # Try as alias
    click.echo(f"Loading benchmark data for alias: {benchmark}...")
    try:
        benchmark_data = fetch_benchmark_data(
            benchmark,
            start_date=data.index[0] if not start_date else start_date,
            end_date=data.index[-1] if not end_date else end_date,
            force_refresh=force_refresh,
        )
        click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")
        return benchmark_data
    except Exception as e:
        click.echo(f"Warning: Error fetching benchmark data: {str(e)}")
        click.echo("Continuing without benchmark data...")
        return None


@click.group()
def cli():
    """AlgoSystemV2 command-line interface."""
    pass


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output-file", "-o", type=click.Path(), default="./dashboard.html",
    help="Path to save the dashboard HTML file (default: ./dashboard.html)",
)
@click.option(
    "--benchmark", "-b",
    help="Benchmark to use. Can be a file path or an alias (e.g., 'sp500', 'nasdaq')",
)
@click.option("--start-date", help="Start date for the backtest (YYYY-MM-DD)")
@click.option("--end-date", help="End date for the backtest (YYYY-MM-DD)")
@click.option(
    "--open-browser", is_flag=True, default=True,
    help="Open the dashboard in a browser after rendering",
)
@click.option(
    "--force-refresh", is_flag=True, default=False,
    help="Force refresh of benchmark data even if cached data exists",
)
def dashboard(input_file, output_file, benchmark, start_date, end_date, open_browser, force_refresh):
    """
    Create a self-contained HTML dashboard from a CSV file.

    INPUT_FILE: Path to a CSV file with strategy data
    """
    from algosystemv2.backtesting.engine import Engine

    try:
        # Load data
        click.echo(f"Loading data from {input_file}...")
        data = pd.read_csv(input_file, index_col=0, parse_dates=True)
        click.echo(f"Loaded data with shape: {data.shape}")

        # Date filtering
        if start_date:
            start_date = pd.to_datetime(start_date)
            data = data[data.index >= start_date]
        if end_date:
            end_date = pd.to_datetime(end_date)
            data = data[data.index <= end_date]

        # Load benchmark
        benchmark_data = _load_benchmark(benchmark, data, start_date, end_date, force_refresh)

        # Extract price data
        if isinstance(data, pd.DataFrame) and data.shape[1] > 1:
            price_data = data.iloc[:, 0]
        else:
            price_data = data

        # Run backtest
        click.echo("Running backtest...")
        engine = Engine(
            data=price_data,
            benchmark=benchmark_data,
            start_date=start_date,
            end_date=end_date,
        )
        engine.run()
        click.echo("Backtest completed successfully")

        # Generate dashboard
        click.echo("Generating dashboard...")
        dashboard_path = engine.generate_dashboard(
            output_path=output_file, open_browser=open_browser
        )

        click.echo(f"Dashboard generated at: {dashboard_path}")
        if not open_browser:
            click.echo(f"Open in browser: file://{os.path.abspath(dashboard_path)}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        click.echo(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.option(
    "--output-dir", "-o", type=click.Path(), default="./test_dashboard",
    help="Directory to save the test dashboard (default: ./test_dashboard)",
)
@click.option(
    "--periods", "-p", type=int, default=252,
    help="Number of trading days to simulate (default: 252 = 1 year)",
)
@click.option("--benchmark", "-b", help="Benchmark alias for comparison", default="sp500")
@click.option(
    "--open-browser", is_flag=True, default=True,
    help="Open the dashboard in a browser when done",
)
def test(output_dir, periods, benchmark, open_browser):
    """
    Run a quick test with simulated data and generate a dashboard.
    """
    from algosystemv2.backtesting.engine import Engine

    click.echo(f"Creating test data with {periods} trading days...")
    os.makedirs(output_dir, exist_ok=True)

    # Try to get benchmark data for date alignment
    benchmark_data = None
    if benchmark and benchmark.lower() != "none":
        try:
            click.echo(f"Loading benchmark data for {benchmark}...")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=periods * 2)
            benchmark_data = fetch_benchmark_data(benchmark, start_date=start_date, end_date=end_date)
            click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")

            if len(benchmark_data) >= periods:
                benchmark_dates = benchmark_data.index[-periods:]
            else:
                benchmark_dates = pd.date_range(end=datetime.now(), periods=periods, freq="B")
        except Exception as e:
            click.echo(f"Warning: Error fetching benchmark data: {str(e)}")
            benchmark_data = None
            benchmark_dates = pd.date_range(end=datetime.now(), periods=periods, freq="B")
    else:
        benchmark_dates = pd.date_range(end=datetime.now(), periods=periods, freq="B")

    # Generate simulated strategy data
    np.random.seed(42)
    returns = np.random.normal(0.005, 0.01, len(benchmark_dates))
    strategy_prices = 100 * (1 + pd.Series(returns, index=benchmark_dates)).cumprod()

    # Save strategy CSV
    strategy_file = os.path.join(output_dir, "strategy.csv")
    strategy_prices.to_csv(strategy_file)

    # Align benchmark data
    if benchmark_data is not None:
        aligned_benchmark = benchmark_data.reindex(strategy_prices.index, method='ffill')
        valid_dates = aligned_benchmark.dropna().index
        if len(valid_dates) < len(strategy_prices) * 0.8:
            click.echo(f"Warning: Poor date alignment. Continuing without benchmark.")
            benchmark_data = None
        else:
            benchmark_data = aligned_benchmark.dropna()
            strategy_prices = strategy_prices.reindex(benchmark_data.index)

    # Run backtest
    click.echo("Running backtest...")
    engine = Engine(data=strategy_prices, benchmark=benchmark_data)
    results = engine.run()

    # Print metrics
    metrics = results["metrics"]
    click.echo(f"\nBacktest Results:")
    click.echo(f"Total Return: {metrics.get('total_return', 0) * 100:.2f}%")
    click.echo(f"Annualized Return: {metrics.get('annualized_return', 0) * 100:.2f}%")
    click.echo(f"Max Drawdown: {metrics.get('max_drawdown', 0) * 100:.2f}%")
    click.echo(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")

    if "alpha" in metrics and metrics.get("alpha") not in (0, None):
        click.echo(f"Alpha: {metrics.get('alpha', 0) * 100:.2f}%")
    if "beta" in metrics and metrics.get("beta") not in (0, None):
        click.echo(f"Beta: {metrics.get('beta', 0):.2f}")

    # Generate dashboard
    click.echo("\nGenerating dashboard...")
    dashboard_path = engine.generate_dashboard(
        output_path=os.path.join(output_dir, "dashboard.html"),
        open_browser=open_browser,
    )

    click.echo(f"Dashboard generated at: {dashboard_path}")
    return dashboard_path


@cli.command()
@click.option("--fetch-all", is_flag=True, default=False, help="Fetch all available benchmarks")
@click.option("--force-refresh", is_flag=True, default=False, help="Force refresh cached data")
@click.option("--info", is_flag=True, default=False, help="Show detailed benchmark info")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.argument("benchmark", required=False)
def benchmarks(fetch_all, force_refresh, info, start_date, end_date, benchmark):
    """
    List, fetch, and manage benchmark data.

    Specify a benchmark alias to fetch data for that benchmark.
    """
    try:
        if start_date:
            start_date = pd.to_datetime(start_date)
        if end_date:
            end_date = pd.to_datetime(end_date)

        if info:
            benchmark_info = get_benchmark_info()
            categories = benchmark_info.groupby("Category")
            click.echo("Available benchmarks by category:\n")
            for category_name, group in categories:
                click.echo(f"=== {category_name} ===")
                for _, row in group.iterrows():
                    click.echo(f"  {row['Alias']}: {row['Description']}")
                click.echo("")
            click.echo(f"Total benchmarks available: {len(benchmark_info)}")
            return

        if not benchmark and not fetch_all:
            benchmark_list = get_benchmark_list()
            click.echo("Available benchmark aliases:")
            col_width = max(len(alias) for alias in benchmark_list) + 2
            for i in range(0, len(benchmark_list), 3):
                row = benchmark_list[i : i + 3]
                click.echo("  " + "".join(alias.ljust(col_width) for alias in row))
            click.echo(f"\nTotal: {len(benchmark_list)} benchmarks available")
            click.echo("Use '--info' for detailed descriptions.")
            return

        if fetch_all:
            click.echo("Fetching data for all benchmarks...")
            from algosystemv2.data.benchmark import fetch_all_benchmarks
            results = fetch_all_benchmarks(start_date=start_date, end_date=end_date, force_refresh=force_refresh)
            click.echo(f"Successfully fetched data for {len(results)} benchmarks.")
            return

        if benchmark:
            click.echo(f"Fetching data for benchmark: {benchmark}")
            benchmark_data = fetch_benchmark_data(
                benchmark, start_date=start_date, end_date=end_date, force_refresh=force_refresh,
            )
            click.echo(f"Successfully fetched benchmark data: {benchmark}")
            click.echo(f"Data shape: {benchmark_data.shape}")
            click.echo(f"Date range: {benchmark_data.index[0].date()} to {benchmark_data.index[-1].date()}")

            returns = benchmark_data.pct_change().dropna()
            total_return = (benchmark_data.iloc[-1] / benchmark_data.iloc[0]) - 1
            annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
            volatility = returns.std() * np.sqrt(252)

            click.echo(f"Total return: {total_return:.2%}")
            click.echo(f"Annualized return: {annualized_return:.2%}")
            click.echo(f"Annualized volatility: {volatility:.2%}")

    except Exception as e:
        click.echo(f"Error: {str(e)}")
        click.echo(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("benchmark_list", nargs=-1, required=True)
@click.option("--output-file", "-o", type=click.Path(), help="Save comparison to CSV")
@click.option("--start-date", help="Start date (YYYY-MM-DD)")
@click.option("--end-date", help="End date (YYYY-MM-DD)")
@click.option("--metrics", is_flag=True, default=False, help="Show performance metrics")
@click.option("--force-refresh", is_flag=True, default=False, help="Force refresh cached data")
def compare_benchmarks(benchmark_list, output_file, start_date, end_date, metrics, force_refresh):
    """
    Compare multiple benchmarks over the same period.

    Example: algosystemv2 compare-benchmarks sp500 nasdaq gold
    """
    try:
        from algosystemv2.data.benchmark import compare_benchmarks as _compare, get_benchmark_metrics

        if start_date:
            start_date = pd.to_datetime(start_date)
        if end_date:
            end_date = pd.to_datetime(end_date)

        click.echo(f"Comparing benchmarks: {', '.join(benchmark_list)}")
        comparison_df = _compare(benchmark_list, start_date=start_date, end_date=end_date)

        click.echo(f"Period: {comparison_df.index[0].date()} to {comparison_df.index[-1].date()}")
        click.echo(f"Trading days: {len(comparison_df)}")

        # Total returns sorted
        total_returns = {}
        for col in comparison_df.columns:
            total_returns[col] = (comparison_df[col].iloc[-1] / comparison_df[col].iloc[0]) - 1
        sorted_bm = sorted(total_returns.items(), key=lambda x: x[1], reverse=True)

        click.echo("\nTotal Returns:")
        for bm, ret in sorted_bm:
            click.echo(f"  {bm}: {ret:.2%}")

        if metrics:
            click.echo("\nPerformance Metrics:")
            for alias in benchmark_list:
                try:
                    bm_metrics = get_benchmark_metrics(alias, start_date=start_date, end_date=end_date)
                    click.echo(f"\n  {alias}:")
                    click.echo(f"    Total Return: {bm_metrics['total_return'] * 100:.2f}%")
                    click.echo(f"    Annual Return: {bm_metrics['annualized_return'] * 100:.2f}%")
                    click.echo(f"    Volatility: {bm_metrics['volatility'] * 100:.2f}%")
                    click.echo(f"    Sharpe Ratio: {bm_metrics['sharpe_ratio']:.2f}")
                    click.echo(f"    Max Drawdown: {bm_metrics['max_drawdown'] * 100:.2f}%")
                except Exception as e:
                    click.echo(f"  Warning: Could not calculate metrics for {alias}: {str(e)}")

        if output_file:
            comparison_df.to_csv(output_file)
            click.echo(f"\nComparison data saved to: {output_file}")

    except Exception as e:
        click.echo(f"Error: {str(e)}")
        click.echo(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    cli()
