import matplotlib.pyplot as plt
import pandas as pd

from algosystem.backtesting import metrics
from algosystem.utils._logging import get_logger

logger = get_logger(__name__)


class Engine:
    """Backtesting engine that uses a price series (e.g. portfolio value) as input."""

    def __init__(
        self,
        data,
        benchmark=None,
        start_date=None,
        end_date=None,
        initial_capital=None,
        price_column=None,
    ):
        """
        Initialize the backtesting engine using a price series.

        Parameters:
        -----------
        data : pd.DataFrame or pd.Series
            Historical data of the strategy's portfolio value.
            If a DataFrame is provided, you must either pass a price_column or ensure it has one column.
        benchmark : pd.DataFrame or pd.Series, optional
            Benchmark data to compare against
        start_date : str, optional
            Start date for the backtest (YYYY-MM-DD). Defaults to the first date in data.
        end_date : str, optional
            End date for the backtest (YYYY-MM-DD). Defaults to the last date in data.
        initial_capital : float, optional
            Initial capital. If not provided, inferred as the first value of the price series.
        price_column : str, optional
            If data is a DataFrame with multiple columns, specify the column name representing
            portfolio value.
        """
        # Support for DataFrame or Series input
        if isinstance(data, pd.DataFrame):
            if price_column is not None:
                self.price_series = data[price_column].copy()
            else:
                if data.shape[1] == 1:
                    self.price_series = data.iloc[:, 0].copy()
                else:
                    raise ValueError(
                        "DataFrame has multiple columns; specify price_column."
                    )
        elif isinstance(data, pd.Series):
            self.price_series = data.copy()
        else:
            raise TypeError("data must be a pandas DataFrame or Series")

        # Handle benchmark data
        self.benchmark_series = None
        if benchmark is not None:
            if isinstance(benchmark, pd.DataFrame):
                if benchmark.shape[1] == 1:
                    self.benchmark_series = benchmark.iloc[:, 0].copy()
                else:
                    raise ValueError(
                        "Benchmark DataFrame has multiple columns; only first column will be used"
                    )
            elif isinstance(benchmark, pd.Series):
                self.benchmark_series = benchmark.copy()
            else:
                raise TypeError("benchmark must be a pandas DataFrame or Series")

        # Set date range based on provided dates or available index
        self.start_date = (
            pd.to_datetime(start_date) if start_date else self.price_series.index[0]
        )
        self.end_date = (
            pd.to_datetime(end_date) if end_date else self.price_series.index[-1]
        )
        mask = (self.price_series.index >= self.start_date) & (
            self.price_series.index <= self.end_date
        )
        self.price_series = self.price_series.loc[mask]

        # Apply same date filter to benchmark if it exists
        if self.benchmark_series is not None:
            benchmark_mask = (self.benchmark_series.index >= self.start_date) & (
                self.benchmark_series.index <= self.end_date
            )
            self.benchmark_series = self.benchmark_series.loc[benchmark_mask]

        if self.price_series.empty:
            raise ValueError("No data available for the specified date range")

        # Use the provided initial_capital or infer it from the first value
        self.initial_capital = (
            initial_capital
            if initial_capital is not None
            else self.price_series.iloc[0]
        )

        self.results = None
        self.metrics_data = None
        self.plots = None

        if hasattr(self.start_date, "date"):
            logger.info(
                f"Initialized backtest from {self.start_date.date()} to {self.end_date.date()}"
            )
        else:
            logger.info(
                f"Initialized backtest from {self.start_date} to {self.end_date}"
            )

    def run(self):
        """
        Run the backtest simulation.

        Since the input data is already the price series of your strategy,
        we interpret the data as the evolution of portfolio value. The engine
        normalizes the price series with respect to the first day, then scales it
        by the initial capital.

        Returns:
        --------
        results : dict
            Dictionary containing backtest results.
        """
        logger.info("Starting backtest simulation")

        # Normalize the price series relative to its first value and scale by initial capital.
        equity_series = self.initial_capital * (
            self.price_series / self.price_series.iloc[0]
        )

        logger.info("Calculating performance metrics")
        # Calculate metrics
        self.metrics_data = metrics.calculate_metrics(
            equity_series, self.benchmark_series
        )

        logger.info("Calculating time series data")
        # Calculate time series data
        self.plots = metrics.calculate_time_series_data(
            equity_series, self.benchmark_series
        )

        self.results = {
            "equity": equity_series,
            "initial_capital": self.initial_capital,
            "final_capital": equity_series.iloc[-1],
            "returns": (equity_series.iloc[-1] - self.initial_capital) / self.initial_capital,
            "data": self.price_series,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "metrics": self.metrics_data,
            "plots": self.plots,
        }

        logger.info(f"Backtest completed. Final return: {self.results['returns']:.2%}")
        return self.results

    def get_results(self):
        """Get the full results dictionary."""
        if self.results is None:
            logger.warning("No results available. Run the backtest first.")
            return {}
        return self.results

    def get_metrics(self):
        """Get the metrics dictionary."""
        if self.metrics_data is None:
            logger.warning("No metrics available. Run the backtest first.")
            return {}
        return self.metrics_data

    def print_metrics(self):
        """Print performance metrics to console."""
        metrics = self.get_metrics()
        if not metrics:
            logger.warning("No metrics available. Run the backtest first.")
            return

        logger.info("Performance Metrics:")
        for key, value in metrics.items():
            logger.info(f"{key}: {value}")

    def get_plots(self, show_charts=False):
        """
        Get the plot data and optionally display charts.

        Parameters:
        -----------
        show_charts : bool, optional
            Whether to display the charts using matplotlib. Defaults to False.

        Returns:
        --------
        plots : dict
            Dictionary containing plot data
        """
        if self.plots is None:
            logger.warning("No plots available. Run the backtest first.")
            return {}

        if show_charts:
            self._display_charts()

        return self.plots

    def _display_charts(self):
        """Display important charts using matplotlib."""
        if self.results is None or self.plots is None:
            logger.warning("No results available. Run the backtest first.")
            return

        # Create a figure with 2x2 subplots
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))

        # Plot equity curve
        axs[0, 0].plot(self.results["equity"])
        axs[0, 0].set_title("Equity Curve")
        axs[0, 0].set_xlabel("Date")
        axs[0, 0].set_ylabel("Value")
        axs[0, 0].grid(True)

        # Plot drawdown
        if "drawdown_series" in self.plots:
            axs[0, 1].fill_between(
                self.plots["drawdown_series"].index,
                0,
                self.plots["drawdown_series"],
                color="red",
                alpha=0.3,
            )
            axs[0, 1].set_title("Drawdown")
            axs[0, 1].set_xlabel("Date")
            axs[0, 1].set_ylabel("Drawdown")
            axs[0, 1].grid(True)

        # Plot rolling Sharpe ratio
        if "rolling_sharpe" in self.plots:
            axs[1, 0].plot(self.plots["rolling_sharpe"])
            axs[1, 0].set_title("Rolling Sharpe Ratio")
            axs[1, 0].set_xlabel("Date")
            axs[1, 0].set_ylabel("Sharpe Ratio")
            axs[1, 0].grid(True)

        # Plot monthly returns
        if "monthly_returns" in self.plots:
            monthly_returns = self.plots["monthly_returns"]
            axs[1, 1].bar(monthly_returns.index, monthly_returns)
            axs[1, 1].set_title("Monthly Returns")
            axs[1, 1].set_xlabel("Date")
            axs[1, 1].set_ylabel("Return")
            axs[1, 1].grid(True)

        plt.tight_layout()
        plt.show()

        return fig

    def generate_dashboard(self, output_dir=None, open_browser=True, config_path=None):
        """
        Generate an HTML dashboard for the backtest results.

        Parameters:
        -----------
        output_dir : str, optional
            Directory where dashboard files will be saved. Defaults to ./dashboard/
        open_browser : bool, optional
            Whether to automatically open the dashboard in browser. Defaults to True
        config_path : str, optional
            Path to the graph configuration file.

        Returns:
        --------
        dashboard_path : str
            Path to the generated dashboard HTML file
        """
        if self.results is None:
            logger.warning("No results available. Running backtest first.")
            self.run()

        from algosystem.backtesting.dashboard.dashboard_generator import (
            generate_dashboard,
        )

        return generate_dashboard(self, output_dir, open_browser, config_path)

    def generate_standalone_dashboard(self, output_path=None):
        """
        Generate a standalone HTML dashboard that doesn't require a web server.

        Parameters:
        -----------
        output_path : str, optional
            Path where the standalone HTML file will be saved

        Returns:
        --------
        output_path : str
            Path to the generated standalone HTML file
        """
        if self.results is None:
            logger.warning("No results available. Running backtest first.")
            self.run()

        from algosystem.backtesting.dashboard.dashboard_generator import (
            generate_standalone_dashboard,
        )

        return generate_standalone_dashboard(self, output_path)

    def export_db(self, run_id=None, name="Backtest", description="", hyperparameters=None, include_positions=True, include_pnl=True):
        """
        Export backtest results to the database.

        Parameters:
        -----------
        run_id : int or str, optional
            Unique identifier for this backtest run. If not provided, a new ID is generated.
        name : str, optional
            Name for this backtest run. Defaults to "Backtest".
        description : str, optional
            Description of this backtest run.
        hyperparameters : dict, optional
            Dictionary of hyperparameters used in this backtest.
        include_positions : bool, optional
            Whether to export final positions data (if available). Defaults to True.
        include_pnl : bool, optional
            Whether to export symbol PnL data (if available). Defaults to True.

        Returns:
        --------
        int or str
            The run_id used for the export

        Notes:
        ------
        - Requires database connection parameters in .env file
        - Database schema must exist with the required tables (see documentation)
        """
        # Check if results are available
        if self.results is None:
            logger.warning("No results available. Running backtest first.")
            self.run()

            if self.results is None:
                raise ValueError("No results available to export to database.")

        from algosystem.data.connectors.db_manager import DBManager
        
        # Create DB manager instance
        db = DBManager()

        # Get or generate run_id
        if run_id is None:
            # Generate a unique run_id
            run_id = db.get_next_run_id()
        
        # Ensure run_id is a string
        run_id = str(run_id)

        # Prepare data for export
        equity_curve = self.results.get("equity")
        metrics = self.results.get("metrics", {})

        # Extract configuration if available
        config = {
            "start_date": self.start_date.strftime("%Y-%m-%d")
            if hasattr(self.start_date, "strftime")
            else str(self.start_date),
            "end_date": self.end_date.strftime("%Y-%m-%d")
            if hasattr(self.end_date, "strftime")
            else str(self.end_date),
            "initial_capital": float(self.initial_capital),
            "benchmark": self.benchmark_series is not None,
        }

        # Prepare final positions data if available and requested
        final_positions = None
        if include_positions and hasattr(self, "positions") and self.positions is not None:
            final_positions = self.positions

        # Prepare symbol PnL data if available and requested
        symbol_pnl = None
        if include_pnl and hasattr(self, "symbol_pnl") and self.symbol_pnl is not None:
            symbol_pnl = self.symbol_pnl

        # Export to database
        run_id = db.export_backtest_results(
            run_id=run_id,
            name=name,
            description=description,
            hyperparameters=hyperparameters,
            equity_curve=equity_curve,
            final_positions=final_positions,
            symbol_pnl=symbol_pnl,
            metrics=metrics,
            config=config,
        )

        logger.info(f"Successfully exported backtest results to database with run_id: {run_id}")

        return run_id

