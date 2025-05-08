import os
import sys
import click
import json
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
@click.option('--save-config', type=click.Path(), 
              help='Path to save the edited configuration file (creates a new file)')
def launch(config, data_dir, host, port, debug, save_config):
    """Launch the AlgoSystem Dashboard UI."""
    # Set environment variables for config and data if provided
    if config:
        os.environ['ALGO_DASHBOARD_CONFIG'] = os.path.abspath(config)
    
    if save_config:
        os.environ['ALGO_DASHBOARD_SAVE_CONFIG'] = os.path.abspath(save_config)
    
    if data_dir:
        os.environ['ALGO_DASHBOARD_DATA_DIR'] = os.path.abspath(data_dir)
    
    # Launch the dashboard web editor
    try:
        from algosystem.backtesting.dashboard.web_app.app import start_dashboard_editor
        click.echo(f"Starting AlgoSystem Dashboard Editor on http://{host}:{port}/")
        
        if save_config:
            click.echo(f"Configuration will be saved to: {save_config}")
        
        click.echo("Press Ctrl+C to stop the server.")
        start_dashboard_editor(host=host, port=port, debug=debug)
    except ImportError as e:
        click.echo(f"Error: {e}")
        click.echo("Make sure Flask is installed: pip install flask")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error starting dashboard editor: {e}")
        sys.exit(1)

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
@click.option('--use-default-config', is_flag=True, default=False,
              help='Use default configuration instead of custom config (overrides --config)')
def render(input_file, output_dir, config, benchmark, open_browser, use_default_config):
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
    config_path = None
    if use_default_config:
        click.echo("Using default dashboard configuration")
        from algosystem.backtesting.dashboard.utils.default_config import DEFAULT_CONFIG_PATH
        config_path = DEFAULT_CONFIG_PATH
    elif config:
        click.echo(f"Using custom configuration from: {config}")
        config_path = config
    else:
        # Use default config path
        click.echo("No configuration specified, using default configuration")
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
        click.echo(f"Generating dashboard using configuration from: {config_path}")
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
@click.argument('output_path', type=click.Path())
@click.option('--based-on', '-b', type=click.Path(exists=True),
              help='Path to an existing configuration file to use as a base')
def create_config(output_path, based_on):
    """
    Create a dashboard configuration file.
    
    OUTPUT_PATH: Path where the configuration file will be saved
    """
    # Load the base configuration
    if based_on:
        try:
            click.echo(f"Creating configuration based on: {based_on}")
            with open(based_on, 'r') as f:
                config = json.load(f)
        except Exception as e:
            click.echo(f"Error loading base configuration: {str(e)}", err=True)
            sys.exit(1)
    else:
        # Load the default configuration
        from algosystem.backtesting.dashboard.utils.default_config import DEFAULT_CONFIG_PATH
        click.echo("Creating configuration based on default template")
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Save configuration file
    try:
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=4)
        click.echo(f"Configuration saved to: {output_path}")
    except Exception as e:
        click.echo(f"Error saving configuration: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--output-file', '-o', type=click.Path(), default="./standalone_dashboard.html",
              help='Path to save the standalone dashboard HTML file (default: ./standalone_dashboard.html)')
@click.option('--benchmark', '-b', type=click.Path(exists=True),
              help='Path to a CSV file with benchmark data')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to a custom dashboard configuration file')
@click.option('--use-default-config', is_flag=True, default=False,
              help='Use default configuration instead of custom config (overrides --config)')
@click.option('--open-browser', is_flag=True, default=False,
              help='Open the dashboard in a browser after rendering')
