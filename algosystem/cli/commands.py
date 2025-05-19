"""
Enhanced CLI with benchmark support for AlgoSystem.
This module extends the existing CLI to support benchmark aliases and automatic data downloading.
"""

import json
import os
import sys
import traceback
from datetime import datetime

import click
import numpy as np
import pandas as pd

# Add parent directory to path to allow direct script execution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import benchmark functionality
from algosystem.data.benchmark import (
    DEFAULT_BENCHMARK,
    fetch_benchmark_data,
    get_benchmark_info,
    get_benchmark_list,
)

# Define user config directory and file
USER_CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".algosystem")
USER_CONFIG_FILE = os.path.join(USER_CONFIG_DIR, "config.json")


def ensure_user_config_exists():
    """
    Ensure the user configuration file exists. If not, create it with default settings.
    If it exists but is invalid, reset it to default settings.

    Returns:
    --------
    str
        Path to the user configuration file
    """
    # Create .algosystem directory if it doesn't exist
    os.makedirs(USER_CONFIG_DIR, exist_ok=True)

    # Load default configuration
    from algosystem.backtesting.dashboard.utils.default_config import get_default_config

    default_config = get_default_config()

    # Check if user config exists
    if not os.path.exists(USER_CONFIG_FILE):
        click.echo(f"Creating new user configuration at: {USER_CONFIG_FILE}")
        with open(USER_CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)
        click.echo("User configuration initialized with default settings.")
        return USER_CONFIG_FILE

    # Validate existing config
    try:
        with open(USER_CONFIG_FILE, "r") as f:
            user_config = json.load(f)

        # Basic validation - check required sections
        required_sections = ["metrics", "charts", "layout"]
        config_valid = True

        for section in required_sections:
            if section not in user_config:
                config_valid = False
                break

        # Check that metrics and charts are lists
        if config_valid:
            if not isinstance(user_config.get("metrics"), list):
                config_valid = False
            if not isinstance(user_config.get("charts"), list):
                config_valid = False
            if not isinstance(user_config.get("layout"), dict):
                config_valid = False

        # Additional validation for required fields in metrics and charts
        if config_valid:
            for metric in user_config["metrics"]:
                if not all(
                    key in metric
                    for key in ["id", "type", "title", "value_key", "position"]
                ):
                    config_valid = False
                    break

            for chart in user_config["charts"]:
                if not all(
                    key in chart
                    for key in ["id", "type", "title", "data_key", "position"]
                ):
                    config_valid = False
                    break

        if config_valid:
            click.echo(f"Using existing user configuration: {USER_CONFIG_FILE}")
            return USER_CONFIG_FILE
        else:
            # Invalid config - reset to default
            click.echo(
                "Warning: User configuration file is invalid. Resetting to default settings."
            )
            # Backup the old config
            backup_file = f"{USER_CONFIG_FILE}.backup.{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
            os.rename(USER_CONFIG_FILE, backup_file)
            click.echo(f"Old configuration backed up to: {backup_file}")

            # Create new config with defaults
            with open(USER_CONFIG_FILE, "w") as f:
                json.dump(default_config, f, indent=4)
            click.echo("User configuration reset to default settings.")
            return USER_CONFIG_FILE

    except (json.JSONDecodeError, IOError) as e:
        # File exists but can't be read - reset to default
        click.echo(
            f"Warning: Cannot read user configuration file ({str(e)}). Resetting to default settings."
        )
        # Backup the old config
        backup_file = (
            f"{USER_CONFIG_FILE}.backup.{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
        )
        if os.path.exists(USER_CONFIG_FILE):
            os.rename(USER_CONFIG_FILE, backup_file)
            click.echo(f"Old configuration backed up to: {backup_file}")

        # Create new config with defaults
        with open(USER_CONFIG_FILE, "w") as f:
            json.dump(default_config, f, indent=4)
        click.echo("User configuration reset to default settings.")
        return USER_CONFIG_FILE


