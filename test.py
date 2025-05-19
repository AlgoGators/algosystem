#!/usr/bin/env python3
"""
Example script demonstrating how to use the database functionality in AlgoSystem.
This shows how to export backtest results, query existing backtests, and analyze backtest performance.
"""

import os
import sys
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# Add the parent directory to the path if running as script
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from algosystem.backtesting import Engine
from algosystem.data.connectors.db_manager import DBManager


def generate_sample_backtest_data(days=100, volatility=0.015, drift=0.0005):
    """Generate sample backtest data for demonstration."""
    np.random.seed(42)  # For reproducibility
    
    # Create a date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq="B")
    
    # Generate returns with drift and volatility
    returns = np.random.normal(drift, volatility, len(dates))
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    
    return prices


def create_benchmark_data(prices, beta=0.8, idiosyncratic_vol=0.01):
    """Create a correlated benchmark series."""
    np.random.seed(43)  # Different seed from main series
    
    # Generate correlated benchmark returns
    market_returns = prices.pct_change().dropna()
    benchmark_returns = np.zeros(len(market_returns))
    
    for i in range(len(market_returns)):
        # Beta * market return + idiosyncratic return
        benchmark_returns[i] = (
            beta * market_returns.iloc[i] +
            np.random.normal(0.0003, idiosyncratic_vol)
        )
    
    # Convert returns to prices
    benchmark_start = 100
    benchmark_prices = pd.Series(
        [benchmark_start], index=[market_returns.index[0] - pd.Timedelta(days=1)]
    )
    
    for i, date in enumerate(market_returns.index):
        next_price = benchmark_prices.iloc[-1] * (1 + benchmark_returns[i])
        benchmark_prices = pd.concat(
            [benchmark_prices, pd.Series([next_price], index=[date])]
        )
    
    return benchmark_prices


def run_backtest_and_export(strategy_name, description=None):
    """Run a backtest with the provided name and export to database."""
    # Generate sample data
    prices = generate_sample_backtest_data(days=252)  # 1 year of data
    benchmark = create_benchmark_data(prices)
    
    # Create a dictionary of hyperparameters for this "strategy"
    hyperparameters = {
        "volatility": 0.015,
        "drift": 0.0005,
        "beta": 0.8,
        "data_period": 252,
        "strategy_type": "momentum",
        "rebalance_frequency": "daily"
    }
    
    # Create and run engine
    engine = Engine(prices, benchmark=benchmark)
    results = engine.run()
    
    # Print summary
    metrics = results["metrics"]
    print(f"\nBacktest Results for '{strategy_name}':")
    print(f"Total Return: {metrics['total_return'] * 100:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {metrics['max_drawdown'] * 100:.2f}%")
    print(f"Beta: {metrics.get('beta', 'N/A')}")
    
    # Export to database
    run_id = engine.export_db(
        name=strategy_name,
        description=description or f"Auto-generated {strategy_name} strategy backtest",
        hyperparameters=hyperparameters
    )
    
    print(f"Exported to database with run_id: {run_id}")
    return run_id


def list_backtests():
    """List all backtests in the database."""
    db = DBManager()
    backtests = db.get_backtest_names()
    
    if not backtests:
        print("\nNo backtests found in database.")
        return
    
    print("\nAvailable Backtests:")
    print(f"{'ID':<10} {'Name':<30} {'Date':<20}")
    print("-" * 60)
    
    for backtest in backtests:
        date_str = backtest['date_inserted'].strftime("%Y-%m-%d %H:%M") if isinstance(backtest['date_inserted'], datetime) else str(backtest['date_inserted'])
        print(f"{backtest['run_id']:<10} {backtest['name']:<30} {date_str:<20}")


