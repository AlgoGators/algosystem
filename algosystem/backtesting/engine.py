import pandas as pd
import numpy as np
import os
import shutil
import json
import webbrowser
import matplotlib.pyplot as plt

from algosystem.utils._logging import get_logger
from algosystem.backtesting.visualization import (
    create_equity_chart,
    create_drawdown_chart,
    create_monthly_returns_heatmap,
    create_rolling_sharpe_chart
)

from algosystem.backtesting import metrics

logger = get_logger(__name__)

class Engine:
    """Backtesting engine that uses a price series (e.g. portfolio value) as input."""
    
    def __init__(self, data, benchmark, start_date=None, end_date=None, 
                 initial_capital=None, price_column=None):
        """
        Initialize the backtesting engine using a price series.
        
        Parameters:
        -----------
        data : pd.DataFrame or pd.Series
            Historical data of the strategy’s portfolio value.
            If a DataFrame is provided, you must either pass a price_column or ensure it has one column.
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
                    raise ValueError("DataFrame has multiple columns; specify price_column.")
        elif isinstance(data, pd.Series):
            self.price_series = data.copy()
        else:
            raise TypeError("data must be a pandas DataFrame or Series")
        
        
        self.benchmark_series = benchmark.copy() if benchmark is not None else None

        # Set date range based on provided dates or available index
        self.start_date = pd.to_datetime(start_date) if start_date else self.price_series.index[0]
        self.end_date = pd.to_datetime(end_date) if end_date else self.price_series.index[-1]
        mask = (self.price_series.index >= self.start_date) & (self.price_series.index <= self.end_date)
        self.price_series = self.price_series.loc[mask]
        
        if self.price_series.empty:
            raise ValueError("No data available for the specified date range")
        
        # Use the provided initial_capital or infer it from the first value
        self.initial_capital = initial_capital if initial_capital is not None else self.price_series.iloc[0]
        
        self.results = None
        self.metrics = None
        self.plots = None

        logger.info(f"Initialized backtest from {self.start_date.date()} to {self.end_date.date()}")
        
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
        equity_series = self.initial_capital * (self.price_series / self.price_series.iloc[0])

        logger.info("Calculating performance metrics")
        self.metrics = metrics.calculate_metrics(equity_series, self.benchmark_series)

        logger.info("Generating performance plots")
        # Fix: Pass benchmark_series instead of initial_capital
        self.plots = metrics.calculate_time_series_data(equity_series, self.benchmark_series)
        
        self.results = {
            'equity': equity_series,
            # Positions and trades are not computed in this model because the data
            # represents the final portfolio value. If desired, you can derive additional metrics.
            'initial_capital': self.initial_capital,
            'final_capital': equity_series.iloc[-1],
            'returns': (equity_series.iloc[-1] - self.initial_capital) / self.initial_capital,
            'data': self.price_series,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'metrics': self.metrics,
            'plots': self.plots,
        }
        
        logger.info(f"Backtest completed. Final return: {self.results['returns']:.2%}")
        return self.results
    
    def get_results(self):
        return self.results

    def get_metrics(self):
        return self.metrics
    
    def print_metrics(self):
        """
        Print performance metrics to console.
        """
        metrics = self.get_metrics()
        logger.info("Performance Metrics:")
        for key, value in metrics.items():
            logger.info(f"{key}: {value}")
    
    def get_plots(self, output_path=None, show_charts=True):
        """
        Generate, save, and return performance plots.

        Parameters:
        -----------
        output_path : str, optional
            Directory in which to save the plots.
            If not provided, defaults to a subfolder named 'plots' in the current working directory.
        show_charts : bool, optional
            If True, display the charts interactively. If False, the charts will not be shown.

        Returns:
        --------
        plots : dict
            Dictionary containing matplotlib figure objects for each plot.
        """
        # Extract the equity series from the results for those plots that require it:
        equity_series = self.results['equity']

        equity_chart = create_equity_chart(equity_series)
        drawdown_chart = create_drawdown_chart(equity_series)
        monthly_returns_heatmap = create_monthly_returns_heatmap(equity_series)
        rolling_sharpe_chart = create_rolling_sharpe_chart(equity_series)

        plots = {
            'equity_chart': equity_chart,
            'drawdown_chart': drawdown_chart,
            'monthly_returns_heatmap': monthly_returns_heatmap,
            'rolling_sharpe_chart': rolling_sharpe_chart
        }

        # Set default output path if none provided; default to "./plots"
        if output_path is None:
            output_path = os.path.join(os.getcwd(), "plots")
        else:
            output_path = os.path.abspath(output_path)

        # Create the directory if it doesn't exist.
        os.makedirs(output_path, exist_ok=True)

        # Save each plot to a separate PNG file.
        for key, fig in plots.items():
            file_path = os.path.join(output_path, f"{key}.png")
            fig.savefig(file_path)
            print(f"Saved {key} to {file_path}")

        # If show_charts is True, display the plots interactively.
        if show_charts:
            # Turn interactive mode off to force blocking behavior.
            plt.ioff()
            # This call will block until all open figure windows are closed.
            plt.show(block=True)

        return plots
    
    def _format_time_series(self, series):
        """Format a time series for the dashboard"""
        if series is None or series.empty:
            return []
        
        result = []
        for date, value in series.items():
            # Convert date to string
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            
            # Handle NumPy types
            if isinstance(value, (np.integer, np.floating)):
                value_float = float(value.item())
            else:
                value_float = float(value) if pd.notna(value) else None
            
            result.append({'date': date_str, 'value': value_float})
        
        return result

    def generate_dashboard(self, output_dir=None, open_browser=True, config_path=None):
        """
        Generate an HTML dashboard for the backtest results based on graph_config.json
        
        Parameters:
        -----------
        output_dir : str, optional
            Directory where dashboard files will be saved. Defaults to ./dashboard/
        open_browser : bool, optional
            Whether to automatically open the dashboard in browser. Defaults to True
        config_path : str, optional
            Path to the graph configuration file. Defaults to utils/graph_config.json
            
        Returns:
        --------
        dashboard_path : str
            Path to the generated dashboard HTML file
        """
        from .dashboard.dashboard_generator import generate_dashboard
        return generate_dashboard(self, output_dir, open_browser, config_path)
