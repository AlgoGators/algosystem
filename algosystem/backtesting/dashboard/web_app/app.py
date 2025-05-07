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

# Path to the user configuration
USER_CONFIG_PATH = os.path.abspath(os.path.join(
    os.path.expanduser("~"),
    ".algosystem",
    "dashboard_config.json"
))

# Ensure the directory exists
os.makedirs(os.path.dirname(USER_CONFIG_PATH), exist_ok=True)

# Global variables
uploaded_data = None
engine = None
dashboard_path = None

# Import routes
from algosystem.backtesting.dashboard.web_app.routes import *

def start_dashboard_editor(host='127.0.0.1', port=5000, debug=False):
    """Start the dashboard editor web server."""
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    start_dashboard_editor(debug=True)