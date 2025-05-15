def generate_chart_html(chart_config, chart_data):
    """
    Generate HTML for a chart component

    Parameters:
    -----------
    chart_config : dict
        Chart configuration
    chart_data : dict
        Chart data

    Returns:
    --------
    str
        HTML for the chart component
    """
    chart_id = chart_config["id"]
    chart_title = chart_config["title"]
    chart_type = chart_config["type"]

    # Base chart container
    chart_html = f"""
<div class="chart-card" data-chart-id="{chart_id}" data-chart-type="{chart_type}">
    <div class="chart-header">
        <h3 class="chart-title">{chart_title}</h3>
    </div>
    <div class="chart-body">
        <div id="{chart_id}" class="chart-container"></div>
    </div>
</div>
"""

    return chart_html


def generate_line_chart_js(chart_id, chart_data, chart_config):
    """
    Generate JavaScript for a line chart

    Parameters:
    -----------
    chart_id : str
        Chart ID
    chart_data : dict
        Chart data
    chart_config : dict
        Chart configuration

    Returns:
    --------
    str
        JavaScript for the line chart
    """
    # Extract configuration
    y_axis_label = chart_config.get("config", {}).get("y_axis_label", "Value")
    percentage_format = chart_config.get("config", {}).get("percentage_format", False)

    # Generate JavaScript
    js = f"""
// Create chart: {chart_id}
createLineChart(
    '{chart_id}',
    chartData.charts['{chart_id}'].data,
    {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{
                display: true,
                position: 'top',
            }},
            tooltip: {{
                mode: 'index',
                intersect: false,
                callbacks: {{
                    label: function(context) {{
                        let label = context.dataset.label || '';
                        if (label) {{
                            label += ': ';
                        }}
                        if (context.parsed.y !== null) {{
                            label += {"formatAsPercentage(context.parsed.y)" if percentage_format else "formatValue(context.parsed.y)"};
                        }}
                        return label;
                    }}
                }}
            }}
        }},
        elements: {{
            point: {{
                radius: 0,
                hoverRadius: 3,
                hitRadius: 10,
                borderWidth: 0,
                hoverBorderWidth: 1
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
                    text: '{y_axis_label}'
                }},
                {"ticks: { callback: function(value) { return formatAsPercentage(value); } }," if percentage_format else ""}
            }}
        }}
    }}
);
"""

    return js


def generate_heatmap_table_js(chart_id, chart_data, chart_config):
    """
    Generate JavaScript for a heatmap table

    Parameters:
    -----------
    chart_id : str
        Chart ID
    chart_data : dict
        Chart data
    chart_config : dict
        Chart configuration

    Returns:
    --------
    str
        JavaScript for the heatmap table
    """
    # Generate JavaScript
    js = f"""
// Create heatmap table: {chart_id}
createHeatmapTable(
    '{chart_id}',
    chartData.charts['{chart_id}'].data
);
"""

    return js
