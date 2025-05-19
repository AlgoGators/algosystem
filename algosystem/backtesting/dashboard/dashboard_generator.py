import json
import os
import shutil
import webbrowser

from .template.base_template import generate_html
from .utils.config_parser import validate_config
from .utils.data_formatter import prepare_dashboard_data


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
        Path to the graph configuration file. If None, will use the default config

    Returns:
    --------
    dashboard_path : str
        Path to the generated dashboard HTML file
    """
    # Check if backtest results are available
    if engine.results is None:
        # Try to run the backtest if not already run
        engine.run()

        if engine.results is None:
            raise ValueError("No backtest results available. Run the backtest first.")

    # Set default output directory
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "dashboard")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load graph configuration
    if config_path is None:
        # Check for a user config first
        user_config = os.path.join(
            os.path.expanduser("~"), ".algosystem", "dashboard_config.json"
        )
        if os.path.exists(user_config):
            print(f"Using user configuration from: {user_config}")
            with open(user_config, "r") as f:
                config = json.load(f)
        else:
            # Use default configuration
            from .utils.default_config import get_default_config

            config = get_default_config()
    else:
        # Use the specified configuration
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            # If the specified config doesn't exist, use default and create the file
            print(
                f"Warning: Configuration file {config_path} not found. Creating it with default configuration."
            )
            from .utils.default_config import get_default_config

            config = get_default_config()

            # Ensure directory exists for the config path
            os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)

            # Save the default config to the specified location
            with open(config_path, "w") as f:
                json.dump(config, f, indent=4)

    # Validate configuration
    validate_config(config)

    # Prepare data for the dashboard
    dashboard_data = prepare_dashboard_data(engine, config)

    # Generate HTML content
    html_content = generate_html(engine, config, dashboard_data)

    # Write HTML file
    dashboard_path = os.path.join(output_dir, "dashboard.html")
    with open(dashboard_path, "w") as f:
        f.write(html_content)

    # Write data file
    data_path = os.path.join(output_dir, "dashboard_data.json")
    with open(data_path, "w") as f:
        json.dump(dashboard_data, f, indent=2)

    # Create directories for static files
    js_dir = os.path.join(output_dir, "js")
    os.makedirs(js_dir, exist_ok=True)

    css_dir = os.path.join(output_dir, "css")
    os.makedirs(css_dir, exist_ok=True)

    # Copy static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")

    # Copy JS files
    js_files = ["dashboard.js", "chart_factory.js", "metric_factory.js"]
    for js_file in js_files:
        src_path = os.path.join(static_dir, "js", js_file)
        if os.path.exists(src_path):
            shutil.copy(src_path, js_dir)
        else:
            # Create minimum required JS files if they don't exist
            create_default_js_files(js_dir, js_file)

    # Copy CSS file
    css_path = os.path.join(static_dir, "css", "dashboard.css")
    if os.path.exists(css_path):
        shutil.copy(css_path, css_dir)
    else:
        # Create default CSS file if it doesn't exist
        create_default_css_file(css_dir)

    # Add configuration source information to the HTML file
    config_info = ""
    if config_path:
        config_info = f"<p>Configuration source: {os.path.basename(config_path)}</p>"
    else:
        user_config = os.path.join(
            os.path.expanduser("~"), ".algosystem", "dashboard_config.json"
        )
        if os.path.exists(user_config):
            config_info = "<p>Configuration source: User configuration</p>"
        else:
            config_info = "<p>Configuration source: Default configuration</p>"

    # Insert config info before the closing body tag
    with open(dashboard_path, "r") as f:
        html_content = f.read()

    html_content = html_content.replace(
        "</body>", f'<div class="config-info">{config_info}</div></body>'
    )

    with open(dashboard_path, "w") as f:
        f.write(html_content)

    # Open in browser if requested
    if open_browser:
        webbrowser.open("file://" + os.path.abspath(dashboard_path))

    return dashboard_path


def create_default_js_files(js_dir, file_name):
    """Create default JS files with minimal functionality if originals don't exist."""
    if file_name == "dashboard.js":
        content = """
/**
 * Dashboard - Main dashboard functionality
 */

// Global data object
let chartData;

/**
 * Initialize the dashboard
 */
function initDashboard() {
    // Load data
    fetch('dashboard_data.json')
        .then(response => response.json())
        .then(data => {
            // Store data globally
            chartData = data;
            
            // Initialize dashboard components
            createDashboard();
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
            document.body.innerHTML = `<div class="error-message">Error loading dashboard data: ${error.message}</div>`;
        });
}

/**
 * Create the dashboard
 */
function createDashboard() {
    // Update metadata in the header
    updateHeader();
    
    // Create metrics
    createMetrics();
    
    // Create charts
    createCharts();
}

/**
 * Update the dashboard header with metadata
 */
function updateHeader() {
    // Update title if needed
    const titleElement = document.querySelector('.dashboard-header h1');
    if (titleElement && chartData.metadata.title) {
        titleElement.textContent = chartData.metadata.title;
    }
    
    // Update date range
    const dateRangeElement = document.querySelector('.date-range');
    if (dateRangeElement) {
        dateRangeElement.textContent = `Backtest Period: ${chartData.metadata.start_date} to ${chartData.metadata.end_date}`;
    }
    
    // Update total return
    const totalReturnElement = document.querySelector('.header-summary h2');
    if (totalReturnElement) {
        const totalReturn = chartData.metadata.total_return;
        const sign = totalReturn >= 0 ? '+' : '';
        totalReturnElement.textContent = `${sign}${totalReturn.toFixed(2)}%`;
        totalReturnElement.className = totalReturn >= 0 ? 'positive-return' : 'negative-return';
    }
}

/**
 * Create metrics based on data
 */
function createMetrics() {
    // Check if metrics data is available
    if (!chartData.metrics) return;
    
    // Update each metric
    for (const metricId in chartData.metrics) {
        const metric = chartData.metrics[metricId];
        updateMetric(metricId, metric);
    }
}

/**
 * Create charts based on data
 */
function createCharts() {
    // Check if charts data is available
    if (!chartData.charts) return;
    
    // Create each chart
    for (const chartId in chartData.charts) {
        const chart = chartData.charts[chartId];
        createChart(chartId, chart);
    }
}

/**
 * Update a metric with data
 */
function updateMetric(metricId, metricData) {
    const element = document.getElementById(metricId);
    if (!element) return;
    
    // Format value based on type
    let formattedValue = metricData.value;
    let className = '';
    
    if (metricData.type === 'Percentage') {
        formattedValue = `${(metricData.value * 100).toFixed(2)}%`;
        className = metricData.value >= 0 ? 'positive' : 'negative';
    } else if (metricData.type === 'Value') {
        formattedValue = metricData.value.toFixed(2);
        className = metricData.value >= 0 ? 'positive' : 'negative';
    } else if (metricData.type === 'Currency') {
        formattedValue = `$${metricData.value.toFixed(2)}`;
        className = metricData.value >= 0 ? 'positive' : 'negative';
    }
    
    element.innerHTML = `<span class="${className}">${formattedValue}</span>`;
}

/**
 * Create a chart with data
 */
function createChart(chartId, chartData) {
    const container = document.getElementById(chartId);
    if (!container) return;
    
    // Create a simple fallback visualization if Chart.js is not available
    if (typeof Chart === 'undefined') {
        container.innerHTML = '<div style="text-align: center; padding: 20px;">Chart visualization not available.<br>Data is available in the dashboard_data.json file.</div>';
        return;
    }
    
    // Create a canvas element
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    
    // Create the chart based on type
    if (chartData.type === 'LineChart') {
        new Chart(canvas, {
            type: 'line',
            data: chartData.data,
            options: getChartOptions(chartData)
        });
    } else if (chartData.type === 'HeatmapTable') {
        // For heatmap tables, create a table instead of a canvas
        container.innerHTML = createHeatmapTable(chartData.data);
    }
}

/**
 * Get chart options based on configuration
 */
function getChartOptions(chartData) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            title: {
                display: true,
                text: chartData.title
            },
            legend: {
                display: true,
                position: 'top'
            }
        },
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'day',
                    displayFormats: {
                        day: 'MMM d, yyyy'
                    }
                },
                title: {
                    display: true,
                    text: 'Date'
                }
            },
            y: {
                title: {
                    display: true,
                    text: chartData.config?.y_axis_label || 'Value'
                }
            }
        }
    };
}

/**
 * Create a heatmap table from data
 */
function createHeatmapTable(data) {
    if (!data || !data.years || !data.months) {
        return '<div class="error-message">No data available for heatmap</div>';
    }
    
    let html = '<table class="heatmap-table">';
    
    // Add header row with months
    html += '<tr><th></th>';
    data.months.forEach(month => {
        html += `<th>${month}</th>`;
    });
    html += '</tr>';
    
    // Add rows for each year
    data.years.forEach(year => {
        html += `<tr><th>${year}</th>`;
        
        // Add cells for each month
        for (let month = 1; month <= 12; month++) {
            const key = `${year}-${month}`;
            const value = data.data[key];
            
            if (value !== undefined) {
                const formatted = (value * 100).toFixed(1) + '%';
                const colorClass = value >= 0 ? 'positive' : 'negative';
                const intensity = Math.min(Math.abs(value) * 10, 1);
                const style = value >= 0 
                    ? `background-color: rgba(46, 204, 113, ${intensity});` 
                    : `background-color: rgba(231, 76, 60, ${intensity});`;
                
                html += `<td style="${style}" class="${colorClass}">${formatted}</td>`;
            } else {
                html += '<td></td>';
            }
        }
        
        html += '</tr>';
    });
    
    html += '</table>';
    return html;
}

// Initialize dashboard when document is loaded
document.addEventListener('DOMContentLoaded', function() {
    initDashboard();
});
        """
    elif file_name == "chart_factory.js":
        content = """
/**
 * Chart Factory - Functions for creating various chart types
 */

/**
 * Create a line chart
 * @param {string} containerId - ID of the container element
 * @param {object} data - Chart data
 * @param {object} options - Chart options
 */
function createLineChart(containerId, data, options) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Clear existing content
    container.innerHTML = '';
    
    // Create canvas element
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    
    // Check if data is available
    if (!data || !data.labels || !data.datasets || data.labels.length === 0) {
        container.innerHTML = '<div class="error-message">No data available</div>';
        return;
    }
    
    // Create chart instance (requires Chart.js library)
    if (typeof Chart !== 'undefined') {
        new Chart(canvas, {
            type: 'line',
            data: data,
            options: options || {}
        });
    } else {
        container.innerHTML = '<div class="error-message">Chart.js library not loaded</div>';
    }
}

/**
 * Create a heatmap table
 * @param {string} containerId - ID of the container element
 * @param {object} data - Heatmap data
 */
function createHeatmapTable(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Clear existing content
    container.innerHTML = '';
    
    // Check if data is available
    if (!data || !data.years || !data.months || data.years.length === 0) {
        container.innerHTML = '<div class="error-message">No data available</div>';
        return;
    }
    
    // Create table element
    const table = document.createElement('table');
    table.className = 'heatmap-table';
    
    // Create header row
    const headerRow = document.createElement('tr');
    
    // Add empty corner cell
    const cornerCell = document.createElement('th');
    headerRow.appendChild(cornerCell);
    
    // Add month headers
    for (const month of data.months) {
        const cell = document.createElement('th');
        cell.textContent = month;
        headerRow.appendChild(cell);
    }
    
    table.appendChild(headerRow);
    
    // Create data rows
    for (const year of data.years) {
        const row = document.createElement('tr');
        
        // Add year header
        const yearCell = document.createElement('th');
        yearCell.textContent = year;
        row.appendChild(yearCell);
        
        // Add data cells
        for (let month = 1; month <= 12; month++) {
            const cell = document.createElement('td');
            const key = `${year}-${month}`;
            
            if (key in data.data) {
                const value = data.data[key];
                
                // Format value
                cell.textContent = formatAsPercentage(value);
                
                // Apply color scale
                applyHeatmapColor(cell, value);
            }
            
            row.appendChild(cell);
        }
        
        table.appendChild(row);
    }
    
    container.appendChild(table);
}

/**
 * Apply color to heatmap cell based on value
 * @param {HTMLElement} cell - Table cell element
 * @param {number} value - Cell value
 */
function applyHeatmapColor(cell, value) {
    if (value > 0.03) {
        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.8)';
        cell.style.color = 'white';
    } else if (value > 0.01) {
        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.5)';
    } else if (value > 0) {
        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.2)';
    } else if (value > -0.01) {
        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.2)';
    } else if (value > -0.03) {
        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.5)';
    } else {
        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.8)';
        cell.style.color = 'white';
    }
}

/**
 * Format value as percentage
 * @param {number} value - Value to format
 * @returns {string} - Formatted percentage
 */
function formatAsPercentage(value) {
    return `${(value * 100).toFixed(1)}%`;
}
        """
    elif file_name == "metric_factory.js":
        content = """
/**
 * Metric Factory - Functions for updating various metric types
 */

/**
 * Update a percentage metric
 * @param {string} metricId - ID of the metric element
 * @param {number} value - Metric value
 */
function updatePercentageMetric(metricId, value) {
    const element = document.getElementById(metricId);
    if (!element) return;
    
    // Format value
    const formattedValue = formatAsPercentage(value);
    
    // Determine class based on value
    const className = value >= 0 ? 'positive' : 'negative';
    
    // Update element
    element.innerHTML = `<span class="${className}">${formattedValue}</span>`;
}

/**
 * Update a value metric
 * @param {string} metricId - ID of the metric element
 * @param {number} value - Metric value
 */
function updateValueMetric(metricId, value) {
    const element = document.getElementById(metricId);
    if (!element) return;
    
    // Format value
    const formattedValue = formatValue(value);
    
    // Determine class based on value
    const className = value >= 0 ? 'positive' : 'negative';
    
    // Update element
    element.innerHTML = `<span class="${className}">${formattedValue}</span>`;
}

/**
 * Update a currency metric
 * @param {string} metricId - ID of the metric element
 * @param {number} value - Metric value
 */
function updateCurrencyMetric(metricId, value) {
    const element = document.getElementById(metricId);
    if (!element) return;
    
    // Format value
    const formattedValue = formatAsCurrency(value);
    
    // Determine class based on value
    const className = value >= 0 ? 'positive' : 'negative';
    
    // Update element
    element.innerHTML = `<span class="${className}">${formattedValue}</span>`;
}

/**
 * Format value
 * @param {number} value - Value to format
 * @returns {string} - Formatted value
 */
function formatValue(value) {
    return value.toFixed(2);
}

/**
 * Format value as currency
 * @param {number} value - Value to format
 * @returns {string} - Formatted currency
 */
function formatAsCurrency(value) {
    return `${value.toFixed(2)}`;
}
        """

    with open(os.path.join(js_dir, file_name), "w") as f:
        f.write(content)