@click.group()
def cli():
    """AlgoSystem Dashboard command-line interface."""
    pass


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to a dashboard configuration file to load",
)
@click.option(
    "--data-dir",
    "-d",
    type=click.Path(exists=True),
    help="Directory containing data files to preload",
)
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Host to run the dashboard editor server on (default: 127.0.0.1)",
)
@click.option(
    "--port",
    type=int,
    default=5000,
    help="Port to run the dashboard editor server on (default: 5000)",
)
@click.option(
    "--debug", is_flag=True, default=False, help="Run the server in debug mode"
)
@click.option(
    "--save-config",
    type=click.Path(),
    help="Path to save the edited configuration file (creates a new file if it does not exist)",
)
@click.option(
    "--default",
    is_flag=True,
    default=False,
    help="Use the default configuration instead of user config",
)
def launch(config, data_dir, host, port, debug, save_config, default):
    """Launch the AlgoSystem Dashboard UI."""
    # Clear environment variables to start fresh
    if "ALGO_DASHBOARD_CONFIG" in os.environ:
        del os.environ["ALGO_DASHBOARD_CONFIG"]
    if "ALGO_DASHBOARD_SAVE_CONFIG" in os.environ:
        del os.environ["ALGO_DASHBOARD_SAVE_CONFIG"]

    # Determine which configuration to use
    if default:
        # Use library default config
        from algosystem.backtesting.dashboard.utils.default_config import (
            DEFAULT_CONFIG_PATH,
        )

        os.environ["ALGO_DASHBOARD_CONFIG"] = DEFAULT_CONFIG_PATH
        click.echo("Using library default configuration")
    elif config:
        # Use specified config file
        os.environ["ALGO_DASHBOARD_CONFIG"] = os.path.abspath(config)
        click.echo(f"Loading configuration from: {os.path.abspath(config)}")
    else:
        # Use or create user config
        user_config_path = ensure_user_config_exists()
        os.environ["ALGO_DASHBOARD_CONFIG"] = user_config_path
        click.echo(f"Using user configuration: {user_config_path}")

    # Set save location
    if save_config:
        # Ensure it's an absolute path
        save_config_path = os.path.abspath(save_config)
        os.environ["ALGO_DASHBOARD_SAVE_CONFIG"] = save_config_path
        click.echo(f"Configuration will be saved to: {save_config_path}")

        # Create directory for save_config if it doesn't exist
        os.makedirs(os.path.dirname(save_config_path), exist_ok=True)
    else:
        # If no save-config specified and using user config, save back to user config
        if not default and not config:
            os.environ["ALGO_DASHBOARD_SAVE_CONFIG"] = USER_CONFIG_FILE
            click.echo(
                f"Changes will be saved to user configuration: {USER_CONFIG_FILE}"
            )

    if data_dir:
        os.environ["ALGO_DASHBOARD_DATA_DIR"] = os.path.abspath(data_dir)

    # Launch the dashboard web editor
    try:
        from algosystem.backtesting.dashboard.web_app.app import start_dashboard_editor

        click.echo(f"Starting AlgoSystem Dashboard Editor on http://{host}:{port}/")
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
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./dashboard_output",
    help="Directory to save the dashboard files (default: ./dashboard_output)",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to a custom dashboard configuration file",
)
@click.option(
    "--benchmark",
    "-b",
    help="Benchmark to use. Can be a file path or an alias (e.g., 'sp500', 'nasdaq')",
)
@click.option(
    "--start-date",
    help="Start date for the backtest (YYYY-MM-DD). Default: first date in input data",
)
@click.option(
    "--end-date",
    help="End date for the backtest (YYYY-MM-DD). Default: last date in input data",
)
@click.option(
    "--open-browser",
    is_flag=True,
    default=False,
    help="Open the dashboard in a browser after rendering",
)
@click.option(
    "--default",
    is_flag=True,
    default=False,
    help="Use library default configuration (overrides --config)",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    default=False,
    help="Force refresh of benchmark data even if cached data exists",
)
def render(
    input_file,
    output_dir,
    config,
    benchmark,
    start_date,
    end_date,
    open_browser,
    default,
    force_refresh,
):
    """
    Render a dashboard from a CSV file with strategy data.

    INPUT_FILE: Path to a CSV file with strategy data
    """
    from algosystem.backtesting.dashboard.dashboard_generator import generate_dashboard
    from algosystem.backtesting.engine import Engine

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load the dashboard configuration
    config_path = None
    if default:
        click.echo("Using library default dashboard configuration")
        from algosystem.backtesting.dashboard.utils.default_config import (
            DEFAULT_CONFIG_PATH,
        )

        config_path = DEFAULT_CONFIG_PATH
    elif config:
        click.echo(f"Using custom configuration from: {config}")
        config_path = config
    else:
        # Use user config
        config_path = ensure_user_config_exists()
        click.echo(f"Using user configuration: {config_path}")

    try:
        # Load the CSV data
        click.echo(f"Loading data from {input_file}...")
        data = pd.read_csv(input_file, index_col=0, parse_dates=True)
        click.echo(f"Loaded data with shape: {data.shape}")

        # Handle date range filtering
        if start_date:
            start_date = pd.to_datetime(start_date)
            data = data[data.index >= start_date]

        if end_date:
            end_date = pd.to_datetime(end_date)
            data = data[data.index <= end_date]

        if start_date or end_date:
            click.echo(f"Filtered data to shape: {data.shape}")

        # Load benchmark data if provided
        benchmark_data = None
        if benchmark:
            # Check if it's a file path
            if os.path.exists(benchmark):
                click.echo(f"Loading benchmark data from file: {benchmark}...")
                benchmark_data = pd.read_csv(benchmark, index_col=0, parse_dates=True)
                if (
                    isinstance(benchmark_data, pd.DataFrame)
                    and benchmark_data.shape[1] > 1
                ):
                    benchmark_data = benchmark_data.iloc[:, 0]  # Use first column
                click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")
            else:
                # Try to load as an alias
                click.echo(f"Loading benchmark data for alias: {benchmark}...")
                try:
                    benchmark_data = fetch_benchmark_data(
                        benchmark,
                        start_date=data.index[0] if not start_date else start_date,
                        end_date=data.index[-1] if not end_date else end_date,
                        force_refresh=force_refresh,
                    )
                    click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")
                except ImportError:
                    click.echo(
                        "Warning: Could not import benchmark module. Make sure the 'yfinance' package is installed."
                    )
                    click.echo("Continuing without benchmark data...")
                except Exception as e:
                    click.echo(f"Warning: Error fetching benchmark data: {str(e)}")
                    click.echo("Continuing without benchmark data...")
        elif not benchmark:
            # If no benchmark specified, use S&P 500 by default
            try:
                click.echo("Loading default benchmark (S&P 500)...")
                benchmark_data = fetch_benchmark_data(
                    DEFAULT_BENCHMARK,
                    start_date=data.index[0] if not start_date else start_date,
                    end_date=data.index[-1] if not end_date else end_date,
                    force_refresh=force_refresh,
                )
                click.echo(
                    f"Loaded S&P 500 benchmark data with {len(benchmark_data)} rows"
                )
            except ImportError:
                click.echo(
                    "Warning: Could not import benchmark module. Make sure the 'yfinance' package is installed."
                )
                click.echo("Continuing without benchmark data...")
            except Exception as e:
                click.echo(f"Warning: Error fetching S&P 500 benchmark data: {str(e)}")
                click.echo("Continuing without benchmark data...")

        # Create a backtest engine to process the data
        click.echo("Running backtest...")
        if isinstance(data, pd.DataFrame) and data.shape[1] > 1:
            # Use the first column as price data
            price_data = data.iloc[:, 0]
        else:
            price_data = data

        # Initialize and run the engine
        engine = Engine(
            data=price_data,
            benchmark=benchmark_data,
            start_date=start_date,
            end_date=end_date,
        )
        results = engine.run()
        click.echo("Backtest completed successfully")

        # Generate dashboard
        click.echo(f"Generating dashboard using configuration from: {config_path}")
        dashboard_path = generate_dashboard(
            engine=engine,
            output_dir=output_dir,
            open_browser=open_browser,
            config_path=config_path,
        )

        click.echo(f"Dashboard generated successfully at: {dashboard_path}")

        # Provide instructions for viewing
        if not open_browser:
            click.echo("To view the dashboard, open this file in a web browser:")
            click.echo(f"  {os.path.abspath(dashboard_path)}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        # Print traceback for debugging
        click.echo(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("output_path", type=click.Path())
@click.option(
    "--based-on",
    "-b",
    type=click.Path(exists=True),
    help="Path to an existing configuration file to use as a base",
)
@click.option(
    "--default",
    is_flag=True,
    default=False,
    help="Create config based on library default configuration",
)
@click.option(
    "--user",
    is_flag=True,
    default=False,
    help="Create config based on user configuration",
)
def create_config(output_path, based_on, default, user):
    """
    Create a dashboard configuration file.

    OUTPUT_PATH: Path where the configuration file will be saved
    """
    # Load the base configuration
    if default:
        # Load the library default configuration
        from algosystem.backtesting.dashboard.utils.default_config import (
            DEFAULT_CONFIG_PATH,
        )

        click.echo("Creating configuration based on library default template")
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            config = json.load(f)
    elif user:
        # Load user configuration
        user_config_path = ensure_user_config_exists()
        click.echo(f"Creating configuration based on user template: {user_config_path}")
        with open(user_config_path, "r") as f:
            config = json.load(f)
    elif based_on:
        try:
            click.echo(f"Creating configuration based on: {based_on}")
            with open(based_on, "r") as f:
                config = json.load(f)
        except Exception as e:
            click.echo(f"Error loading base configuration: {str(e)}", err=True)
            sys.exit(1)
    else:
        # Default to user config if it exists, otherwise library default
        if os.path.exists(USER_CONFIG_FILE):
            click.echo("Creating configuration based on user template")
            with open(USER_CONFIG_FILE, "r") as f:
                config = json.load(f)
        else:
            from algosystem.backtesting.dashboard.utils.default_config import (
                DEFAULT_CONFIG_PATH,
            )

            click.echo("Creating configuration based on library default template")
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                config = json.load(f)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Save configuration file
    try:
        with open(output_path, "w") as f:
            json.dump(config, f, indent=4)
        click.echo(f"Configuration saved to: {output_path}")
    except Exception as e:
        click.echo(f"Error saving configuration: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option(
    "--output-file",
    "-o",
    type=click.Path(),
    default="./dashboard.html",
    help="Path to save the dashboard HTML file (default: ./dashboard.html)",
)
@click.option(
    "--benchmark",
    "-b",
    help="Benchmark to use. Can be a file path or an alias (e.g., 'sp500', 'nasdaq')",
)
@click.option(
    "--start-date",
    help="Start date for the backtest (YYYY-MM-DD). Default: first date in input data",
)
@click.option(
    "--end-date",
    help="End date for the backtest (YYYY-MM-DD). Default: last date in input data",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to a custom dashboard configuration file",
)
@click.option(
    "--default",
    is_flag=True,
    default=False,
    help="Use library default configuration (overrides --config)",
)
@click.option(
    "--open-browser",
    is_flag=True,
    default=True,
    help="Open the dashboard in a browser after rendering",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    default=False,
    help="Force refresh of benchmark data even if cached data exists",
)
def dashboard(
    input_file,
    output_file,
    benchmark,
    start_date,
    end_date,
    config,
    default,
    open_browser,
    force_refresh,
):
    """
    Create a standalone HTML dashboard from a CSV file that can be viewed without a web server.

    INPUT_FILE: Path to a CSV file with strategy data
    """
    import webbrowser

    from algosystem.backtesting.dashboard.dashboard_generator import (
        generate_standalone_dashboard,
    )
    from algosystem.backtesting.engine import Engine

    # Determine which configuration to use
    config_path = None
    if default:
        click.echo("Using library default dashboard configuration")
        from algosystem.backtesting.dashboard.utils.default_config import (
            DEFAULT_CONFIG_PATH,
        )

        config_path = DEFAULT_CONFIG_PATH
    elif config:
        click.echo(f"Using custom configuration from: {config}")
        config_path = config
    else:
        # Use user config
        config_path = ensure_user_config_exists()
        click.echo(f"Using user configuration: {config_path}")

    try:
        # Load the CSV data
        click.echo(f"Loading data from {input_file}...")
        data = pd.read_csv(input_file, index_col=0, parse_dates=True)
        click.echo(f"Loaded data with shape: {data.shape}")

        # Handle date range filtering
        if start_date:
            start_date = pd.to_datetime(start_date)
            data = data[data.index >= start_date]

        if end_date:
            end_date = pd.to_datetime(end_date)
            data = data[data.index <= end_date]

        if start_date or end_date:
            click.echo(f"Filtered data to shape: {data.shape}")

        # Load benchmark data if provided
        benchmark_data = None
        if benchmark:
            # Check if it's a file path
            if os.path.exists(benchmark):
                click.echo(f"Loading benchmark data from file: {benchmark}...")
                benchmark_data = pd.read_csv(benchmark, index_col=0, parse_dates=True)
                if (
                    isinstance(benchmark_data, pd.DataFrame)
                    and benchmark_data.shape[1] > 1
                ):
                    benchmark_data = benchmark_data.iloc[:, 0]  # Use first column
                click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")
            else:
                # Try to load as an alias
                click.echo(f"Loading benchmark data for alias: {benchmark}...")
                try:
                    benchmark_data = fetch_benchmark_data(
                        benchmark,
                        start_date=data.index[0] if not start_date else start_date,
                        end_date=data.index[-1] if not end_date else end_date,
                        force_refresh=force_refresh,
                    )
                    click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")
                except ImportError:
                    click.echo(
                        "Warning: Could not import benchmark module. Make sure the 'yfinance' package is installed."
                    )
                    click.echo("Continuing without benchmark data...")
                except Exception as e:
                    click.echo(f"Warning: Error fetching benchmark data: {str(e)}")
                    click.echo("Continuing without benchmark data...")
        elif not benchmark:
            # If no benchmark specified, use S&P 500 by default
            try:
                click.echo("Loading default benchmark (S&P 500)...")
                benchmark_data = fetch_benchmark_data(
                    DEFAULT_BENCHMARK,
                    start_date=data.index[0] if not start_date else start_date,
                    end_date=data.index[-1] if not end_date else end_date,
                    force_refresh=force_refresh,
                )
                click.echo(
                    f"Loaded S&P 500 benchmark data with {len(benchmark_data)} rows"
                )
            except ImportError:
                click.echo(
                    "Warning: Could not import benchmark module. Make sure the 'yfinance' package is installed."
                )
                click.echo("Continuing without benchmark data...")
            except Exception as e:
                click.echo(f"Warning: Error fetching S&P 500 benchmark data: {str(e)}")
                click.echo("Continuing without benchmark data...")

        # Create a backtest engine to process the data
        click.echo("Running backtest...")
        if isinstance(data, pd.DataFrame) and data.shape[1] > 1:
            # Use the first column as price data
            price_data = data.iloc[:, 0]
        else:
            price_data = data

        # Initialize and run the engine
        engine = Engine(
            data=price_data,
            benchmark=benchmark_data,
            start_date=start_date,
            end_date=end_date,
        )
        results = engine.run()
        click.echo("Backtest completed successfully")

        # Generate standalone dashboard
        click.echo(
            f"Generating standalone dashboard using configuration from: {config_path}"
        )
        dashboard_path = generate_standalone_dashboard(
            engine=engine, output_path=output_file, config_path=config_path
        )

        click.echo(f"Standalone dashboard generated successfully at: {dashboard_path}")

        # Open in browser if requested
        if open_browser:
            webbrowser.open("file://" + os.path.abspath(dashboard_path))
        else:
            click.echo("To view the dashboard, open this file in a web browser:")
            click.echo(f"  {os.path.abspath(dashboard_path)}")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        # Print traceback for debugging
        click.echo(traceback.format_exc())
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
def show_config(config_file):
    """
    Display the contents of a configuration file in a readable format.

    CONFIG_FILE: Path to the configuration file to display
    """
    try:
        with open(config_file, "r") as f:
            config = json.load(f)

        click.echo(f"Configuration file: {config_file}\n")

        # Display layout
        if "layout" in config:
            click.echo("=== Layout ===")
            click.echo(f"Title: {config['layout'].get('title', 'N/A')}")
            click.echo(f"Max columns: {config['layout'].get('max_cols', 'N/A')}")
            click.echo("")

        # Display metrics
        if "metrics" in config:
            click.echo("=== Metrics ===")
            for i, metric in enumerate(config["metrics"]):
                click.echo(
                    f"{i + 1}. {metric.get('title', 'Untitled')} ({metric.get('id', 'no-id')})"
                )
                click.echo(f"   Type: {metric.get('type', 'N/A')}")
                click.echo(
                    f"   Position: Row {metric['position'].get('row', 'N/A')}, Column {metric['position'].get('col', 'N/A')}"
                )
                click.echo("")

        # Display charts
        if "charts" in config:
            click.echo("=== Charts ===")
            for i, chart in enumerate(config["charts"]):
                click.echo(
                    f"{i + 1}. {chart.get('title', 'Untitled')} ({chart.get('id', 'no-id')})"
                )
                click.echo(f"   Type: {chart.get('type', 'N/A')}")
                click.echo(f"   Data Key: {chart.get('data_key', 'N/A')}")
                click.echo(
                    f"   Position: Row {chart['position'].get('row', 'N/A')}, Column {chart['position'].get('col', 'N/A')}"
                )
                click.echo("")

    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--show-user",
    is_flag=True,
    default=False,
    help="Show full path of user configuration file",
)
@click.option(
    "--show-default",
    is_flag=True,
    default=False,
    help="Show full path of library default configuration file",
)
def list_configs(show_user, show_default):
    """
    List all available configuration files in the user's home directory.
    """
    # Show special config file paths if requested
    if show_user:
        user_config_path = ensure_user_config_exists()
        click.echo(f"User configuration file: {user_config_path}")
        return

    if show_default:
        from algosystem.backtesting.dashboard.utils.default_config import (
            DEFAULT_CONFIG_PATH,
        )

        click.echo(f"Library default configuration: {DEFAULT_CONFIG_PATH}")
        return

    # List all config files in user directory
    if not os.path.exists(USER_CONFIG_DIR):
        click.echo(
            "No configuration directory found. Use 'create-config' to create your first configuration."
        )
        return

    config_files = [f for f in os.listdir(USER_CONFIG_DIR) if f.endswith(".json")]

    if not config_files:
        click.echo("No configuration files found in the user directory.")
        click.echo(f"Directory: {USER_CONFIG_DIR}")
        return

    click.echo(f"Configuration files in {USER_CONFIG_DIR}:")
    for i, config_file in enumerate(config_files):
        full_path = os.path.join(USER_CONFIG_DIR, config_file)
        file_size = os.path.getsize(full_path) / 1024  # size in KB
        mod_time = os.path.getmtime(full_path)
        mod_time_str = pd.to_datetime(mod_time, unit="s").strftime("%Y-%m-%d %H:%M:%S")

        # Mark the main user config file
        marker = " (user config)" if config_file == "config.json" else ""
        click.echo(
            f"{i + 1}. {config_file}{marker} ({file_size:.1f} KB, modified: {mod_time_str})"
        )

    # Show paths to special files
    click.echo(f"\nUser configuration: {USER_CONFIG_FILE}")
    click.echo("Use --show-default to see the library default configuration path")


# Add a new command to reset user config
@cli.command()
@click.option(
    "--backup",
    is_flag=True,
    default=True,
    help="Create a backup of existing user configuration (default: True)",
)
@click.option(
    "--no-backup",
    is_flag=True,
    default=False,
    help="Do not create a backup (overrides --backup)",
)
def reset_user_config(backup, no_backup):
    """
    Reset the user configuration to library defaults.
    """
    if not os.path.exists(USER_CONFIG_FILE):
        click.echo("No user configuration file exists. Creating one now...")
        ensure_user_config_exists()
        return

    # Confirm reset
    click.confirm(
        f"This will reset your user configuration at {USER_CONFIG_FILE} to library defaults. "
        f"Continue?",
        abort=True,
    )

    # Create backup if requested
    create_backup = backup and not no_backup
    if create_backup:
        backup_file = (
            f"{USER_CONFIG_FILE}.backup.{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.rename(USER_CONFIG_FILE, backup_file)
        click.echo(f"Backup created: {backup_file}")

    # Load default config and save to user config
    from algosystem.backtesting.dashboard.utils.default_config import get_default_config

    default_config = get_default_config()

    with open(USER_CONFIG_FILE, "w") as f:
        json.dump(default_config, f, indent=4)

    click.echo(f"User configuration reset to library defaults: {USER_CONFIG_FILE}")


# Add a new command to list and manage benchmarks
@cli.command()
@click.option(
    "--fetch-all",
    is_flag=True,
    default=False,
    help="Fetch or update all available benchmarks",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    default=False,
    help="Force refresh of benchmark data even if cached data exists",
)
@click.option(
    "--info",
    is_flag=True,
    default=False,
    help="Show detailed information about all available benchmarks",
)
@click.option(
    "--start-date",
    help="Start date for benchmark data (YYYY-MM-DD). Default: 5 years ago",
)
@click.option(
    "--end-date", help="End date for benchmark data (YYYY-MM-DD). Default: today"
)
@click.argument("benchmark", required=False)
def benchmarks(fetch_all, force_refresh, info, start_date, end_date, benchmark):
    """
    List, fetch, and manage benchmark data.

    Specify a benchmark alias to fetch or update data for that specific benchmark.
    Use --fetch-all to fetch or update all available benchmarks.
    """
    try:
        # Parse dates if provided
        if start_date:
            start_date = pd.to_datetime(start_date)
        if end_date:
            end_date = pd.to_datetime(end_date)

        # Show info about all benchmarks
        if info:
            try:
                benchmark_info = get_benchmark_info()

                # Group by category
                categories = benchmark_info.groupby("Category")

                click.echo("Available benchmarks by category:\n")
                for category_name, group in categories:
                    click.echo(f"=== {category_name} ===")
                    for _, row in group.iterrows():
                        click.echo(f"  • {row['Alias']}: {row['Description']}")
                    click.echo("")

                click.echo(f"Total benchmarks available: {len(benchmark_info)}")
                click.echo(
                    "Use 'algosystem benchmarks <alias>' to fetch a specific benchmark."
                )
                click.echo(
                    "Use 'algosystem benchmarks --fetch-all' to fetch all benchmarks."
                )
                return
            except ImportError:
                click.echo(
                    "Error: Benchmark module not available. Make sure yfinance is installed:"
                )
                click.echo("  pip install yfinance")
                sys.exit(1)

        # List available benchmarks if no specific action requested
        if not benchmark and not fetch_all:
            try:
                benchmark_list = get_benchmark_list()
                click.echo("Available benchmark aliases:")

                # Display benchmarks in columns
                col_width = max(len(alias) for alias in benchmark_list) + 2
                num_cols = 3  # Adjust this for different terminal widths

                for i in range(0, len(benchmark_list), num_cols):
                    row = benchmark_list[i : i + num_cols]
                    click.echo("  " + "".join(alias.ljust(col_width) for alias in row))

                click.echo(f"\nTotal: {len(benchmark_list)} benchmarks available")
                click.echo(
                    "\nUse 'algosystem benchmarks --info' for detailed descriptions."
                )
                click.echo(
                    "Use 'algosystem benchmarks <alias>' to fetch a specific benchmark."
                )
                return
            except ImportError:
                click.echo(
                    "Error: Benchmark module not available. Make sure yfinance is installed:"
                )
                click.echo("  pip install yfinance")
                sys.exit(1)

        # Fetch all benchmarks
        if fetch_all:
            try:
                click.echo("Fetching data for all benchmarks...")
                from algosystem.data.benchmark import fetch_all_benchmarks

                benchmarks = fetch_all_benchmarks(
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=force_refresh,
                )

                click.echo(
                    f"Successfully fetched data for {len(benchmarks)} benchmarks."
                )
                return
            except ImportError:
                click.echo(
                    "Error: Benchmark module not available. Make sure yfinance is installed:"
                )
                click.echo("  pip install yfinance")
                sys.exit(1)

        # Fetch specific benchmark
        if benchmark:
            try:
                click.echo(f"Fetching data for benchmark: {benchmark}")
                benchmark_data = fetch_benchmark_data(
                    benchmark,
                    start_date=start_date,
                    end_date=end_date,
                    force_refresh=force_refresh,
                )

                # Print benchmark info
                click.echo(f"Successfully fetched benchmark data: {benchmark}")
                click.echo(f"Data shape: {benchmark_data.shape}")
                click.echo(
                    f"Date range: {benchmark_data.index[0].date()} to {benchmark_data.index[-1].date()}"
                )

                # Calculate a few basic stats
                returns = benchmark_data.pct_change().dropna()
                total_return = (benchmark_data.iloc[-1] / benchmark_data.iloc[0]) - 1
                annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
                volatility = returns.std() * np.sqrt(252)

                click.echo(f"Total return: {total_return:.2%}")
                click.echo(f"Annualized return: {annualized_return:.2%}")
                click.echo(f"Annualized volatility: {volatility:.2%}")

                return
            except ImportError:
                click.echo(
                    "Error: Benchmark module not available. Make sure yfinance is installed:"
                )
                click.echo("  pip install yfinance")
                sys.exit(1)
            except ValueError as e:
                click.echo(f"Error: {str(e)}")
                sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {str(e)}")
        # Print traceback for debugging
        click.echo(traceback.format_exc())
        sys.exit(1)


# Add a command to compare benchmarks
@cli.command()
@click.argument("benchmarks", nargs=-1, required=True)
@click.option(
    "--output-file", "-o", type=click.Path(), help="Save comparison results to CSV file"
)
@click.option(
    "--start-date", help="Start date for comparison (YYYY-MM-DD). Default: 5 years ago"
)
@click.option("--end-date", help="End date for comparison (YYYY-MM-DD). Default: today")
@click.option(
    "--metrics",
    is_flag=True,
    default=False,
    help="Show performance metrics for each benchmark",
)
@click.option(
    "--force-refresh",
    is_flag=True,
    default=False,
    help="Force refresh of benchmark data even if cached data exists",
)
def compare_benchmarks(
    benchmarks, output_file, start_date, end_date, metrics, force_refresh
):
    """
    Compare multiple benchmarks over the same period.

    Provide benchmark aliases separated by spaces.
    Example: algosystem compare-benchmarks sp500 nasdaq treasuries
    """
    try:
        # Import required functions
        from algosystem.data.benchmark import compare_benchmarks, get_benchmark_metrics

        # Parse dates if provided
        if start_date:
            start_date = pd.to_datetime(start_date)
        if end_date:
            end_date = pd.to_datetime(end_date)

        # Get comparison data
        click.echo(f"Comparing benchmarks: {', '.join(benchmarks)}")
        comparison_df = compare_benchmarks(
            benchmarks, start_date=start_date, end_date=end_date
        )

        # Print basic info
        click.echo(
            f"Comparison period: {comparison_df.index[0].date()} to {comparison_df.index[-1].date()}"
        )
        click.echo(f"Number of trading days: {len(comparison_df)}")

        # Calculate total returns
        total_returns = {}
        for column in comparison_df.columns:
            total_returns[column] = (
                comparison_df[column].iloc[-1] / comparison_df[column].iloc[0]
            ) - 1

        # Sort by total return
        sorted_benchmarks = sorted(
            total_returns.items(), key=lambda x: x[1], reverse=True
        )

        # Print total returns
        click.echo("\nTotal Returns:")
        for benchmark, return_value in sorted_benchmarks:
            click.echo(f"  {benchmark}: {return_value:.2%}")

        # Show additional metrics if requested
        if metrics:
            click.echo("\nPerformance Metrics:")
            metrics_list = []

            for alias in benchmarks:
                try:
                    benchmark_metrics = get_benchmark_metrics(
                        alias, start_date=start_date, end_date=end_date
                    )

                    metrics_list.append(
                        {
                            "Benchmark": alias,
                            "Total Return": benchmark_metrics["total_return"] * 100,
                            "Annual Return": benchmark_metrics["annualized_return"]
                            * 100,
                            "Volatility": benchmark_metrics["volatility"] * 100,
                            "Sharpe Ratio": benchmark_metrics["sharpe_ratio"],
                            "Max Drawdown": benchmark_metrics["max_drawdown"] * 100,
                        }
                    )
                except Exception as e:
                    click.echo(
                        f"Warning: Could not calculate metrics for {alias}: {str(e)}"
                    )

            # Print metrics table
            if metrics_list:
                for metric in metrics_list:
                    click.echo(f"\n  {metric['Benchmark']}:")
                    click.echo(f"    Total Return: {metric['Total Return']:.2f}%")
                    click.echo(f"    Annual Return: {metric['Annual Return']:.2f}%")
                    click.echo(f"    Volatility: {metric['Volatility']:.2f}%")
                    click.echo(f"    Sharpe Ratio: {metric['Sharpe Ratio']:.2f}")
                    click.echo(f"    Max Drawdown: {metric['Max Drawdown']:.2f}%")

        # Save to file if requested
        if output_file:
            comparison_df.to_csv(output_file)
            click.echo(f"\nComparison data saved to: {output_file}")

    except ImportError:
        click.echo(
            "Error: Benchmark module not available. Make sure yfinance is installed:"
        )
        click.echo("  pip install yfinance")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {str(e)}")
        # Print traceback for debugging
        click.echo(traceback.format_exc())
        sys.exit(1)


# Add a test command to simulate a basic workflow
@cli.command()
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="./test_dashboard",
    help="Directory to save the test dashboard (default: ./test_dashboard)",
)
@click.option(
    "--periods",
    "-p",
    type=int,
    default=252,
    help="Number of trading days to simulate (default: 252 = 1 year)",
)
@click.option(
    "--benchmark", "-b", help="Benchmark to use for comparison", default="sp500"
)
@click.option(
    "--open-browser",
    is_flag=True,
    default=False,
    help="Open the dashboard in a browser when done",
)
def test(output_dir, periods, benchmark, open_browser):
    """
    Run a quick test with simulated data and generate a dashboard.

    This is useful for testing the system without having real data.
    It creates a simulated strategy and benchmark, then generates a dashboard.
    """
    import os

    import numpy as np

    from algosystem.backtesting.dashboard.dashboard_generator import generate_dashboard
    from algosystem.backtesting.engine import Engine

    click.echo(f"Creating test data with {periods} trading days...")

    # Create a directory for test output
    os.makedirs(output_dir, exist_ok=True)

    # Generate random data for a simulated strategy
    dates = pd.date_range(end=datetime.now(), periods=periods, freq="B")
    np.random.seed(42)  # For reproducibility

    # Strategy returns with positive drift
    returns = np.random.normal(
        0.0005, 0.01, periods
    )  # 0.05% daily return, 1% volatility
    strategy_prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()

    # Save strategy data to CSV
    strategy_file = os.path.join(output_dir, "strategy.csv")
    strategy_prices.to_csv(strategy_file)
    click.echo(f"Strategy data saved to {strategy_file}")

    # Try to get benchmark data
    benchmark_data = None
    try:
        click.echo(f"Loading benchmark data for {benchmark}...")
        benchmark_data = fetch_benchmark_data(
            benchmark, start_date=dates[0], end_date=dates[-1]
        )
        click.echo(f"Loaded benchmark data with {len(benchmark_data)} rows")
    except Exception as e:
        click.echo(f"Warning: Error fetching benchmark data: {str(e)}")
        click.echo("Continuing without benchmark data...")

    # Run backtest and generate dashboard
    click.echo("Running backtest...")
    engine = Engine(data=strategy_prices, benchmark=benchmark_data)
    results = engine.run()

    # Print some basic metrics
    metrics = results["metrics"]
    click.echo("\nBacktest Results:")
    click.echo(f"Total Return: {metrics.get('total_return', 0) * 100:.2f}%")
    click.echo(f"Annualized Return: {metrics.get('annualized_return', 0) * 100:.2f}%")
    click.echo(f"Max Drawdown: {metrics.get('max_drawdown', 0) * 100:.2f}%")
    click.echo(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")

    if "alpha" in metrics:
        click.echo(f"Alpha: {metrics.get('alpha', 0) * 100:.2f}%")
    if "beta" in metrics:
        click.echo(f"Beta: {metrics.get('beta', 0):.2f}")

    # Generate dashboard
    click.echo("\nGenerating dashboard...")
    dashboard_path = generate_dashboard(
        engine=engine, output_dir=output_dir, open_browser=open_browser
    )

    click.echo(f"Dashboard generated at: {dashboard_path}")

    if not open_browser:
        click.echo("To view the dashboard, open this file in a web browser:")
        click.echo(f"  {os.path.abspath(dashboard_path)}")

    return dashboard_path


if __name__ == "__main__":
    cli()
