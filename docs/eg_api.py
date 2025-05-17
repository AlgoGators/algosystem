"""
Usage examples for the AlgoSystem API.
This script demonstrates how to use the enhanced API for backtesting and visualization.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime

from algosystem.api import AlgoSystem, quick_backtest


# Create sample data for demonstration
def create_sample_data(n_periods=252):
    """Create sample price series data for testing."""
    dates = pd.date_range(start="2022-01-01", periods=n_periods, freq="B")
    np.random.seed(42)  # For reproducibility

    # Generate random returns with positive drift
    returns = np.random.normal(0.0005, 0.01, n_periods)
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

    return prices


# Create sample benchmark data
def create_benchmark_data(n_periods=252):
    """Create sample benchmark data for testing."""
    dates = pd.date_range(start="2022-01-01", periods=n_periods, freq="B")
    np.random.seed(123)  # Different seed for benchmark

    # Generate benchmark returns with less drift
    returns = np.random.normal(0.0003, 0.008, n_periods)
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

    return prices


# Example 1: Quick backtest with default settings
def example_quick_backtest():
    """Run a quick backtest and print results."""
    print("\n=== Example 1: Quick Backtest ===")

    # Create sample data
    strategy_data = create_sample_data()
    benchmark_data = create_benchmark_data()

    # Run the backtest and print results
    engine = quick_backtest(strategy_data, benchmark_data)

    return engine


# Example 2: Generate dashboard and export data
def example_dashboard_and_export(engine=None):
    """Generate a dashboard and export data."""
    print("\n=== Example 2: Dashboard and Exports ===")

    if engine is None:
        # Create and run backtest if no engine was provided
        strategy_data = create_sample_data()
        benchmark_data = create_benchmark_data()
        engine = AlgoSystem.run_backtest(strategy_data, benchmark_data)

    # Generate a dashboard
    dashboard_path = AlgoSystem.generate_dashboard(
        engine,
        output_dir="./dashboard_output",
        open_browser=False,  # Set to True to open in browser
    )
    print(f"Dashboard generated at: {dashboard_path}")

    # Export data to CSV
    csv_path = "./exports/backtest_data.csv"
    AlgoSystem.export_data(engine, csv_path, format="csv")
    print(f"Data exported to CSV: {csv_path}")

    # Export data to Excel
    excel_path = "./exports/backtest_data.xlsx"
    AlgoSystem.export_data(engine, excel_path, format="excel")
    print(f"Data exported to Excel: {excel_path}")

    return engine


# Example 3: Export charts
def example_export_charts(engine=None):
    """Export all charts as images."""
    print("\n=== Example 3: Export Charts ===")

    if engine is None:
        # Create and run backtest if no engine was provided
        strategy_data = create_sample_data()
        benchmark_data = create_benchmark_data()
        engine = AlgoSystem.run_backtest(strategy_data, benchmark_data)

    # Export all charts
    chart_paths = AlgoSystem.export_charts(
        engine, output_dir="./plots", dpi=300  # Higher resolution
    )

    print(f"Exported {len(chart_paths)} charts to './plots/' directory")

    return engine


# Example 4: Working with configurations
def example_configuration():
    """Load, modify and save dashboard configurations."""
    print("\n=== Example 4: Dashboard Configurations ===")

    # List available configurations
    print("Available configurations:")
    AlgoSystem.list_configs()

    # Load default configuration
    config = AlgoSystem.load_config()
    print(
        f"Loaded configuration with {len(config.get('metrics', []))} metrics and {len(config.get('charts', []))} charts"
    )

    # Modify configuration
    config["layout"]["title"] = f"Modified Dashboard - {datetime.now().strftime('%Y-%m-%d')}"

    # Add a new metric if not already present
    if not any(m["id"] == "custom_metric" for m in config["metrics"]):
        config["metrics"].append(
            {
                "id": "custom_metric",
                "type": "Value",
                "title": "Custom Metric",
                "value_key": "sharpe_ratio",  # Using existing data
                "position": {"row": 0, "col": 3},
            }
        )

    # Save the modified configuration
    output_path = "./custom_dashboard_config.json"
    AlgoSystem.save_config(config, output_path)
    print(f"Saved modified configuration to: {output_path}")


# Example 5: Standalone dashboard
def example_standalone_dashboard(engine=None):
    """Generate a standalone dashboard."""
    print("\n=== Example 5: Standalone Dashboard ===")

    if engine is None:
        # Create and run backtest if no engine was provided
        strategy_data = create_sample_data()
        benchmark_data = create_benchmark_data()
        engine = AlgoSystem.run_backtest(strategy_data, benchmark_data)

    # Generate a standalone dashboard
    dashboard_path = AlgoSystem.generate_standalone_dashboard(
        engine, output_path="./standalone_dashboard.html"
    )

    print(f"Standalone dashboard generated at: {dashboard_path}")


# Run all examples
if __name__ == "__main__":
    # Make sure output directories exist
    os.makedirs("./dashboard_output", exist_ok=True)
    os.makedirs("./exports", exist_ok=True)
    os.makedirs("./plots", exist_ok=True)

    # Run examples
    engine = example_quick_backtest()
    engine = example_dashboard_and_export(engine)
    engine = example_export_charts(engine)
    example_configuration()
    example_standalone_dashboard(engine)

    print("\nAll examples completed successfully!")
