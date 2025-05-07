from flask import render_template, request, jsonify, redirect, url_for, flash, send_from_directory
import os
import json
import pandas as pd
import numpy as np
from werkzeug.utils import secure_filename
from algosystem.backtesting.dashboard.web_app.app import app, DEFAULT_CONFIG_PATH, USER_CONFIG_PATH, uploaded_data, engine, dashboard_path
from algosystem.backtesting.engine import Engine

# Available chart types and metrics
AVAILABLE_CHARTS = [
    {"id": "equity_curve", "type": "LineChart", "title": "Equity Curve", "data_key": "equity", 
     "description": "Shows the growth of portfolio value over time"},
    {"id": "drawdown", "type": "LineChart", "title": "Drawdown Chart", "data_key": "drawdown", 
     "description": "Shows the drawdown periods for the strategy"},
    {"id": "monthly_returns", "type": "HeatmapTable", "title": "Monthly Returns Heatmap", "data_key": "monthly_returns", 
     "description": "Displays monthly returns as a heatmap"},
    {"id": "rolling_sharpe", "type": "LineChart", "title": "Rolling Sharpe Ratio", "data_key": "rolling_sharpe", 
     "description": "Shows the rolling Sharpe ratio over time"},
    {"id": "rolling_volatility", "type": "LineChart", "title": "Rolling Volatility", "data_key": "rolling_volatility", 
     "description": "Shows the rolling volatility over time"},
    {"id": "rolling_returns", "type": "LineChart", "title": "Rolling Returns", "data_key": "rolling_returns", 
     "description": "Shows the rolling returns over time"},
    {"id": "returns_distribution", "type": "LineChart", "title": "Returns Distribution", "data_key": "returns_distribution", 
     "description": "Shows the distribution of returns"}
]

AVAILABLE_METRICS = [
    {"id": "annual_return", "type": "Percentage", "title": "Annualized Return", "value_key": "annual_return", 
     "description": "Annualized return of the strategy"},
    {"id": "volatility", "type": "Percentage", "title": "Volatility", "value_key": "volatility", 
     "description": "Annualized volatility of the strategy"},
    {"id": "sharpe_ratio", "type": "Value", "title": "Sharpe Ratio", "value_key": "sharpe_ratio", 
     "description": "Sharpe ratio of the strategy"},
    {"id": "sortino_ratio", "type": "Value", "title": "Sortino Ratio", "value_key": "sortino_ratio", 
     "description": "Sortino ratio of the strategy"},
    {"id": "max_drawdown", "type": "Percentage", "title": "Max Drawdown", "value_key": "max_drawdown", 
     "description": "Maximum drawdown of the strategy"},
    {"id": "calmar_ratio", "type": "Value", "title": "Calmar Ratio", "value_key": "calmar_ratio", 
     "description": "Calmar ratio of the strategy"},
    {"id": "win_rate", "type": "Percentage", "title": "Win Rate", "value_key": "win_rate", 
     "description": "Percentage of winning trades"},
    {"id": "avg_win", "type": "Percentage", "title": "Average Win", "value_key": "avg_win", 
     "description": "Average return of winning trades"},
    {"id": "avg_loss", "type": "Percentage", "title": "Average Loss", "value_key": "avg_loss", 
     "description": "Average return of losing trades"}
]

def load_config(config_path=None):
    """Load configuration from file or use default if file doesn't exist."""
    if config_path is None:
        config_path = USER_CONFIG_PATH
    
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    else:
        # Use default config
        with open(DEFAULT_CONFIG_PATH, 'r') as f:
            config = json.load(f)
        
        # Save to user config
        with open(USER_CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        
        return config

def save_config(config, config_path=None):
    """Save configuration to file."""
    if config_path is None:
        config_path = USER_CONFIG_PATH
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

@app.route('/')
def index():
    """Render the dashboard editor."""
    config = load_config()
    return render_template('index.html', 
                          config=config, 
                          available_charts=AVAILABLE_CHARTS,
                          available_metrics=AVAILABLE_METRICS,
                          data_loaded=(uploaded_data is not None))

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get the current configuration."""
    config = load_config()
    return jsonify(config)

@app.route('/api/config', methods=['POST'])
def update_config():
    """Update the configuration."""
    config = request.json
    save_config(config)
    return jsonify({"status": "success"})

@app.route('/api/reset-config', methods=['POST'])
def reset_config():
    """Reset to the default configuration."""
    with open(DEFAULT_CONFIG_PATH, 'r') as f:
        config = json.load(f)
    
    save_config(config)
    return jsonify({"status": "success"})

@app.route('/api/upload-csv', methods=['POST'])
def upload_csv():
    """Upload a CSV file and process it."""
    global uploaded_data, engine, dashboard_path
    
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"})
    
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Load the CSV data
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
            
            # If it's a multi-column DataFrame, use the first column as price data
            if isinstance(data, pd.DataFrame) and data.shape[1] > 1:
                price_data = data.iloc[:, 0]
            else:
                price_data = data
            
            # Create a backtest engine
            engine = Engine(data=price_data, benchmark=None)
            results = engine.run()
            
            # Generate dashboard
            dashboard_path = engine.generate_dashboard(
                output_dir=os.path.join(app.config['UPLOAD_FOLDER'], 'dashboard'),
                open_browser=False,
                config_path=USER_CONFIG_PATH
            )
            
            # Store the uploaded data for later use
            uploaded_data = data
            
            return jsonify({
                "status": "success", 
                "message": f"Successfully processed {filename}",
                "dashboard_url": f"/dashboard"
            })
        
        except Exception as e:
            return jsonify({"status": "error", "message": f"Error processing file: {str(e)}"})
    
    return jsonify({"status": "error", "message": "Invalid file format"})

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