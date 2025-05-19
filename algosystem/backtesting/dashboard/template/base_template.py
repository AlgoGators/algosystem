from ..utils.config_parser import get_component_rows
from .chart_templates import generate_chart_html
from .metric_templates import generate_metric_html


def generate_html(engine, config, dashboard_data):
    """
    Generate HTML for the dashboard

    Parameters:
    -----------
    engine : Engine
        Backtesting engine with results
    config : dict
        Dashboard configuration
    dashboard_data : dict
        Formatted dashboard data

    Returns:
    --------
    str
        Complete HTML content for the dashboard
    """
    # Generate header
    header_html = generate_header_html(dashboard_data)

    # Generate metrics section
    metrics_html = generate_metrics_section(config, dashboard_data)

    # Generate charts section
    charts_html = generate_charts_section(config, dashboard_data)

    # Assemble the complete HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{config["layout"]["title"]}</title>
    <link rel="stylesheet" href="css/dashboard.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-adapter-moment/1.0.1/chartjs-adapter-moment.min.js"></script>
    <script src="js/chart_factory.js"></script>
    <script src="js/metric_factory.js"></script>
    <script src="js/dashboard.js"></script>
</head>
<body>
    <div class="dashboard-container">
        {header_html}
        {metrics_html}
        {charts_html}
    </div>
    
    <script>
        // Initialize dashboard when document is loaded
        document.addEventListener('DOMContentLoaded', function() {{
            initDashboard();
        }});
    </script>
</body>
</html>
"""

    return html


def generate_header_html(dashboard_data):
    """
    Generate HTML for the dashboard header

    Parameters:
    -----------
    dashboard_data : dict
        Dashboard data

    Returns:
    --------
    str
        HTML for the header section
    """
    metadata = dashboard_data["metadata"]
    total_return = metadata["total_return"]
    total_return_class = "positive-return" if total_return >= 0 else "negative-return"
    total_return_sign = "+" if total_return >= 0 else ""

    header_html = f"""
<header class="dashboard-header">
    <div class="header-info">
        <h1>{metadata["title"]}</h1>
        <div class="date-range">Backtest Period: {metadata["start_date"]} to {metadata["end_date"]}</div>
    </div>
    <div class="header-summary">
        <h2 class="{total_return_class}">{total_return_sign}{total_return:.2f}%</h2>
        <p class="label">Total Return</p>
    </div>
</header>
"""

    return header_html


def generate_metrics_section(config, dashboard_data):
    """
    Generate HTML for the metrics section

    Parameters:
    -----------
    config : dict
        Dashboard configuration
    dashboard_data : dict
        Dashboard data

    Returns:
    --------
    str
        HTML for the metrics section
    """
    metrics_html = '<section class="metrics-section">'

    # Get metrics grouped by row
    metrics_rows = get_component_rows(config["metrics"])

    # Generate HTML for each row
    for row in sorted(metrics_rows.keys()):
        metrics_row = metrics_rows[row]
        metrics_html += f'<div class="metrics-row" data-row="{row}">'
        # Generate HTML for each metric in this row
        for metric_config in metrics_row:
            metric_id = metric_config["id"]
            metric_data = dashboard_data["metrics"].get(metric_id, {})

            # Skip if metric data is not available
            if not metric_data:
                continue

            # Generate HTML for this metric
            metric_html = generate_metric_html(metric_config, metric_data)
            metrics_html += metric_html

        metrics_html += "</div>"

    metrics_html += "</section>"

    return metrics_html


def generate_charts_section(config, dashboard_data):
    """
    Generate HTML for the charts section

    Parameters:
    -----------
    config : dict
        Dashboard configuration
    dashboard_data : dict
        Dashboard data

    Returns:
    --------
    str
        HTML for the charts section
    """
    charts_html = '<section class="charts-section">'

    # Get charts grouped by row
    charts_rows = get_component_rows(config["charts"])

    # Get maximum number of columns
    max_cols = config["layout"]["max_cols"]

    # Generate HTML for each row
    for row in sorted(charts_rows.keys()):
        charts_row = charts_rows[row]
        charts_html += f'<div class="charts-row" data-row="{row}" style="grid-template-columns: repeat({max_cols}, 1fr);">'

        # Generate HTML for each chart in this row
        for chart_config in charts_row:
            chart_id = chart_config["id"]
            chart_data = dashboard_data["charts"].get(chart_id, {})

            # Skip if chart data is not available
            if not chart_data:
                continue

            # Generate HTML for this chart
            chart_html = generate_chart_html(chart_config, chart_data)
            charts_html += chart_html

        charts_html += "</div>"

    charts_html += "</section>"

    return charts_html