def create_default_css_file(css_dir):
    """Create a default CSS file with basic styling if original doesn't exist."""
    content = """/**
 * Dashboard Styling
 */

/* Reset and base styles */
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f5f7fa;
    color: #333;
    line-height: 1.6;
}

/* Container */
.dashboard-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* Header styles */
.dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    background-color: #2c3e50;
    color: white;
    border-radius: 8px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.header-info h1 {
    font-size: 24px;
    margin-bottom: 5px;
}

.date-range {
    font-size: 14px;
    opacity: 0.8;
}

.header-summary h2 {
    font-size: 28px;
    font-weight: bold;
    margin-bottom: 5px;
}

.header-summary .label {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.8);
}

/* Metrics section */
.metrics-section {
    margin-bottom: 20px;
}

.metrics-row {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
}

.metric-card {
    background-color: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
}

.metric-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
}

.metric-title {
    font-size: 14px;
    color: #7f8c8d;
    margin-bottom: 10px;
}

.metric-value {
    font-size: 24px;
    font-weight: bold;
}

/* Charts section */
.charts-section {
    margin-bottom: 20px;
}

.charts-row {
    display: grid;
    gap: 20px;
    margin-bottom: 20px;
}

.chart-card {
    background-color: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
}

.chart-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
}

.chart-header {
    margin-bottom: 15px;
}

.chart-title {
    font-size: 18px;
    color: #333;
}

.chart-container {
    height: 300px;
    width: 100%;
    position: relative;
}

/* Heatmap table */
.heatmap-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}

.heatmap-table th,
.heatmap-table td {
    padding: 8px;
    text-align: center;
    border: 1px solid #ddd;
}

.heatmap-table th {
    background-color: #f2f2f2;
    font-weight: bold;
}

/* Value formatting */
.positive {
    color: #2ecc71;
}

.negative {
    color: #e74c3c;
}

.positive-return {
    color: #2ecc71;
}

.negative-return {
    color: #e74c3c;
}

/* Error messages */
.error-message {
    color: #e74c3c;
    text-align: center;
    padding: 20px;
    font-weight: bold;
}

/* Responsive design */
@media (max-width: 768px) {
    .dashboard-header {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .header-summary {
        margin-top: 15px;
    }
    
    .charts-row {
        grid-template-columns: 1fr !important;
    }
    
    .metrics-row {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 480px) {
    .dashboard-container {
        padding: 10px;
    }
    
    .dashboard-header {
        padding: 15px;
    }
    
    .header-info h1 {
        font-size: 20px;
    }
    
    .header-summary h2 {
        font-size: 24px;
    }
    
    .metric-value {
        font-size: 20px;
    }
    
    .chart-container {
        height: 250px;
    }
}"""

    with open(os.path.join(css_dir, "dashboard.css"), "w") as f:
        f.write(content)


