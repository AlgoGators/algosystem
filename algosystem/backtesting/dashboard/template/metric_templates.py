def generate_metric_html(metric_config, metric_data):
    """
    Generate HTML for a metric component

    Parameters:
    -----------
    metric_config : dict
        Metric configuration
    metric_data : dict
        Metric data

    Returns:
    --------
    str
        HTML for the metric component
    """
    metric_id = metric_config["id"]
    metric_title = metric_config["title"]
    metric_type = metric_config["type"]
    metric_value = metric_data.get("value", 0)

    # Determine the value format
    value_html = format_metric_value(metric_value, metric_type)

    # Base metric card
    metric_html = f"""
<div class="metric-card" data-metric-id="{metric_id}" data-metric-type="{metric_type}">
    <div class="metric-content">
        <h3 class="metric-title">{metric_title}</h3>
        <div id="{metric_id}" class="metric-value">{value_html}</div>
    </div>
</div>
"""

    return metric_html


def format_metric_value(value, metric_type):
    """
    Format a metric value based on its type

    Parameters:
    -----------
    value : float
        Metric value
    metric_type : str
        Metric type

    Returns:
    --------
    str
        Formatted metric value
    """
    if metric_type == "Percentage":
        # Format as percentage
        formatted_value = f"{value:.2f}%"

        # Add class based on sign
        sign_class = "positive" if value >= 0 else "negative"

        return f'<span class="{sign_class}">{formatted_value}</span>'

    elif metric_type == "Value":
        # Format as number
        formatted_value = f"{value:.2f}"

        # Add class based on sign
        sign_class = "positive" if value >= 0 else "negative"

        return f'<span class="{sign_class}">{formatted_value}</span>'

    elif metric_type == "Currency":
        # Format as currency
        formatted_value = f"${value:,.2f}"

        # Add class based on sign
        sign_class = "positive" if value >= 0 else "negative"

        return f'<span class="{sign_class}">{formatted_value}</span>'

    else:
        # Default format
        return f"{value}"


def generate_percentage_metric_js(metric_id, metric_data):
    """
    Generate JavaScript for a percentage metric

    Parameters:
    -----------
    metric_id : str
        Metric ID
    metric_data : dict
        Metric data

    Returns:
    --------
    str
        JavaScript for the percentage metric
    """
    # Generate JavaScript
    js = f"""
// Update percentage metric: {metric_id}
updatePercentageMetric(
    '{metric_id}',
    chartData.metrics['{metric_id}'].value
);
"""

    return js


def generate_value_metric_js(metric_id, metric_data):
    """
    Generate JavaScript for a value metric

    Parameters:
    -----------
    metric_id : str
        Metric ID
    metric_data : dict
        Metric data

    Returns:
    --------
    str
        JavaScript for the value metric
    """
    # Generate JavaScript
    js = f"""
// Update value metric: {metric_id}
updateValueMetric(
    '{metric_id}',
    chartData.metrics['{metric_id}'].value
);
"""

    return js


def generate_currency_metric_js(metric_id, metric_data):
    """
    Generate JavaScript for a currency metric

    Parameters:
    -----------
    metric_id : str
        Metric ID
    metric_data : dict
        Metric data

    Returns:
    --------
    str
        JavaScript for the currency metric
    """
    # Generate JavaScript
    js = f"""
// Update currency metric: {metric_id}
updateCurrencyMetric(
    '{metric_id}',
    chartData.metrics['{metric_id}'].value
);
"""

    return js
