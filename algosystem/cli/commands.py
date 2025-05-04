import os
import sys
import click
import pandas as pd
from pathlib import Path

# Add parent directory to path to allow direct script execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@click.group()
def cli():
    """AlgoSystem Dashboard command-line interface."""
    pass

@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), 
              help='Path to a dashboard configuration file to load')
@click.option('--data-dir', '-d', type=click.Path(exists=True),
              help='Directory containing data files to preload')
def launch(config, data_dir):
    """Launch the AlgoSystem Dashboard UI."""
    from algosystem.dashboard.dashboard_module import launch_dashboard
    
    # Set environment variables for config and data if provided
    if config:
        os.environ['ALGO_DASHBOARD_CONFIG'] = os.path.abspath(config)
    
    if data_dir:
        os.environ['ALGO_DASHBOARD_DATA_DIR'] = os.path.abspath(data_dir)
    
    # Launch the dashboard
    launch_dashboard()

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.argument('output_file', type=click.Path())
def render(input_file, output_file,):
    """
    Render a dashboard from a configuration file and CSV data.
    
    INPUT_FILE: Path to a CSV file with strategy data
    OUTPUT_FILE: Path to save the dashboard image (PNG or PDF)
    """
    import json
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    from algosystem.backtesting.engine import Engine
    
    # Load the dashboard configuration
    with open('algosystem/utils/graph_config.json', 'r') as f:
        dashboard_config = json.load(f)
    
    # Load the CSV data
    try:
        data = pd.read_csv(input_file, index_col=0, parse_dates=True)
        print(f"Loaded data with shape: {data.shape}")
    except Exception as e:
        print(f"Error loading CSV file: {e}")
        sys.exit(1)
    
    # Create a backtest engine to process the data
    try:
        if isinstance(data, pd.DataFrame) and data.shape[1] > 1:
            # Use the first column as price data for simplicity
            price_data = data.iloc[:, 0]
        else:
            price_data = data
        
        engine = Engine(data=price_data)
        results = engine.run()
        print("Backtest completed successfully")
    except Exception as e:
        print(f"Error running backtest: {e}")
        sys.exit(1)
    
    # Determine the dashboard grid size
    if 'dashboard' in dashboard_config and 'max_cols' in dashboard_config['dashboard']:
        max_cols = dashboard_config['dashboard']['max_cols']
    else:
        max_cols = 2
    
    # Count plots to determine grid size
    if 'dashboard' in dashboard_config and 'plots' in dashboard_config['dashboard']:
        plots = dashboard_config['dashboard']['plots']
        num_plots = len(plots)
    else:
        print("No plots defined in configuration file")
        sys.exit(1)
    
    # Calculate grid dimensions
    num_rows = (num_plots + max_cols - 1) // max_cols
    
    # Create matplotlib figure for the dashboard
    fig = plt.figure(figsize=(max_cols * 8, num_rows * 6))
    gs = GridSpec(num_rows, max_cols, figure=fig)
    
    # Create a plot for each defined plot in the configuration
    plot_positions = {}
    for i, plot_config in enumerate(plots):
        # Get plot position from config or calculate it
        if 'position' in plot_config:
            row, col = plot_config['position']['row'], plot_config['position']['col']
        else:
            row, col = i // max_cols, i % max_cols
        
        # Store position to avoid duplicates
        pos_key = f"{row},{col}"
        if pos_key in plot_positions:
            # Position already occupied, find next available spot
            for r in range(num_rows):
                for c in range(max_cols):
                    test_key = f"{r},{c}"
                    if test_key not in plot_positions:
                        row, col = r, c
                        pos_key = test_key
                        break
        
        plot_positions[pos_key] = True
        
        # Create the plot based on its type
        ax = fig.add_subplot(gs[row, col])
        
        # Get plot type and title
        plot_type = plot_config.get('type', 'Unknown')
        title = plot_config.get('title', plot_type)
        
        # Create the appropriate plot based on type
        if plot_type == 'Equity Curve':
            equity = results['equity']
            ax.plot(equity, label='Strategy')
            ax.set_title(title)
            ax.set_xlabel('Date')
            ax.set_ylabel('Equity ($)')
            ax.grid(alpha=0.3)
        
        elif plot_type == 'Drawdown Chart':
            # Calculate drawdown
            equity = results['equity']
            returns = equity.pct_change().dropna()
            cum_returns = (1 + returns).cumprod()
            running_max = cum_returns.cummax()
            drawdown = (cum_returns / running_max) - 1
            
            ax.fill_between(drawdown.index, 0, drawdown, color='red', alpha=0.3)
            ax.plot(drawdown, color='red', linewidth=1)
            ax.set_title(title)
            ax.set_xlabel('Date')
            ax.set_ylabel('Drawdown (%)')
            ax.grid(alpha=0.3)
        
        elif plot_type == 'Monthly Returns Heatmap':
            equity = results['equity']
            monthly_returns = equity.resample('M').last().pct_change().dropna()
            returns_matrix = monthly_returns.groupby(
                [monthly_returns.index.year, monthly_returns.index.month]).first().unstack()
            
            # Create heatmap (simplified version)
            cax = ax.imshow(returns_matrix, cmap='RdYlGn')
            plt.colorbar(cax, ax=ax, label='Monthly Return')
            ax.set_title(title)
            ax.set_xlabel('Month')
            ax.set_ylabel('Year')
        
        elif plot_type == 'Rolling Sharpe Ratio':
            equity = results['equity']
            returns = equity.pct_change().dropna()
            window = plot_config.get('config', {}).get('window_size', 252)
            
            # Calculate rolling Sharpe ratio
            rolling_return = returns.rolling(window).mean() * 252
            rolling_vol = returns.rolling(window).std() * (252 ** 0.5)
            rolling_sharpe = rolling_return / rolling_vol
            
            ax.plot(rolling_sharpe, linewidth=2)
            ax.axhline(y=1, color='green', linestyle='--', alpha=0.7)
            ax.axhline(y=0, color='red', linestyle='--', alpha=0.7)
            
            ax.set_title(f"{title} ({window//252}-Year Window)")
            ax.set_xlabel('Date')
            ax.set_ylabel('Sharpe Ratio')
            ax.grid(alpha=0.3)
        
        else:
            # Generic plot for unrecognized types
            ax.text(0.5, 0.5, f"Plot Type: {plot_type}", ha='center', va='center')
            ax.set_title(title)
            ax.axis('off')
    
    # Add overall title
    fig.suptitle("AlgoSystem Dashboard", fontsize=16)
    
    # Adjust layout and save
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    
    try:
        output_ext = os.path.splitext(output_file)[1].lower()
        if output_ext == '.pdf':
            fig.savefig(output_file, format='pdf')
        else:
            # Default to PNG
            fig.savefig(output_file, format='png', dpi=300)
        
        print(f"Dashboard saved to: {output_file}")
    except Exception as e:
        print(f"Error saving dashboard: {e}")
        sys.exit(1)

