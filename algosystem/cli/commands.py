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
@click.option('--host', type=str, default='127.0.0.1',
              help='Host to run the dashboard editor server on (default: 127.0.0.1)')
@click.option('--port', type=int, default=5000,
              help='Port to run the dashboard editor server on (default: 5000)')
@click.option('--debug', is_flag=True, default=False,
              help='Run the server in debug mode')
def launch(config, data_dir, host, port, debug):
    """Launch the AlgoSystem Dashboard UI."""
    # Set environment variables for config and data if provided
    if config:
        os.environ['ALGO_DASHBOARD_CONFIG'] = os.path.abspath(config)
    
    if data_dir:
        os.environ['ALGO_DASHBOARD_DATA_DIR'] = os.path.abspath(data_dir)
    
    # Launch the dashboard web editor
    from algosystem.backtesting.dashboard.web_app.app import start_dashboard_editor
    click.echo(f"Starting AlgoSystem Dashboard Editor on http://{host}:{port}/")
    click.echo("Press Ctrl+C to stop the server.")
    start_dashboard_editor(host=host, port=port, debug=debug)

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-dir', '-o', type=click.Path(), default="./dashboard_output",
              help='Directory to save the dashboard files (default: ./dashboard_output)')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to a custom dashboard configuration file')
@click.option('--benchmark', '-b', type=click.Path(exists=True),
              help='Path to a CSV file with benchmark data')
@click.option('--open-browser', is_flag=True, default=False,
              help='Open the dashboard in a browser after rendering')
def render(input_file, output_dir, config, benchmark, open_browser):
    """
    Render a dashboard from a CSV file with strategy data.
    
    INPUT_FILE: Path to a CSV file with strategy data
    """
    import json
    import webbrowser
    from algosystem.backtesting.engine import Engine
    from algosystem.backtesting.dashboard.dashboard_generator import generate_dashboard
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load the dashboard configuration
    config_path = config
    if not config_path:
        # Use default config path
        from algosystem.backtesting.dashboard.utils.default_config import DEFAULT_CONFIG_PATH
        config_path = DEFAULT_CONFIG_PATH
    
    try:
        # Load the CSV data
        click.echo(f"Loading data from {input_file}...")
        data = pd.read_csv(input_file, index_col=0, parse_dates=True)
        click.echo(f"Loaded data with shape: {data.shape}")
        
        # Load benchmark data if provided
        benchmark_data = None
        if benchmark:
            click.echo(f"Loading benchmark data from {benchmark}...")
            benchmark_data = pd.read_csv(benchmark, index_col=0, parse_dates=True)
            if isinstance(benchmark_data, pd.DataFrame) and benchmark_data.shape[1] > 1:
                benchmark_data = benchmark_data.iloc[:, 0]  # Use first column
            click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")
        
        # Create a backtest engine to process the data
        click.echo("Running backtest...")
        if isinstance(data, pd.DataFrame) and data.shape[1] > 1:
            # Use the first column as price data
            price_data = data.iloc[:, 0]
        else:
            price_data = data
        
        # Initialize and run the engine
        engine = Engine(data=price_data, benchmark=benchmark_data)
        results = engine.run()
        click.echo("Backtest completed successfully")
        
        # Generate dashboard
        click.echo("Generating dashboard...")
        dashboard_path = generate_dashboard(
            engine=engine,
            output_dir=output_dir,
            open_browser=open_browser,
            config_path=config_path
        )
        
        click.echo(f"Dashboard generated successfully at: {dashboard_path}")
        
        # Provide instructions for viewing
        if not open_browser:
            click.echo("To view the dashboard, open this file in a web browser:")
            click.echo(f"  {os.path.abspath(dashboard_path)}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('output_dir', type=click.Path())
def create_config(output_dir):
    """
    Create a sample dashboard configuration file.
    
    OUTPUT_DIR: Directory to save the sample configuration
    """
    # Load the default configuration
    from algosystem.backtesting.dashboard.utils.default_config import DEFAULT_CONFIG_PATH
    import json
    
    with open(DEFAULT_CONFIG_PATH, 'r') as f:
        sample_config = json.load(f)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Save configuration file
    output_path = os.path.join(output_dir, 'sample_dashboard_config.json')
    with open(output_path, 'w') as f:
        json.dump(sample_config, f, indent=4)
    
    click.echo(f"Sample configuration saved to: {output_path}")

if __name__ == '__main__':
    cli()