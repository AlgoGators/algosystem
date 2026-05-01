"""
Dashboard generator for AlgoSystemV2.
Uses quantstats to produce a comprehensive HTML tearsheet with interactive charts.
No external dependencies beyond quantstats, no config files, no web server required.
"""

import os
import webbrowser

import numpy as np
import pandas as pd
import quantstats as qs

from algosystemv2.utils._logging import get_logger

logger = get_logger(__name__)


def generate_dashboard(engine, output_path=None, open_browser=True):
    """
    Generate a self-contained HTML dashboard for backtest results.

    Uses quantstats to generate a full tearsheet with performance metrics,
    drawdown analysis, rolling statistics, monthly heatmaps, and more.

    Parameters:
    -----------
    engine : Engine
        Backtesting engine with results
    output_path : str, optional
        Path where the HTML file will be saved. Defaults to ./dashboard.html
    open_browser : bool, optional
        Whether to automatically open the dashboard in browser. Defaults to True

    Returns:
    --------
    str
        Path to the generated dashboard HTML file
    """
    if engine.results is None:
        engine.run()
        if engine.results is None:
            raise ValueError("No backtest results available. Run the backtest first.")

    if output_path is None:
        output_path = os.path.join(os.getcwd(), "dashboard.html")

    # Ensure output directory exists
    output_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(output_dir, exist_ok=True)

    # Extract the equity series and compute returns
    equity = engine.results.get("equity")
    if equity is None or equity.empty:
        raise ValueError("No equity data available in results.")

    strategy_returns = equity.pct_change().dropna()

    # Extract benchmark returns if available
    benchmark_returns = None
    if engine.benchmark_series is not None:
        benchmark_clean = engine.benchmark_series.dropna()
        if len(benchmark_clean) > 1:
            benchmark_returns = benchmark_clean.pct_change().dropna()
            # Align with strategy returns
            strategy_returns, benchmark_returns = strategy_returns.align(
                benchmark_returns, join="inner"
            )

    # Generate the quantstats HTML tearsheet
    qs.reports.html(
        strategy_returns,
        benchmark=benchmark_returns,
        title="AlgoSystem Dashboard",
        output=output_path,
        download_filename="algosystem-dashboard.html",
    )

    logger.info(f"Dashboard generated at: {output_path}")

    if open_browser:
        webbrowser.open("file://" + os.path.abspath(output_path))

    return output_path