@cli.command()
@click.argument('output_dir', type=click.Path())
def create_config(output_dir):
    """
    Create a sample dashboard configuration file.
    
    OUTPUT_DIR: Directory to save the sample configuration
    """
    import json
    
    # Create a sample configuration
    sample_config = {
        'dashboard': {
            'max_cols': 2,
            'plots': [
                {
                    'id': 1,
                    'type': 'Equity Curve',
                    'title': 'Strategy Equity',
                    'position': {'row': 0, 'col': 0},
                    'config': {
                        'line_color': '#0000FF',
                        'line_width': 2,
                        'grid': {'x': True, 'y': True}
                    }
                },
                {
                    'id': 2,
                    'type': 'Drawdown Chart',
                    'title': 'Drawdown Analysis',
                    'position': {'row': 0, 'col': 1},
                    'config': {
                        'line_color': '#FF0000',
                        'line_width': 1,
                        'grid': {'x': True, 'y': True}
                    }
                },
                {
                    'id': 3,
                    'type': 'Monthly Returns Heatmap',
                    'title': 'Monthly Performance',
                    'position': {'row': 1, 'col': 0},
                    'config': {}
                },
                {
                    'id': 4,
                    'type': 'Rolling Sharpe Ratio',
                    'title': 'Rolling Sharpe',
                    'position': {'row': 1, 'col': 1},
                    'config': {
                        'window_size': 252,
                        'line_color': '#00AA00',
                        'line_width': 2,
                        'grid': {'x': True, 'y': True}
                    }
                }
            ]
        },
        'data_sources': []
    }
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save configuration file
    output_path = os.path.join(output_dir, 'sample_dashboard_config.json')
    with open(output_path, 'w') as f:
        json.dump(sample_config, f, indent=4)
    
    print(f"Sample configuration saved to: {output_path}")

if __name__ == '__main__':
    cli()