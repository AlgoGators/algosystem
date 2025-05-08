from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import json
import pandas as pd
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import AlgoSystem modules
from algosystem.backtesting.dashboard.dashboard_generator import generate_dashboard
from algosystem.backtesting.engine import Engine

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Path to the default configuration
DEFAULT_CONFIG_PATH = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "utils",
    "default_config.json"
))

# Path to the user configuration directory
USER_CONFIG_DIR = os.path.abspath(os.path.join(
    os.path.expanduser("~"),
    ".algosystem"
))

# Path to the default user configuration
USER_CONFIG_PATH = os.path.join(USER_CONFIG_DIR, "dashboard_config.json")

# Check if a specific configuration path was provided via environment variable
CUSTOM_CONFIG_PATH = os.environ.get('ALGO_DASHBOARD_CONFIG')
SAVE_CONFIG_PATH = os.environ.get('ALGO_DASHBOARD_SAVE_CONFIG')

# Determine which configuration to use
CONFIG_PATH = CUSTOM_CONFIG_PATH if CUSTOM_CONFIG_PATH else USER_CONFIG_PATH

# Ensure the directories exist
os.makedirs(USER_CONFIG_DIR, exist_ok=True)
if SAVE_CONFIG_PATH:
    os.makedirs(os.path.dirname(os.path.abspath(SAVE_CONFIG_PATH)), exist_ok=True)

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
    
    # If config_path exists, load it
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Failed to parse config at {config_path}. Using default config.")
    
    # Fall back to default configuration if needed
    with open(DEFAULT_CONFIG_PATH, 'r') as f:
        default_config = json.load(f)
    
    return default_config

def save_config(config, config_path=None):
    """
    Save configuration to the specified path.
    
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
    # Determine where to save the configuration
    if config_path is None:
        # If a save path was specified via environment variable, use that
        if SAVE_CONFIG_PATH:
            config_path = SAVE_CONFIG_PATH
        else:
            # Otherwise use the user config path
            config_path = USER_CONFIG_PATH
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving configuration: {str(e)}")
        return False

def start_dashboard_editor(host='127.0.0.1', port=5000, debug=False):
    """Start the dashboard editor web server."""
    # Import routes here to avoid circular imports
    from algosystem.backtesting.dashboard.web_app.routes import register_routes
    
    # Register all routes
    register_routes(app, load_config, save_config, 
                   DEFAULT_CONFIG_PATH, CONFIG_PATH, SAVE_CONFIG_PATH)
    
    # Run the Flask app
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    start_dashboard_editor(debug=True)