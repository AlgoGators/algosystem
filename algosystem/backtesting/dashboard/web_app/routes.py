from flask import render_template, request, jsonify, redirect, url_for, flash, send_from_directory
import os
import json
import pandas as pd
import numpy as np
from werkzeug.utils import secure_filename
from algosystem.backtesting.engine import Engine

# Import available components
from algosystem.backtesting.dashboard.web_app.available_components import AVAILABLE_METRICS, AVAILABLE_CHARTS

# Global references that will be set when routes are registered
uploaded_data = None
engine = None
dashboard_path = None


def register_routes(app, load_config_func, save_config_func, 
                   default_config_path, config_path, save_config_path):
    """
    Register all routes for the Flask application.
    
    Parameters:
    -----------
    app : Flask
        Flask application
    load_config_func : function
        Function to load configuration
    save_config_func : function
        Function to save configuration
    default_config_path : str
        Path to default configuration
    config_path : str
        Path to current configuration
    save_config_path : str
        Path where to save configuration
    """
    global uploaded_data, engine, dashboard_path
    
    @app.route('/')
    def index():
        """Render the dashboard editor."""
        config = load_config_func()
        return render_template('index.html', 
                              config=config, 
                              available_charts=AVAILABLE_CHARTS,
                              available_metrics=AVAILABLE_METRICS,
                              data_loaded=(uploaded_data is not None))

    @app.route('/api/config', methods=['GET'])
    def get_config():
        """Get the current configuration."""
        config = load_config_func()
        return jsonify(config)

    @app.route('/api/config', methods=['POST'])
    def update_config():
        """Update the configuration."""
        config = request.json
        success = save_config_func(config)
        
        if success:
            return jsonify({"status": "success", "message": "Configuration saved successfully"})
        else:
            return jsonify({"status": "error", "message": "Failed to save configuration"}), 500

    @app.route('/api/config/save-location', methods=['GET'])
    def get_config_save_location():
        """Get the location where the configuration will be saved."""
        save_path = save_config_path if save_config_path else config_path
        return jsonify({"save_path": save_path})

    @app.route('/api/reset-config', methods=['POST'])
    def reset_config():
        """Reset to the default configuration."""
        # Load default config
        with open(default_config_path, 'r') as f:
            config = json.load(f)
        
        # Save to the current config path (don't modify the default config file)
        success = save_config_func(config)
        
        if success:
            return jsonify({"status": "success", "message": "Reset to default configuration successfully"})
        else:
            return jsonify({"status": "error", "message": "Failed to reset configuration"}), 500

    @app.route('/dashboard')
    def view_dashboard():
        """View the generated dashboard."""
        if dashboard_path:
            dashboard_dir = os.path.dirname(dashboard_path)
            return send_from_directory(dashboard_dir, 'dashboard.html')
        else:
            return redirect(url_for('index'))

    @app.route('/dashboard/<path:filename>')
    def dashboard_files(filename):
        """Serve dashboard files."""
        if dashboard_path:
            dashboard_dir = os.path.dirname(dashboard_path)
            return send_from_directory(dashboard_dir, filename)
        else:
            return redirect(url_for('index'))
    
    # Return references to the global variables
    return {
        'uploaded_data': uploaded_data,
        'engine': engine,
        'dashboard_path': dashboard_path
    }