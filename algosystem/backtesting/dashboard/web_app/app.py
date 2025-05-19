import json
import logging
import os
import sys
import tempfile
import traceback

from flask import Flask, jsonify

# Set up basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path
sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
)

# Import AlgoSystem modules

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = tempfile.mkdtemp()
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload

# Path to the default configuration
DEFAULT_CONFIG_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "utils",
        "default_config.json",
    )
)

# Path to the user configuration directory
USER_CONFIG_DIR = os.path.abspath(os.path.join(os.path.expanduser("~"), ".algosystem"))

# Path to the default user configuration
USER_CONFIG_PATH = os.path.join(USER_CONFIG_DIR, "dashboard_config.json")

# Check if a specific configuration path was provided via environment variable
CUSTOM_CONFIG_PATH = os.environ.get("ALGO_DASHBOARD_CONFIG")
SAVE_CONFIG_PATH = os.environ.get("ALGO_DASHBOARD_SAVE_CONFIG")

# Determine which configuration to use for both loading and saving
if SAVE_CONFIG_PATH:
    # If --save-config was specified, use it for both loading and saving
    CONFIG_PATH = os.path.abspath(SAVE_CONFIG_PATH)
    logger.info(
        f"Using custom configuration path for loading and saving: {CONFIG_PATH}"
    )
elif CUSTOM_CONFIG_PATH:
    # If --config was specified, use it for loading
    CONFIG_PATH = os.path.abspath(CUSTOM_CONFIG_PATH)
    logger.info(f"Using custom configuration path for loading: {CONFIG_PATH}")
else:
    # Fall back to the user config
    CONFIG_PATH = USER_CONFIG_PATH
    logger.info(f"Using default user configuration path: {CONFIG_PATH}")

# Ensure the directories exist
os.makedirs(USER_CONFIG_DIR, exist_ok=True)
if CONFIG_PATH:
    config_dir = os.path.dirname(os.path.abspath(CONFIG_PATH))
    os.makedirs(config_dir, exist_ok=True)
    logger.info(f"Ensured directory exists: {config_dir}")

# Global variables
uploaded_data = None
engine = None
dashboard_path = None


def load_config(config_path=None):
    """
    Load configuration from the specified path, falling back to defaults if needed.

    Parameters:
    -----------
    config_path : str, optional
        Path to the configuration file

    Returns:
    --------
    dict
        Configuration dictionary
    """
    # Determine which configuration to load
    if config_path is None:
        config_path = CONFIG_PATH

    logger.info(f"Attempting to load configuration from: {config_path}")

    # If config_path exists, load it
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
                logger.info(f"Successfully loaded configuration from: {config_path}")
                return config_data
        except json.JSONDecodeError as e:
            logger.warning(
                f"Failed to parse config at {config_path}: {str(e)}. Using default config."
            )
        except Exception as e:
            logger.warning(
                f"Error reading config at {config_path}: {str(e)}. Using default config."
            )
    else:
        logger.info(
            f"Configuration file {config_path} does not exist yet. Will be created with default settings."
        )

    # Fall back to default configuration if needed
    try:
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            default_config = json.load(f)
            logger.info(f"Loaded default configuration from: {DEFAULT_CONFIG_PATH}")

        # If the custom config doesn't exist yet, save the default config there
        if config_path != DEFAULT_CONFIG_PATH and not os.path.exists(config_path):
            save_config(default_config, config_path)
            logger.info(f"Created new configuration file at: {config_path}")

        return default_config
    except Exception as e:
        logger.error(f"Error loading default configuration: {str(e)}")
        # Return a minimal default configuration to prevent further errors
        return {
            "metrics": [],
            "charts": [],
            "layout": {"max_cols": 2, "title": "AlgoSystem Trading Dashboard"},
        }