def compare_backtests(run_ids):
    """Compare multiple backtests by their run IDs."""
    if not run_ids:
        print("No run IDs provided for comparison.")
        return
    
    db = DBManager()
    comparison = db.compare_backtests(run_ids)
    
    if "error" in comparison:
        print(f"Error: {comparison['error']}")
        return
    
    backtests = comparison.get("backtests", [])
    
    if not backtests:
        print("No matching backtests found for comparison.")
        return
    
    print("\nBacktest Comparison:")
    print(f"{'Name':<30} {'Total Return':<15} {'Sharpe':<10} {'Max DD':<10} {'Beta':<8}")
    print("-" * 75)
    
    for bt in backtests:
        total_return = f"{bt.get('total_return', 0) * 100:.2f}%" if bt.get('total_return') is not None else "N/A"
        sharpe = f"{bt.get('sharpe_ratio', 0):.2f}" if bt.get('sharpe_ratio') is not None else "N/A"
        max_dd = f"{bt.get('max_drawdown', 0) * 100:.2f}%" if bt.get('max_drawdown') is not None else "N/A"
        beta = f"{bt.get('beta', 0):.2f}" if bt.get('beta') is not None else "N/A"
        
        print(f"{bt.get('name', 'Unknown'):<30} {total_return:<15} {sharpe:<10} {max_dd:<10} {beta:<8}")
    
    # Plot equity curves if available
    equity_curves = comparison.get("equity_curves", {})
    if equity_curves:
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(12, 6))
            for run_id, curve in equity_curves.items():
                # Find the name for this run_id
                name = "Unknown"
                for bt in backtests:
                    if str(bt.get('run_id')) == str(run_id):
                        name = bt.get('name', 'Unknown')
                        break
                
                # Normalize the curve to start at 100
                normalized = 100 * (curve / curve.iloc[0])
                plt.plot(normalized, label=f"{name} (ID: {run_id})")
            
            plt.title("Equity Curve Comparison (Normalized to 100)")
            plt.xlabel("Date")
            plt.ylabel("Value")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.show()
        except ImportError:
            print("Matplotlib is required for plotting equity curves.")
        except Exception as e:
            print(f"Error plotting equity curves: {e}")


def get_backtest_details(run_id):
    """Show detailed information about a specific backtest."""
    db = DBManager()
    summary = db.get_backtest_summary(run_id)
    
    if not summary:
        print(f"No backtest found with run_id: {run_id}")
        return
    
    print(f"\nBacktest Details for ID: {run_id}")
    print(f"Name: {summary.get('name', 'N/A')}")
    print(f"Description: {summary.get('description', 'N/A')}")
    print(f"Created: {summary.get('date_inserted', 'N/A')}")
    print(f"Date Range: {summary.get('start_date', 'N/A')} to {summary.get('end_date', 'N/A')}")
    
    print("\nPerformance Metrics:")
    metrics_to_display = [
        ("total_return", "Total Return", lambda x: f"{x * 100:.2f}%"),
        ("annualized_return", "Annualized Return", lambda x: f"{x * 100:.2f}%"),
        ("sharpe_ratio", "Sharpe Ratio", lambda x: f"{x:.2f}"),
        ("sortino_ratio", "Sortino Ratio", lambda x: f"{x:.2f}"),
        ("max_drawdown", "Max Drawdown", lambda x: f"{x * 100:.2f}%"),
        ("volatility", "Volatility", lambda x: f"{x * 100:.2f}%"),
        ("beta", "Beta", lambda x: f"{x:.2f}"),
        ("correlation", "Correlation", lambda x: f"{x:.2f}"),
        ("calmar_ratio", "Calmar Ratio", lambda x: f"{x:.2f}"),
        ("var_95", "Value at Risk (95%)", lambda x: f"{x * 100:.2f}%"),
    ]
    
    for key, label, formatter in metrics_to_display:
        if key in summary and summary[key] is not None:
            print(f"  {label}: {formatter(summary[key])}")
    
    print(f"\nData Points: {summary.get('equity_points', 0)}")
    print(f"Positions: {summary.get('position_count', 0)}")
    print(f"Symbols with PnL: {summary.get('symbol_pnl_count', 0)}")
    
    # Show hyperparameters if available
    if "hyperparameters" in summary and summary["hyperparameters"]:
        print("\nHyperparameters:")
        for key, value in summary["hyperparameters"].items():
            print(f"  {key}: {value}")
    
    # Load and show equity curve if available
    equity_curve = db.get_equity_curve(run_id)
    if equity_curve is not None:
        try:
            import matplotlib.pyplot as plt
            
            # Plot equity curve
            plt.figure(figsize=(12, 6))
            plt.subplot(2, 1, 1)
            plt.plot(equity_curve)
            plt.title("Equity Curve")
            plt.grid(True, alpha=0.3)
            
            # Plot drawdown
            plt.subplot(2, 1, 2)
            drawdown = (equity_curve / equity_curve.cummax() - 1) * 100  # In percentage
            plt.fill_between(drawdown.index, 0, drawdown, color='red', alpha=0.3)
            plt.title("Drawdown (%)")
            plt.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.show()
        except ImportError:
            print("Matplotlib is required for plotting equity curves.")
        except Exception as e:
            print(f"Error plotting equity curve: {e}")