def generate_standalone_dashboard(engine, output_path=None, config_path=None):
    """
    Generate a completely standalone HTML dashboard with no external dependencies.
    The entire dashboard including all data, styles, and JavaScript is embedded
    in a single HTML file that can be viewed without a web server.

    Parameters:
    -----------
    engine : Engine
        Backtesting engine with results
    output_path : str, optional
        Path where the standalone HTML file will be saved.
        Defaults to './standalone_dashboard.html'
    config_path : str, optional
        Path to a custom dashboard configuration file

    Returns:
    --------
    output_path : str
        Path to the generated standalone HTML file
    """
    import json
    import os
    from datetime import datetime

    # Check if backtest results are available
    if engine.results is None:
        # Try to run the backtest if not already run
        engine.run()

        if engine.results is None:
            raise ValueError("No backtest results available. Run the backtest first.")

    # Set default output path if not provided
    if output_path is None:
        output_path = os.path.join(os.getcwd(), "standalone_dashboard.html")

    # Ensure the output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    # Determine which configuration to use
    config = None
    config_source = "Default configuration"

    if config_path is not None:
        # User specified a configuration file
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                config_source = (
                    f"Custom configuration from {os.path.basename(config_path)}"
                )
                print(f"Using configuration from: {config_path}")
            except Exception as e:
                print(
                    f"Warning: Failed to load configuration from {config_path}: {str(e)}"
                )
                print("Using default configuration instead.")
                config = None
        else:
            print(f"Warning: Configuration file {config_path} not found.")
            print("Using default configuration instead.")

    if config is None:
        # Check for user configuration in the home directory
        user_config_path = os.path.join(
            os.path.expanduser("~"), ".algosystem", "dashboard_config.json"
        )
        if os.path.exists(user_config_path):
            try:
                with open(user_config_path, "r") as f:
                    config = json.load(f)
                config_source = (
                    f"User configuration from {os.path.basename(user_config_path)}"
                )
                print(f"Using user configuration from: {user_config_path}")
            except Exception as e:
                print(f"Warning: Failed to load user configuration: {str(e)}")
                print("Using default configuration instead.")
                config = None

    if config is None:
        # Use default configuration
        from .utils.default_config import get_default_config

        config = get_default_config()
        print("Using default dashboard configuration")

    # Prepare dashboard data
    from .utils.data_formatter import prepare_dashboard_data

    dashboard_data = prepare_dashboard_data(engine, config)

    # Include data generation timestamp
    generation_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dashboard_data["metadata"]["generation_time"] = generation_time

    # Create the standalone HTML content with embedded data, CSS, and JavaScript
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dashboard_data["metadata"]["title"]} - AlgoSystem Dashboard</title>
    
    <!-- Required libraries from CDN -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-adapter-moment/1.0.1/chartjs-adapter-moment.min.js"></script>
    
    <style>
    /* Dashboard Styles */
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }}

    body {{
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background-color: #f5f7fa;
        color: #333;
        line-height: 1.6;
        padding: 20px;
    }}

    .dashboard-container {{
        max-width: 1200px;
        margin: 0 auto;
        background-color: white;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        padding: 30px;
    }}

    .dashboard-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 20px;
        background-color: #2c3e50;
        color: white;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}

    .header-info h1 {{
        font-size: 24px;
        margin-bottom: 5px;
    }}

    .date-range {{
        font-size: 14px;
        opacity: 0.8;
    }}

    .header-summary {{
        text-align: right;
    }}

    .header-summary h2 {{
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 5px;
    }}

    .header-summary .label {{
        font-size: 14px;
        color: rgba(255, 255, 255, 0.8);
    }}

    .metrics-section {{
        margin-bottom: 30px;
    }}

    .metrics-row {{
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
    }}

    .metric-card {{
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }}

    .metric-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }}

    .metric-title {{
        font-size: 14px;
        color: #7f8c8d;
        margin-bottom: 10px;
    }}

    .metric-value {{
        font-size: 24px;
        font-weight: bold;
    }}

    .charts-section {{
        margin-bottom: 30px;
    }}

    .charts-row {{
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        margin-bottom: 20px;
    }}

    .chart-card {{
        background-color: white;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
    }}

    .chart-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }}

    .chart-header {{
        margin-bottom: 15px;
    }}

    .chart-title {{
        font-size: 18px;
        color: #333;
    }}

    .chart-container {{
        height: 300px;
        width: 100%;
        position: relative;
    }}

    .heatmap-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 14px;
    }}

    .heatmap-table th,
    .heatmap-table td {{
        padding: 8px;
        text-align: center;
        border: 1px solid #ddd;
    }}

    .heatmap-table th {{
        background-color: #f2f2f2;
        font-weight: bold;
    }}

    .positive {{
        color: #2ecc71;
    }}

    .negative {{
        color: #e74c3c;
    }}

    .positive-return {{
        color: #2ecc71;
    }}

    .negative-return {{
        color: #e74c3c;
    }}

    .error-message {{
        color: #e74c3c;
        text-align: center;
        padding: 20px;
        font-weight: bold;
    }}

    .export-actions {{
        text-align: right;
        margin-bottom: 20px;
    }}

    .export-button {{
        background-color: #3498db;
        color: white;
        border: none;
        padding: 8px 15px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
    }}

    .export-button:hover {{
        background-color: #2980b9;
    }}

    .dashboard-footer {{
        margin-top: 30px;
        text-align: center;
        color: #7f8c8d;
        font-size: 12px;
        border-top: 1px solid #eee;
        padding-top: 20px;
    }}

    @media print {{
        body {{
            padding: 0;
            background-color: white;
        }}
        
        .dashboard-container {{
            box-shadow: none;
            max-width: 100%;
            padding: 0;
        }}
        
        .export-actions {{
            display: none;
        }}
    }}

    @media (max-width: 768px) {{
        .dashboard-header {{
            flex-direction: column;
            align-items: flex-start;
        }}
        
        .header-summary {{
            margin-top: 15px;
            text-align: left;
        }}
        
        .charts-row {{
            grid-template-columns: 1fr;
        }}
    }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="export-actions">
            <button class="export-button" onclick="window.print()">Print Dashboard</button>
            <button class="export-button" onclick="exportToPDF()">Export as PDF</button>
        </div>
        
        <!-- Header -->
        <header class="dashboard-header">
            <div class="header-info">
                <h1>{dashboard_data["metadata"]["title"]}</h1>
                <div class="date-range">Backtest Period: {dashboard_data["metadata"]["start_date"]} to {dashboard_data["metadata"]["end_date"]}</div>
            </div>
            <div class="header-summary">
                <h2 class="{("positive-return" if dashboard_data["metadata"]["total_return"] >= 0 else "negative-return")}">{"+" if dashboard_data["metadata"]["total_return"] >= 0 else ""}{dashboard_data["metadata"]["total_return"]:.2f}%</h2>
                <p class="label">Total Return</p>
            </div>
        </header>
        
        <!-- Metrics Section -->
        <section class="metrics-section">
            <div class="metrics-row" id="metrics-container">
                <!-- Metrics will be added here by JavaScript -->
            </div>
        </section>
        
        <!-- Charts Section -->
        <section class="charts-section" id="charts-section">
            <!-- Charts will be added here by JavaScript -->
        </section>
        
        <!-- Footer -->
        <div class="dashboard-footer">
            <p>Generated by AlgoSystem Dashboard on {generation_time}</p>
            <p>Configuration: {config_source}</p>
        </div>
    </div>
    
    <script>
    // Embedded dashboard data
    const dashboardData = {json.dumps(dashboard_data)};
    
    // Utility functions
    function formatAsPercentage(value) {{
        return (value * 100).toFixed(2) + '%';
    }}
    
    function formatValue(value) {{
        return value.toFixed(2);
    }}
    
    function formatAsCurrency(value) {{
        return '$' + value.toFixed(2);
    }}
    
    // Function to create metrics
    function createMetrics() {{
        const container = document.getElementById('metrics-container');
        if (!container) return;
        
        for (const metricId in dashboardData.metrics) {{
            const metric = dashboardData.metrics[metricId];
            
            const card = document.createElement('div');
            card.className = 'metric-card';
            
            const title = document.createElement('div');
            title.className = 'metric-title';
            title.textContent = metric.title;
            
            const value = document.createElement('div');
            value.className = 'metric-value';
            
            let formattedValue;
            let className;
            
            if (metric.type === 'Percentage') {{
                formattedValue = formatAsPercentage(metric.value / 100); // Convert from percentage to decimal
                className = metric.value >= 0 ? 'positive' : 'negative';
            }} else if (metric.type === 'Value') {{
                formattedValue = formatValue(metric.value);
                className = metric.value >= 0 ? 'positive' : 'negative';
            }} else if (metric.type === 'Currency') {{
                formattedValue = formatAsCurrency(metric.value);
                className = metric.value >= 0 ? 'positive' : 'negative';
            }} else {{
                formattedValue = metric.value;
                className = '';
            }}
            
            value.innerHTML = `<span class="${{className}}">${{formattedValue}}</span>`;
            
            card.appendChild(title);
            card.appendChild(value);
            
            container.appendChild(card);
        }}
    }}
    
    // Function to create charts
    function createCharts() {{
        const chartsSection = document.getElementById('charts-section');
        if (!chartsSection) return;
        
        // Group charts by row
        const chartsByRow = {{}};
        
        for (const chartId in dashboardData.charts) {{
            const chart = dashboardData.charts[chartId];
            const row = chart.position.row;
            
            if (!chartsByRow[row]) {{
                chartsByRow[row] = [];
            }}
            
            chartsByRow[row].push(chart);
        }}
        
        // Create chart rows
        const sortedRows = Object.keys(chartsByRow).sort((a, b) => parseInt(a) - parseInt(b));
        
        for (const row of sortedRows) {{
            const charts = chartsByRow[row];
            
            const chartsRow = document.createElement('div');
            chartsRow.className = 'charts-row';
            
            // Sort charts by column
            charts.sort((a, b) => a.position.col - b.position.col);
            
            // Add charts to row
            for (const chart of charts) {{
                const chartCard = createChartCard(chart);
                chartsRow.appendChild(chartCard);
            }}
            
            chartsSection.appendChild(chartsRow);
        }}
    }}
    
    // Function to create a chart card
    function createChartCard(chart) {{
        const card = document.createElement('div');
        card.className = 'chart-card';
        
        const header = document.createElement('div');
        header.className = 'chart-header';
        
        const title = document.createElement('h3');
        title.className = 'chart-title';
        title.textContent = chart.title;
        
        header.appendChild(title);
        card.appendChild(header);
        
        const chartContainer = document.createElement('div');
        chartContainer.className = 'chart-container';
        chartContainer.id = chart.id;
        card.appendChild(chartContainer);
        
        return card;
    }}
    
    // Function to render charts after DOM is loaded
    function renderCharts() {{
        // For each chart in the dashboard data
        for (const chartId in dashboardData.charts) {{
            const chart = dashboardData.charts[chartId];
            const container = document.getElementById(chart.id);
            
            if (!container) continue;
            
            if (chart.type === 'LineChart') {{
                renderLineChart(container, chart);
            }} else if (chart.type === 'HeatmapTable') {{
                renderHeatmapTable(container, chart);
            }}
        }}
    }}
    
    // Function to render a line chart
    function renderLineChart(container, chartData) {{
        const canvas = document.createElement('canvas');
        container.appendChild(canvas);
        
        // Check if data is available
        if (!chartData.data || !chartData.data.datasets || chartData.data.datasets.length === 0) {{
            container.innerHTML = '<div class="error-message">No data available</div>';
            return;
        }}
        
        // Create options
        const options = {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                legend: {{
                    display: true,
                    position: 'top',
                }},
                tooltip: {{
                    mode: 'index',
                    intersect: false
                }}
            }},
            scales: {{
                x: {{
                    type: 'time',
                    time: {{
                        unit: 'month',
                        displayFormats: {{
                            month: 'MMM YYYY'
                        }}
                    }},
                    title: {{
                        display: true,
                        text: 'Date'
                    }}
                }},
                y: {{
                    title: {{
                        display: true,
                        text: chartData.config && chartData.config.y_axis_label ? chartData.config.y_axis_label : 'Value'
                    }}
                }}
            }}
        }};
        
        // Add percentage formatting if needed
        if (chartData.config && chartData.config.percentage_format) {{
            options.plugins.tooltip.callbacks = {{
                label: function(context) {{
                    let label = context.dataset.label || '';
                    if (label) {{
                        label += ': ';
                    }}
                    if (context.parsed.y !== null) {{
                        label += formatAsPercentage(context.parsed.y);
                    }}
                    return label;
                }}
            }};
            
            options.scales.y.ticks = {{
                callback: function(value) {{
                    return formatAsPercentage(value);
                }}
            }};
        }}
        
        // Create chart
        new Chart(canvas, {{
            type: 'line',
            data: chartData.data,
            options: options
        }});
    }}
    
    // Function to render a heatmap table
    function renderHeatmapTable(container, chartData) {{
        // Check if data is available
        if (!chartData.data || !chartData.data.years || !chartData.data.months) {{
            container.innerHTML = '<div class="error-message">No data available</div>';
            return;
        }}
        
        // Create table
        const table = document.createElement('table');
        table.className = 'heatmap-table';
        
        // Create header row
        const headerRow = document.createElement('tr');
        
        // Add empty corner cell
        const cornerCell = document.createElement('th');
        headerRow.appendChild(cornerCell);
        
        // Add month headers
        for (const month of chartData.data.months) {{
            const cell = document.createElement('th');
            cell.textContent = month;
            headerRow.appendChild(cell);
        }}
        
        table.appendChild(headerRow);
        
        // Create data rows
        for (const year of chartData.data.years) {{
            const row = document.createElement('tr');
            
            // Add year header
            const yearCell = document.createElement('th');
            yearCell.textContent = year;
            row.appendChild(yearCell);
            
            // Add data cells
            for (let month = 1; month <= 12; month++) {{
                const cell = document.createElement('td');
                const key = `${{year}}-${{month}}`;
                
                if (chartData.data.data[key] !== undefined) {{
                    const value = chartData.data.data[key];
                    
                    // Format value
                    cell.textContent = formatAsPercentage(value);
                    
                    // Apply color scale
                    if (value > 0.03) {{
                        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.8)';
                        cell.style.color = 'white';
                    }} else if (value > 0.01) {{
                        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.5)';
                    }} else if (value > 0) {{
                        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.2)';
                    }} else if (value > -0.01) {{
                        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.2)';
                    }} else if (value > -0.03) {{
                        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.5)';
                    }} else {{
                        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.8)';
                        cell.style.color = 'white';
                    }}
                }}
                
                row.appendChild(cell);
            }}
            
            table.appendChild(row);
        }}
        
        container.appendChild(table);
    }}
    
    // Function to export to PDF
    function exportToPDF() {{
        // Alert that we're using print for PDF export
        alert('To save as PDF, use the Print dialog and select "Save as PDF" as the destination.');
        window.print();
    }}
    
    // Initialize dashboard when document is ready
    document.addEventListener('DOMContentLoaded', function() {{
        createMetrics();
        createCharts();
        // Wait a moment for DOM to update before rendering charts
        setTimeout(renderCharts, 100);
    }});
    </script>
</body>
</html>
"""

    # Write to output file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Standalone dashboard generated successfully at: {output_path}")
    return output_path
