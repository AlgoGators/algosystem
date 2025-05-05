import os
import json
import webbrowser
import shutil

from .template.base_template import generate_html
from .utils.data_formatter import prepare_dashboard_data
from .utils.config_parser import validate_config


def generate_dashboard(engine, output_dir=None, open_browser=True, config_path=None):
    """
    Generate an HTML dashboard for the backtest results based on graph_config.json
    
    Parameters:
    -----------
    engine : Engine
        Backtesting engine with results
    output_dir : str, optional
        Directory where dashboard files will be saved. Defaults to ./dashboard/
    open_browser : bool, optional
        Whether to automatically open the dashboard in browser. Defaults to True
    config_path : str, optional
        Path to the graph configuration file. Defaults to utils/graph_config.json
        
    Returns:
    --------
    dashboard_path : str
        Path to the generated dashboard HTML file
    """
    # Check if backtest results are available
    if engine.results is None:
        raise ValueError("No backtest results available. Run the backtest first.")
    
    # Set default output directory
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "dashboard")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load graph configuration
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                 "utils", "graph_config.json")
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    # Validate configuration
    validate_config(config)
    
    # Prepare data for the dashboard
    dashboard_data = prepare_dashboard_data(engine, config)
    
    # Generate HTML content
    html_content = generate_html(engine, config, dashboard_data)
    
    # Write HTML file
    dashboard_path = os.path.join(output_dir, 'dashboard.html')
    with open(dashboard_path, 'w') as f:
        f.write(html_content)
    
    # Write data file
    data_path = os.path.join(output_dir, 'dashboard_data.json')
    with open(data_path, 'w') as f:
        json.dump(dashboard_data, f, indent=2)
    
    # Copy static files
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    
    # Create js directory
    js_dir = os.path.join(output_dir, 'js')
    os.makedirs(js_dir, exist_ok=True)
    
    # Copy main JS file
    main_js_path = os.path.join(static_dir, 'js', 'dashboard.js')
    shutil.copy(main_js_path, js_dir)
    
    # Copy chart factory JS file
    chart_factory_js_path = os.path.join(static_dir, 'js', 'chart_factory.js')
    shutil.copy(chart_factory_js_path, js_dir)
    
    # Copy metric factory JS file
    metric_factory_js_path = os.path.join(static_dir, 'js', 'metric_factory.js')
    shutil.copy(metric_factory_js_path, js_dir)
    
    # Create css directory
    css_dir = os.path.join(output_dir, 'css')
    os.makedirs(css_dir, exist_ok=True)
    
    # Copy CSS file
    css_path = os.path.join(static_dir, 'css', 'dashboard.css')
    shutil.copy(css_path, css_dir)
    
    # Open in browser if requested
    if open_browser:
        webbrowser.open('file://' + os.path.abspath(dashboard_path))
    
    return dashboard_path