def save_config(config, config_path=None):
    """
    Enhanced save_config function with robust error handling and debugging.

    Parameters:
    -----------
    config : dict
        Configuration to save
    config_path : str, optional
        Path where the configuration should be saved

    Returns:
    --------
    bool
        True if the configuration was saved successfully, False otherwise
    """
    logger = logging.getLogger(__name__)

    # Use the provided config_path or fall back to default
    if config_path is None:
        config_path = os.environ.get(
            "ALGO_DASHBOARD_SAVE_CONFIG",
            os.path.join(
                os.path.expanduser("~"), ".algosystem", "dashboard_config.json"
            ),
        )

    logger.info(f"Saving configuration to: {config_path}")
    print(
        f"Saving configuration to: {config_path}"
    )  # Extra console output for debugging

    # Validate configuration content
    if not isinstance(config, dict):
        logger.error(f"Invalid configuration data type: {type(config).__name__}")
        return False

    # Ensure the configuration has the required sections
    if "metrics" not in config:
        config["metrics"] = []
    if "charts" not in config:
        config["charts"] = []
    if "layout" not in config:
        config["layout"] = {"max_cols": 2, "title": "AlgoSystem Trading Dashboard"}

    # Create directory if it doesn't exist
    config_dir = os.path.dirname(os.path.abspath(config_path))
    os.makedirs(config_dir, exist_ok=True)

    try:
        # Print some diagnostic info
        print(f"Config to save: {json.dumps(config, indent=2)[:200]}...")

        # First write to a temporary file
        temp_file = f"{config_path}.tmp"
        with open(temp_file, "w") as f:
            json.dump(config, f, indent=4)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Now rename the temp file to the target file (atomic operation)
        os.replace(temp_file, config_path)

        # Verify the file was saved correctly
        file_size = os.path.getsize(config_path)
        logger.info(
            f"Configuration saved successfully: {config_path} ({file_size} bytes)"
        )
        print(f"Configuration saved successfully: {config_path} ({file_size} bytes)")

        # Try to read back the saved file as an extra verification step
        try:
            with open(config_path, "r") as f:
                saved_config = json.load(f)
            metrics_count = len(saved_config.get("metrics", []))
            charts_count = len(saved_config.get("charts", []))
            logger.info(
                f"Verified saved config: {metrics_count} metrics, {charts_count} charts"
            )
            print(
                f"Verified saved config: {metrics_count} metrics, {charts_count} charts"
            )
        except Exception as read_error:
            logger.warning(f"Warning: Could not verify saved file: {str(read_error)}")
            print(f"Warning: Could not verify saved file: {str(read_error)}")

        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        print(f"Error saving configuration: {str(e)}")
        logger.error(traceback.format_exc())
        return False


# Add a route specifically for debugging the configuration
@app.route("/api/debug/config", methods=["GET"])
def debug_config():
    """Return detailed information about the configuration for debugging."""
    config_info = {
        "config_paths": {
            "DEFAULT_CONFIG_PATH": DEFAULT_CONFIG_PATH,
            "USER_CONFIG_PATH": USER_CONFIG_PATH,
            "CUSTOM_CONFIG_PATH": CUSTOM_CONFIG_PATH,
            "SAVE_CONFIG_PATH": SAVE_CONFIG_PATH,
            "ACTIVE_CONFIG_PATH": CONFIG_PATH,
        },
        "file_exists": {
            "DEFAULT_CONFIG_PATH": os.path.exists(DEFAULT_CONFIG_PATH),
            "USER_CONFIG_PATH": os.path.exists(USER_CONFIG_PATH),
            "CUSTOM_CONFIG_PATH": CUSTOM_CONFIG_PATH
            and os.path.exists(CUSTOM_CONFIG_PATH),
            "SAVE_CONFIG_PATH": SAVE_CONFIG_PATH and os.path.exists(SAVE_CONFIG_PATH),
            "ACTIVE_CONFIG_PATH": os.path.exists(CONFIG_PATH),
        },
        "file_sizes": {
            "DEFAULT_CONFIG_PATH": (
                os.path.getsize(DEFAULT_CONFIG_PATH)
                if os.path.exists(DEFAULT_CONFIG_PATH)
                else None
            ),
            "USER_CONFIG_PATH": (
                os.path.getsize(USER_CONFIG_PATH)
                if os.path.exists(USER_CONFIG_PATH)
                else None
            ),
            "CUSTOM_CONFIG_PATH": (
                os.path.getsize(CUSTOM_CONFIG_PATH)
                if CUSTOM_CONFIG_PATH and os.path.exists(CUSTOM_CONFIG_PATH)
                else None
            ),
            "SAVE_CONFIG_PATH": (
                os.path.getsize(SAVE_CONFIG_PATH)
                if SAVE_CONFIG_PATH and os.path.exists(SAVE_CONFIG_PATH)
                else None
            ),
            "ACTIVE_CONFIG_PATH": (
                os.path.getsize(CONFIG_PATH) if os.path.exists(CONFIG_PATH) else None
            ),
        },
        "current_config": load_config(),
    }
    return jsonify(config_info)


def start_dashboard_editor(host="127.0.0.1", port=5000, debug=False):
    """Start the dashboard editor web server."""
    # Import routes here to avoid circular imports
    from algosystem.backtesting.dashboard.web_app.routes import register_routes

    # Print the configuration path being used
    if os.path.exists(CONFIG_PATH):
        logger.info(f"Using existing configuration from: {CONFIG_PATH}")
    else:
        logger.info(f"Will create new configuration at: {CONFIG_PATH}")

    # Register all routes
    global_vars = register_routes(
        app, load_config, save_config, DEFAULT_CONFIG_PATH, CONFIG_PATH, CONFIG_PATH
    )

    # Store global variables
    global uploaded_data, engine, dashboard_path
    uploaded_data = global_vars.get("uploaded_data")
    engine = global_vars.get("engine")
    dashboard_path = global_vars.get("dashboard_path")

    # Run the Flask app
    logger.info(f"Starting dashboard editor on http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    start_dashboard_editor(debug=True)
