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
        # Use default configuration
        from .utils.default_config import get_default_config
        config = get_default_config()
    else:
        # Load configuration from file
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
    
    # Create directories for static files
    js_dir = os.path.join(output_dir, 'js')
    os.makedirs(js_dir, exist_ok=True)
    
    css_dir = os.path.join(output_dir, 'css')
    os.makedirs(css_dir, exist_ok=True)
    
    # Copy static files
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    
    # Copy JS files
    js_files = ['dashboard.js', 'chart_factory.js', 'metric_factory.js']
    for js_file in js_files:
        src_path = os.path.join(static_dir, 'js', js_file)
        if os.path.exists(src_path):
            shutil.copy(src_path, js_dir)
        else:
            # Create minimum required JS files if they don't exist
            create_default_js_files(js_dir, js_file)
    
    # Copy CSS file
    css_path = os.path.join(static_dir, 'css', 'dashboard.css')
    if os.path.exists(css_path):
        shutil.copy(css_path, css_dir)
    else:
        # Create default CSS file if it doesn't exist
        create_default_css_file(css_dir)
    
    # Open in browser if requested
    if open_browser:
        webbrowser.open('file://' + os.path.abspath(dashboard_path))
    
    return dashboard_path

def create_default_js_files(js_dir, file_name):
    """Create default JS files with minimal functionality if originals don't exist."""
    if file_name == 'dashboard.js':
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
    elif file_name == 'chart_factory.js':
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
    elif file_name == 'metric_factory.js':
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
    
    with open(os.path.join(js_dir, file_name), 'w') as f:
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
    
    with open(os.path.join(css_dir, 'dashboard.css'), 'w') as f:
        f.write(content)