def standalone(input_file, output_file, benchmark, config, use_default_config, open_browser):
    """
    Create a standalone HTML dashboard from a CSV file that can be viewed without a web server.
    
    INPUT_FILE: Path to a CSV file with strategy data
    """
    import webbrowser
    from algosystem.backtesting.engine import Engine
    from algosystem.backtesting.dashboard.dashboard_generator import generate_standalone_dashboard
    
    # Determine which configuration to use
    config_path = None
    if use_default_config:
        click.echo("Using default dashboard configuration")
        from algosystem.backtesting.dashboard.utils.default_config import DEFAULT_CONFIG_PATH
        config_path = DEFAULT_CONFIG_PATH
    elif config:
        click.echo(f"Using custom configuration from: {config}")
        config_path = config
    else:
        # First, check if there's a config in the user's home directory
        user_config = os.path.join(os.path.expanduser("~"), ".algosystem", "dashboard_config.json")
        if os.path.exists(user_config):
            click.echo(f"Using user configuration from: {user_config}")
            config_path = user_config
        else:
            # Fall back to default
            click.echo("No configuration specified, using default configuration")
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
        
        # Generate standalone dashboard
        click.echo(f"Generating standalone dashboard using configuration from: {config_path}")
        dashboard_path = generate_standalone_dashboard(
            engine=engine, 
            output_path=output_file,
            config_path=config_path
        )
        
        click.echo(f"Standalone dashboard generated successfully at: {dashboard_path}")
        
        # Open in browser if requested
        if open_browser:
            webbrowser.open('file://' + os.path.abspath(dashboard_path))
        else:
            click.echo("To view the dashboard, open this file in a web browser:")
            click.echo(f"  {os.path.abspath(dashboard_path)}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('config_file', type=click.Path(exists=True))
def show_config(config_file):
    """
    Display the contents of a configuration file in a readable format.
    
    CONFIG_FILE: Path to the configuration file to display
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        click.echo(f"Configuration file: {config_file}\n")
        
        # Display layout
        if 'layout' in config:
            click.echo("=== Layout ===")
            click.echo(f"Title: {config['layout'].get('title', 'N/A')}")
            click.echo(f"Max columns: {config['layout'].get('max_cols', 'N/A')}")
            click.echo("")
        
        # Display metrics
        if 'metrics' in config:
            click.echo("=== Metrics ===")
            for i, metric in enumerate(config['metrics']):
                click.echo(f"{i+1}. {metric.get('title', 'Untitled')} ({metric.get('id', 'no-id')})")
                click.echo(f"   Type: {metric.get('type', 'N/A')}")
                click.echo(f"   Position: Row {metric['position'].get('row', 'N/A')}, Column {metric['position'].get('col', 'N/A')}")
                click.echo("")
        
        # Display charts
        if 'charts' in config:
            click.echo("=== Charts ===")
            for i, chart in enumerate(config['charts']):
                click.echo(f"{i+1}. {chart.get('title', 'Untitled')} ({chart.get('id', 'no-id')})")
                click.echo(f"   Type: {chart.get('type', 'N/A')}")
                click.echo(f"   Data Key: {chart.get('data_key', 'N/A')}")
                click.echo(f"   Position: Row {chart['position'].get('row', 'N/A')}, Column {chart['position'].get('col', 'N/A')}")
                click.echo("")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)

@cli.command()
def list_configs():
    """
    List all available configuration files in the user's home directory.
    """
    config_dir = os.path.join(os.path.expanduser("~"), ".algosystem")
    
    if not os.path.exists(config_dir):
        click.echo("No configuration directory found. Use 'create_config' to create your first configuration.")
        return
    
    config_files = [f for f in os.listdir(config_dir) if f.endswith('.json')]
    
    if not config_files:
        click.echo("No configuration files found in the user directory.")
        return
    
    click.echo(f"Configuration files in {config_dir}:")
    for i, config_file in enumerate(config_files):
        full_path = os.path.join(config_dir, config_file)
        file_size = os.path.getsize(full_path) / 1024  # size in KB
        mod_time = os.path.getmtime(full_path)
        mod_time_str = pd.to_datetime(mod_time, unit='s').strftime('%Y-%m-%d %H:%M:%S')
        
        click.echo(f"{i+1}. {config_file} ({file_size:.1f} KB, modified: {mod_time_str})")

if __name__ == '__main__':
    cli()