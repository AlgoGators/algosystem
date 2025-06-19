"""
Enhanced AlgoSystem API - provides a comprehensive Python interface to all functionality.
"""

import os

import matplotlib.pyplot as plt
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from algosystem.backtesting import Engine
from algosystem.backtesting.dashboard.utils.default_config import get_default_config
from algosystem.data.benchmark import (
    DEFAULT_BENCHMARK,
    fetch_benchmark_data,
    get_benchmark_info,
    get_benchmark_list,
)
from algosystem.utils._logging import get_logger

logger = get_logger(__name__)
console = Console()


class AlgoSystem:
    """
    Main API class for AlgoSystem - provides programmatic access to all functionality.
    """

    @staticmethod
    def run_backtest(
        data,
        benchmark=None,
        start_date=None,
        end_date=None,
        initial_capital=None,
        price_column=None,
    ):
        """
        Run a backtest using the provided data.

        Parameters:
        -----------
        data : pd.DataFrame or pd.Series
            Price series data or DataFrame containing price data
        benchmark : pd.DataFrame or pd.Series, optional
            Benchmark data to compare against
        start_date : str, optional
            Start date for the backtest (YYYY-MM-DD)
        end_date : str, optional
            End date for the backtest (YYYY-MM-DD)
        initial_capital : float, optional
            Initial capital for the backtest
        price_column : str, optional
            If data is a DataFrame with multiple columns, specify the column name representing portfolio value

        Returns:
        --------
        engine : Engine
            Backtesting engine instance with results
        """
        engine = Engine(
            data=data,
            benchmark=benchmark,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            price_column=price_column,
        )

        # Run the backtest
        results = engine.run()

        return engine

    @staticmethod
    def print_results(engine, detailed=False):
        """
        Print backtest results to the terminal using rich formatting.

        Parameters:
        -----------
        engine : Engine
            Backtesting engine instance with results
        detailed : bool, optional
            Whether to show detailed metrics
        """
        if engine.results is None:
            console.print(
                "[bold red]No results available. Run the backtest first.[/bold red]"
            )
            return

        results = engine.results
        metrics = results.get("metrics", {})

        # Print summary panel
        console.print(
            Panel(
                f"[bold blue]Backtest Summary[/bold blue]\n"
                f"Period: {results['start_date'].strftime('%Y-%m-%d')} to {results['end_date'].strftime('%Y-%m-%d')}\n"
                f"Initial Capital: ${results['initial_capital']:,.2f}\n"
                f"Final Capital: ${results['final_capital']:,.2f}\n"
                f"Total Return: {results['returns'] * 100:.2f}%",
                title="AlgoSystem Results",
                expand=False,
            )
        )

        # Create metrics table
        table = Table(title="Performance Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        # Essential metrics to show
        essential_metrics = [
            ("total_return", "Total Return", lambda x: f"{x * 100:.2f}%"),
            ("annualized_return", "Annualized Return", lambda x: f"{x * 100:.2f}%"),
            ("sharpe_ratio", "Sharpe Ratio", lambda x: f"{x:.2f}"),
            ("max_drawdown", "Max Drawdown", lambda x: f"{x * 100:.2f}%"),
            ("volatility", "Volatility", lambda x: f"{x * 100:.2f}%"),
        ]

        # Add essential metrics to table
        for key, label, formatter in essential_metrics:
            if key in metrics:
                table.add_row(label, formatter(metrics[key]))

        # Add benchmark metrics if available
        if "alpha" in metrics:
            table.add_row("Alpha", f"{metrics['alpha'] * 100:.2f}%")
        if "beta" in metrics:
            table.add_row("Beta", f"{metrics['beta']:.2f}")

        console.print(table)

        # Print more detailed metrics if requested
        if detailed:
            detailed_table = Table(title="Detailed Metrics")
            detailed_table.add_column("Metric", style="cyan")
            detailed_table.add_column("Value", style="green")

            for key, value in metrics.items():
                # Skip metrics already shown
                if key in [m[0] for m in essential_metrics] or key in ["alpha", "beta"]:
                    continue

                # Format based on metric type
                if isinstance(value, float):
                    if "ratio" in key or "return" in key:
                        formatted_value = f"{value:.4f}"
                    elif "percentage" in key or key.endswith("_pct"):
                        formatted_value = f"{value * 100:.2f}%"
                    else:
                        formatted_value = f"{value:.4f}"
                else:
                    formatted_value = str(value)

                detailed_table.add_row(key, formatted_value)

            console.print(detailed_table)

    @staticmethod
    def generate_dashboard(
        engine, output_dir=None, open_browser=True, config_path=None
    ):
        """
        Generate an interactive HTML dashboard for the backtest results.

        Parameters:
        -----------
        engine : Engine
            Backtesting engine instance with results
        output_dir : str, optional
            Directory where dashboard files will be saved
        open_browser : bool, optional
            Whether to automatically open the dashboard in browser
        config_path : str, optional
            Path to the dashboard configuration file

        Returns:
        --------
        dashboard_path : str
            Path to the generated dashboard HTML file
        """
        if engine.results is None:
            logger.warning("No results available. Running backtest.")
            engine.run()

        # Use default configuration if none provided
        if config_path is None:
            # Check for config in user directory
            user_config = os.path.join(
                os.path.expanduser("~"), ".algosystem", "dashboard_config.json"
            )
            if os.path.exists(user_config):
                logger.info(f"Using configuration from {user_config}")
                config_path = user_config

        # Generate the dashboard
        dashboard_path = engine.generate_dashboard(
            output_dir=output_dir, open_browser=open_browser, config_path=config_path
        )

        return dashboard_path

    @staticmethod
    def generate_standalone_dashboard(engine, output_path=None):
        """
        Generate a standalone HTML dashboard that doesn't require a web server.

        Parameters:
        -----------
        engine : Engine
            Backtesting engine instance with results
        output_path : str, optional
            Path where the standalone HTML file will be saved

        Returns:
        --------
        output_path : str
            Path to the generated standalone HTML file
        """
        if engine.results is None:
            logger.warning("No results available. Running backtest.")
            engine.run()

        # Generate the standalone dashboard
        return engine.generate_standalone_dashboard(output_path)

    @staticmethod
    def export_data(engine, output_path, format="csv"):
        """
        Export backtesting data to a file.

        Parameters:
        -----------
        engine : Engine
            Backtesting engine instance with results
        output_path : str
            Path where the data file will be saved
        format : str, optional
            Export format: 'csv' or 'excel'

        Returns:
        --------
        output_path : str
            Path to the exported data file
        """
        if engine.results is None:
            console.print(
                "[bold red]No results available. Run the backtest first.[/bold red]"
            )
            return None

        results = engine.results

        # Create a dictionary of data to export
        export_data = {
            # Core data
            "equity": results["equity"],
            "returns": results["equity"].pct_change(),
        }

        # Add time series data from plots if available
        if "plots" in results and results["plots"]:
            plots = results["plots"]
            for key, series in plots.items():
                if isinstance(series, pd.Series):
                    export_data[key] = series

        # Create DataFrame from the data
        df = pd.DataFrame(export_data)

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Export based on format
        if format.lower() == "csv":
            df.to_csv(output_path)
            logger.info(f"Data exported to CSV: {output_path}")
        elif format.lower() == "excel":
            df.to_excel(output_path)
            logger.info(f"Data exported to Excel: {output_path}")
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'csv' or 'excel'.")

        return output_path

    @staticmethod
    def export_to_db(engine, db_url, table_name="backtest_results"):
        """
        Export backtest results to a database.

        Parameters:
        -----------
        engine : Engine
            Backtesting engine instance with results
        db_url : str
            Database connection URL
        table_name : str, optional
            Name of the table to store results

        Returns:
        --------
        None
        """
        if engine.results is None:
            console.print(
                "[bold red]No results available. Run the backtest first.[/bold red]"
            )
            return

        # Export results to database
        engine.export_to_db(db_url, table_name)

    @staticmethod
    def export_charts(engine, output_dir=None, dpi=300):
        """
        Export all charts as PNG images.

        Parameters:
        -----------
        engine : Engine
            Backtesting engine instance with results
        output_dir : str, optional
            Directory where chart images will be saved. Defaults to 'plots/' in current directory.
        dpi : int, optional
            Image resolution (dots per inch)

        Returns:
        --------
        output_paths : list
            List of paths to the generated chart images
        """
        if engine.results is None:
            console.print(
                "[bold red]No results available. Run the backtest first.[/bold red]"
            )
            return []

        # Set default output directory if not provided
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "plots")

        # Create the output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        results = engine.results
        plots = results.get("plots", {})

        output_paths = []

        # Function to create and save charts
        def save_chart(data, title, filename, y_label=None, chart_type="line"):
            plt.figure(figsize=(10, 6))

            if chart_type == "line":
                plt.plot(data)
            elif chart_type == "bar":
                plt.bar(data.index, data)
            elif chart_type == "area":
                plt.fill_between(data.index, 0, data, alpha=0.3)

            plt.title(title)
            plt.grid(True, alpha=0.3)

            if y_label:
                plt.ylabel(y_label)
            plt.xlabel("Date")

            # Format date axis
            plt.gcf().autofmt_xdate()

            # Save figure
            output_path = os.path.join(output_dir, f"{filename}.png")
            plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
            plt.close()

            logger.info(f"Chart saved: {output_path}")
            return output_path

        # Export main equity curve
        if "equity" in results:
            output_paths.append(
                save_chart(
                    results["equity"], "Portfolio Equity Curve", "equity_curve", "Value"
                )
            )

        # Export drawdown chart
        if "drawdown_series" in plots:
            output_paths.append(
                save_chart(
                    plots["drawdown_series"],
                    "Drawdown",
                    "drawdown",
                    "Drawdown (%)",
                    "area",
                )
            )

        # Export rolling metrics
        for metric_name in ["rolling_sharpe", "rolling_sortino", "rolling_volatility"]:
            if metric_name in plots:
                output_paths.append(
                    save_chart(
                        plots[metric_name],
                        f"{metric_name.replace('rolling_', 'Rolling ').replace('_', ' ').title()}",
                        metric_name,
                        metric_name.replace("rolling_", "").replace("_", " ").title(),
                    )
                )

        # Export monthly returns
        if "monthly_returns" in plots:
            output_paths.append(
                save_chart(
                    plots["monthly_returns"],
                    "Monthly Returns",
                    "monthly_returns",
                    "Return (%)",
                    "bar",
                )
            )

        # Export other available plots
        for name, data in plots.items():
            # Skip plots we've already exported
            if name in [
                "drawdown_series",
                "rolling_sharpe",
                "rolling_sortino",
                "rolling_volatility",
                "monthly_returns",
            ]:
                continue

            if isinstance(data, pd.Series) and not data.empty:
                title = name.replace("_", " ").title()
                output_paths.append(save_chart(data, title, name, title))

        # Compare with benchmark if available
        if "benchmark_equity_curve" in plots:
            plt.figure(figsize=(10, 6))

            # Plot strategy
            plt.plot(results["equity"], label="Strategy")

            # Plot benchmark
            plt.plot(plots["benchmark_equity_curve"], label="Benchmark")

            plt.title("Strategy vs Benchmark")
            plt.grid(True, alpha=0.3)
            plt.ylabel("Value")
            plt.xlabel("Date")
            plt.legend()

            # Format date axis
            plt.gcf().autofmt_xdate()

            # Save figure
            output_path = os.path.join(output_dir, "benchmark_comparison.png")
            plt.savefig(output_path, dpi=dpi, bbox_inches="tight")
            plt.close()

            logger.info(f"Chart saved: {output_path}")
            output_paths.append(output_path)

        console.print(
            f"[green]Successfully exported {len(output_paths)} charts to {output_dir}[/green]"
        )
        return output_paths

    @staticmethod
    def load_config(config_path=None):
        """
        Load a dashboard configuration.

        Parameters:
        -----------
        config_path : str, optional
            Path to the configuration file. If not provided, tries to load from user directory.

        Returns:
        --------
        config : dict
            Dashboard configuration
        """
        import json

        # If no config path is provided, try loading from user directory
        if config_path is None:
            user_config = os.path.join(
                os.path.expanduser("~"), ".algosystem", "dashboard_config.json"
            )
            if os.path.exists(user_config):
                config_path = user_config
            else:
                # Use default configuration
                return get_default_config()

        # Load configuration from file
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            # Fall back to default configuration
            logger.info("Using default configuration")
            return get_default_config()

    @staticmethod
    def save_config(config, output_path=None):
        """
        Save a dashboard configuration.

        Parameters:
        -----------
        config : dict
            Dashboard configuration
        output_path : str, optional
            Path where the configuration will be saved. If not provided, saves to user directory.

        Returns:
        --------
        output_path : str
            Path to the saved configuration file
        """
        import json

        # If no output path is provided, save to user directory
        if output_path is None:
            user_config_dir = os.path.join(os.path.expanduser("~"), ".algosystem")
            os.makedirs(user_config_dir, exist_ok=True)
            output_path = os.path.join(user_config_dir, "dashboard_config.json")

        # Ensure the output directory exists
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Save configuration to file
        try:
            with open(output_path, "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Saved configuration to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return None

    @staticmethod
    def get_benchmark(
        benchmark_alias=DEFAULT_BENCHMARK, start_date=None, end_date=None
    ):
        """
        Get benchmark data for the specified alias.

        Parameters:
        -----------
        benchmark_alias : str, optional
            Benchmark alias (e.g., 'sp500', 'nasdaq', '10y_treasury')
        start_date : str or datetime, optional
            Start date for the data
        end_date : str or datetime, optional
            End date for the data

        Returns:
        --------
        pd.Series
            Benchmark price series
        """
        return fetch_benchmark_data(benchmark_alias, start_date, end_date)

    @staticmethod
    def list_benchmarks():
        """
        List all available benchmark aliases.

        Returns:
        --------
        list
            List of available benchmark aliases
        """
        benchmarks = get_benchmark_list()

        # Print the list in a nice table
        table = Table(title="Available Benchmark Aliases")
        table.add_column("Category", style="cyan")
        table.add_column("Alias", style="green")
        table.add_column("Description", style="yellow")

        # Get benchmark info
        info = get_benchmark_info()

        # Group by category
        for category in info["Category"].unique():
            category_info = info[info["Category"] == category]

            for _, row in category_info.iterrows():
                table.add_row(
                    category
                    if _ == category_info.index[0]
                    else "",  # Only show category once
                    row["Alias"],
                    row["Description"],
                )

        console.print(table)

        return benchmarks

    @staticmethod
    def compare_benchmarks(benchmarks, start_date=None, end_date=None, plot=True):
        """
        Compare multiple benchmarks over the same period.

        Parameters:
        -----------
        benchmarks : list
            List of benchmark aliases to compare
        start_date : str or datetime, optional
            Start date for the data
        end_date : str or datetime, optional
            End date for the data
        plot : bool, optional
            Whether to plot the comparison

        Returns:
        --------
        pd.DataFrame
            DataFrame with normalized price series for each benchmark
        """
        from algosystem.data.benchmark import compare_benchmarks

        # Get comparison data
        comparison_df = compare_benchmarks(benchmarks, start_date, end_date)

        # Plot if requested
        if plot:
            plt.figure(figsize=(12, 6))
            for column in comparison_df.columns:
                plt.plot(comparison_df.index, comparison_df[column], label=column)

            plt.title("Benchmark Comparison (Normalized to 100)")
            plt.xlabel("Date")
            plt.ylabel("Value")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.gcf().autofmt_xdate()
            plt.show()

        return comparison_df

# Convenience function for quick access
def quick_backtest(data, benchmark=None, **kwargs):
    """
    Quickly run a backtest and print the results.

    Parameters:
    -----------
    data : pd.DataFrame or pd.Series
        Price series data or DataFrame containing price data
    benchmark : pd.DataFrame or pd.Series, optional
        Benchmark data to compare against
    **kwargs : dict
        Additional arguments to pass to AlgoSystem.run_backtest()

    Returns:
    --------
    engine : Engine
        Backtesting engine instance with results
    """
    engine = AlgoSystem.run_backtest(data, benchmark, **kwargs)
    AlgoSystem.print_results(engine)
    return engine