def find_best_backtests(metric="sharpe_ratio", limit=5):
    """Find the best performing backtests based on a metric."""
    db = DBManager()
    best = db.find_best_backtest(metric=metric, limit=limit)
    
    if not best:
        print(f"No backtests found with valid {metric} values.")
        return
    
    print(f"\nTop {limit} Backtests by {metric}:")
    print(f"{'Rank':<5} {'Name':<30} {metric.replace('_', ' ').title():<15} {'Return':<15} {'Created':<20}")
    print("-" * 85)
    
    for i, bt in enumerate(best):
        metric_value = bt.get(metric)
        metric_str = f"{metric_value:.4f}" if metric_value is not None else "N/A"
        
        total_return = bt.get('total_return')
        return_str = f"{total_return * 100:.2f}%" if total_return is not None else "N/A"
        
        date_str = bt['date_inserted'].strftime("%Y-%m-%d %H:%M") if isinstance(bt['date_inserted'], datetime) else str(bt['date_inserted'])
        
        print(f"{i+1:<5} {bt.get('name', 'Unknown'):<30} {metric_str:<15} {return_str:<15} {date_str:<20}")


def search_backtests(query, field="name"):
    """Search for backtests matching a query."""
    db = DBManager()
    results = db.search_backtests(query, field=field)
    
    if not results:
        print(f"No backtests found matching {field}='{query}'")
        return
    
    print(f"\nBacktests matching {field}='{query}':")
    print(f"{'ID':<10} {'Name':<30} {'Description':<40} {'Created':<20}")
    print("-" * 100)
    
    for result in results:
        desc = result.get('description', '')
        # Truncate description if too long
        if desc and len(desc) > 40:
            desc = desc[:37] + "..."
        
        date_str = result['date_inserted'].strftime("%Y-%m-%d %H:%M") if isinstance(result['date_inserted'], datetime) else str(result['date_inserted'])
        
        print(f"{result['run_id']:<10} {result.get('name', 'Unknown'):<30} {desc:<40} {date_str:<20}")


def delete_backtest(run_id):
    """Delete a backtest by its run ID."""
    db = DBManager()
    
    # First get the backtest name
    summary = db.get_backtest_summary(run_id)
    if not summary:
        print(f"No backtest found with run_id: {run_id}")
        return
    
    name = summary.get('name', 'Unknown')
    
    # Confirm deletion
    confirm = input(f"Are you sure you want to delete backtest '{name}' (ID: {run_id})? (y/n): ")
    if confirm.lower() != 'y':
        print("Deletion cancelled.")
        return
    
    # Delete the backtest
    success = db.delete_by_run_id(run_id)
    
    if success:
        print(f"Successfully deleted backtest '{name}' (ID: {run_id})")
    else:
        print(f"Failed to delete backtest '{name}' (ID: {run_id})")


def main():
    """Main function to run the example script."""
    print("AlgoSystem Database Management Example")
    print("=====================================")
    
    db = DBManager()
    
    # Ensure database tables exist
    db.create_backtest_table()
    
    # First check if we have any backtests
    backtests = db.get_backtest_names()
    
    if not backtests:
        print("\nNo backtests found in database. Creating some example backtests...")
        
        # Create a few sample backtests with different parameters
        run_id1 = run_backtest_and_export(
            "Momentum Strategy", 
            "A momentum-based strategy with daily rebalancing"
        )
        
        # Adjust parameters for the second backtest to get different results
        np.random.seed(44)  # Different seed for different results
        run_id2 = run_backtest_and_export(
            "Mean Reversion Strategy", 
            "A mean-reversion strategy that trades counter to momentum"
        )
        
        # Third backtest with yet another seed
        np.random.seed(45)
        run_id3 = run_backtest_and_export(
            "Low Volatility Strategy", 
            "A strategy targeting low volatility stocks"
        )
        
        run_ids = [run_id1, run_id2, run_id3]
    else:
        print("\nFound existing backtests in database.")
        run_ids = [b['run_id'] for b in backtests[:3]]  # Use first 3 for comparison
    
    # List all backtests
    list_backtests()
    
    # Compare backtests
    if len(run_ids) >= 2:
        compare_backtests(run_ids[:2])  # Compare first two
    
    # Find best backtests by Sharpe ratio
    find_best_backtests(metric="sharpe_ratio", limit=3)
    
    # Show details of the first backtest
    if run_ids:
        get_backtest_details(run_ids[0])
    
    # Clean up connections
    db.close()


if __name__ == "__main__":
    main()