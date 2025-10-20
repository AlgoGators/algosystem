# dashboard_utils.py

import pandas as pd
import os
from datetime import datetime
import argparse
import sys

# Import your existing modules
from your_module import BacktestEngine  # Replace with your actual import
import metrics  # Your metrics module


def export_backtest_to_csv(results, output_dir="backtest_exports", prefix="backtest"):
    """
    Export backtest results including metrics and graph data to CSV files.
    
    Parameters
    ----------
    results : dict
        Dictionary containing backtest results from engine.run()
    output_dir : str, default="backtest_exports"
        Directory to save the CSV files
    prefix : str, default="backtest"
        Prefix for the exported files
    
    Returns
    -------
    dict
        Dictionary containing paths to all exported files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    exported_files = {}
    
    # 1. Export Summary Metrics
    summary_data = {
        'Metric': ['Initial Capital', 'Final Capital', 'Total Return', 
                   'Start Date', 'End Date'],
        'Value': [
            results.get('initial_capital', 'N/A'),
            results.get('final_capital', 'N/A'),
            f"{results.get('returns', 0) * 100:.2f}%",
            results.get('start_date', 'N/A'),
            results.get('end_date', 'N/A')
        ]
    }
    
    # Add all calculated metrics
    metrics_data = results.get('metrics', {})
    for key, value in metrics_data.items():
        if not key.endswith('_error'):
            metric_name = key.replace('_', ' ').title()
            if isinstance(value, (int, float)):
                if 'return' in key.lower() or 'ratio' in key.lower():
                    formatted_value = f"{value * 100:.2f}%" if value < 1 else f"{value:.2f}"
                else:
                    formatted_value = f"{value:.4f}"
            else:
                formatted_value = str(value)
            
            summary_data['Metric'].append(metric_name)
            summary_data['Value'].append(formatted_value)
    
    summary_df = pd.DataFrame(summary_data)
    summary_file = os.path.join(output_dir, f"{prefix}_summary_{timestamp}.csv")
    summary_df.to_csv(summary_file, index=False)
    exported_files['summary'] = summary_file
    
    # 2. Export Time Series Data for Graphs
    plots_data = results.get('plots', {})
    
    time_series_dfs = {}
    for key, series_data in plots_data.items():
        if isinstance(series_data, pd.Series):
            col_name = key.replace('_', ' ').title()
            time_series_dfs[col_name] = series_data
    
    if time_series_dfs:
        combined_ts = pd.DataFrame(time_series_dfs)
        combined_ts.index.name = 'Date'
        
        timeseries_file = os.path.join(output_dir, f"{prefix}_timeseries_{timestamp}.csv")
        combined_ts.to_csv(timeseries_file)
        exported_files['timeseries'] = timeseries_file
        
        # Export specialized chart data
        _export_chart_specific_data(combined_ts, output_dir, prefix, timestamp, exported_files)
    
    # 3. Export Raw Equity Series
    if 'equity' in results and isinstance(results['equity'], pd.Series):
        equity_series = pd.DataFrame({
            'Date': results['equity'].index,
            'Portfolio Value': results['equity'].values
        })
        raw_equity_file = os.path.join(output_dir, f"{prefix}_portfolio_value_{timestamp}.csv")
        equity_series.to_csv(raw_equity_file, index=False)
        exported_files['portfolio_value'] = raw_equity_file
    
    # 4. Create metadata file
    _create_metadata_file(results, exported_files, output_dir, prefix, timestamp)
    
    return exported_files


def _export_chart_specific_data(combined_ts, output_dir, prefix, timestamp, exported_files):
    """Helper function to export chart-specific data"""
    # Equity Curve Data
    equity_data = pd.DataFrame()
    for col in ['Equity Curve', 'Benchmark Equity Curve', 'Relative Performance']:
        if col in combined_ts.columns:
            equity_data[col] = combined_ts[col]
    
    if not equity_data.empty:
        equity_file = os.path.join(output_dir, f"{prefix}_equity_curve_{timestamp}.csv")
        equity_data.to_csv(equity_file)
        exported_files['equity_curve'] = equity_file
    
    # Drawdown Data
    drawdown_data = pd.DataFrame()
    for col in ['Drawdown Series', 'Benchmark Drawdown Series', 'Rolling Drawdown Duration']:
        if col in combined_ts.columns:
            drawdown_data[col] = combined_ts[col]
    
    if not drawdown_data.empty:
        drawdown_file = os.path.join(output_dir, f"{prefix}_drawdown_{timestamp}.csv")
        drawdown_data.to_csv(drawdown_file)
        exported_files['drawdown'] = drawdown_file
    
    # Risk Metrics Over Time
    risk_data = pd.DataFrame()
    risk_cols = ['Rolling Sharpe', 'Rolling Sortino', 'Rolling Volatility', 
                 'Rolling Skew', 'Rolling Var']
    for col in risk_cols:
        if col in combined_ts.columns:
            risk_data[col] = combined_ts[col]
    
    if not risk_data.empty:
        risk_file = os.path.join(output_dir, f"{prefix}_risk_metrics_{timestamp}.csv")
        risk_data.to_csv(risk_file)
        exported_files['risk_metrics'] = risk_file


def _create_metadata_file(results, exported_files, output_dir, prefix, timestamp):
    """Helper function to create metadata file"""
    metadata = {
        'Export Timestamp': timestamp,
        'Files Exported': list(exported_files.keys()),
        'Start Date': results.get('start_date', 'N/A'),
        'End Date': results.get('end_date', 'N/A'),
        'Initial Capital': results.get('initial_capital', 'N/A'),
        'Final Capital': results.get('final_capital', 'N/A'),
        'Total Return': f"{results.get('returns', 0) * 100:.2f}%"
    }
    
    metadata_file = os.path.join(output_dir, f"{prefix}_metadata_{timestamp}.txt")
    with open(metadata_file, 'w') as f:
        for key, value in metadata.items():
            if key == 'Files Exported':
                f.write(f"{key}:\n")
                for file in value:
                    f.write(f"  - {file}\n")
            else:
                f.write(f"{key}: {value}\n")
    exported_files['metadata'] = metadata_file


def create_dashboard(engine, output_dir=None, show=True):
    """
    Create an interactive dashboard or export to CSV based on parameters.
    
    Parameters
    ----------
    engine : BacktestEngine
        The backtest engine instance
    output_dir : str, optional
        If provided, export to CSV instead of showing dashboard
    show : bool, default=True
        Whether to display the dashboard (when not exporting)
    
    Returns
    -------
    results : dict
        The backtest results
    """
    # Run the backtest
    results = engine.run()
    
    if output_dir:
        # Export mode
        print("Exporting backtest results to CSV...")
        prefix = getattr(engine, 'strategy_name', 'backtest')
        exported_files = export_backtest_to_csv(results, output_dir, prefix)
        
        print(f"\n✅ Export completed successfully!")
        print(f"📁 Files exported to: {output_dir}")
        print("\n📄 Files created:")
        for file_type, path in exported_files.items():
            print(f"   • {file_type}: {os.path.basename(path)}")
        
        return results, exported_files
    else:
        # Dashboard mode (your existing dashboard code would go here)
        if show:
            # Your existing dashboard visualization code
            print("Launching interactive dashboard...")
            # create_interactive_dashboard(results)  # Your existing function
        
        return results


def main():
    """
    Main entry point for the dashboard utility.
    Can be run from command line with arguments.
    """
    parser = argparse.ArgumentParser(
        description='Backtest Dashboard and Export Utility',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run interactive dashboard
  python dashboard_utils.py --strategy momentum --data prices.csv
  
  # Export to CSV instead of showing dashboard
  python dashboard_utils.py --strategy momentum --data prices.csv --export exports/
  
  # Export with custom prefix
  python dashboard_utils.py --strategy momentum --data prices.csv --export exports/ --prefix "momentum_2024"
        """
    )
    
    # Required arguments
    parser.add_argument('--strategy', '-s', required=True,
                       help='Strategy name or path to strategy file')
    parser.add_argument('--data', '-d', required=True,
                       help='Path to price data CSV file')
    
    # Optional arguments
    parser.add_argument('--benchmark', '-b', default=None,
                       help='Path to benchmark data CSV file')
    parser.add_argument('--capital', '-c', type=float, default=10000,
                       help='Initial capital (default: 10000)')
    parser.add_argument('--start-date', default=None,
                       help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end-date', default=None,
                       help='End date for backtest (YYYY-MM-DD)')
    
    # Export arguments
    parser.add_argument('--export', '-e', dest='export_dir', default=None,
                       help='Export results to CSV in specified directory instead of showing dashboard')
    parser.add_argument('--prefix', '-p', default=None,
                       help='Prefix for exported files (default: strategy name)')
    
    # Dashboard arguments
    parser.add_argument('--no-show', action='store_true',
                       help='Run backtest without showing dashboard')
    
    args = parser.parse_args()
    
    try:
        # Load data
        print(f"Loading data from {args.data}...")
        price_data = pd.read_csv(args.data, index_col=0, parse_dates=True)
        
        benchmark_data = None
        if args.benchmark:
            print(f"Loading benchmark from {args.benchmark}...")
            benchmark_data = pd.read_csv(args.benchmark, index_col=0, parse_dates=True)
        
        # Initialize engine (adjust based on your actual engine initialization)
        engine = BacktestEngine(
            price_series=price_data,
            benchmark_series=benchmark_data,
            initial_capital=args.capital,
            start_date=args.start_date,
            end_date=args.end_date,
            strategy_name=args.strategy
        )
        
        # Set prefix for exports
        if args.prefix:
            prefix = args.prefix
        else:
            prefix = args.strategy
        
        # Run dashboard or export
        if args.export_dir:
            # Export mode
            results, exported_files = create_dashboard(
                engine, 
                output_dir=args.export_dir,
                show=False
            )
            
            # Optionally save the export paths to a JSON for programmatic access
            import json
            paths_file = os.path.join(args.export_dir, f"{prefix}_paths.json")
            with open(paths_file, 'w') as f:
                json.dump(exported_files, f, indent=2)
            print(f"\n📋 Export paths saved to: {paths_file}")
            
        else:
            # Dashboard mode
            results = create_dashboard(
                engine,
                output_dir=None,
                show=not args.no_show
            )
            
            if not args.no_show:
                print("\n✅ Dashboard launched successfully!")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ Error: File not found - {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())