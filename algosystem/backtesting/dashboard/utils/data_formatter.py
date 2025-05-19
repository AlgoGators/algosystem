from datetime import datetime

import numpy as np
import pandas as pd


def prepare_dashboard_data(engine, config):
    """
    Prepare data for the dashboard based on configuration

    Parameters:
    -----------
    engine : Engine
        Backtesting engine with results
    config : dict
        Dashboard configuration

    Returns:
    --------
    dict
        Formatted data for the dashboard
    """
    if engine.results is None:
        raise ValueError("No backtest results available. Run the backtest first.")

    # Prepare basic data
    dashboard_data = {
        "metadata": {
            "title": config["layout"]["title"],
            "start_date": engine.start_date.strftime("%Y-%m-%d"),
            "end_date": engine.end_date.strftime("%Y-%m-%d"),
            "total_return": float(engine.results.get("returns", 0))
            * 100,  # Convert to percentage
            "initial_capital": float(engine.results.get("initial_capital", 0)),
            "final_capital": float(engine.results.get("final_capital", 0)),
            "run_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": prepare_metrics_data(engine, config),
        "charts": prepare_charts_data(engine, config),
    }

    return dashboard_data


def prepare_metrics_data(engine, config):
    """
    Prepare metrics data for the dashboard

    Parameters:
    -----------
    engine : Engine
        Backtesting engine with results
    config : dict
        Dashboard configuration

    Returns:
    --------
    dict
        Formatted metrics data
    """
    # Extract metrics and ensure they're serializable
    metrics = {}
    for key, value in engine.results.get("metrics", {}).items():
        if isinstance(value, (np.integer, np.floating, np.bool_)):
            metrics[key] = value.item()  # Convert NumPy types to Python native types
        else:
            metrics[key] = value

    # Format metrics based on configuration
    formatted_metrics = {}
    for metric_config in config["metrics"]:
        metric_id = metric_config["id"]
        value_key = metric_config["value_key"]

        # Get the value if available, else use 0
        value = metrics.get(value_key, 0)

        # Format based on metric type
        if metric_config["type"] == "Percentage":
            formatted_value = value * 100  # Convert to percentage
        else:
            formatted_value = value

        # Store the formatted metric
        formatted_metrics[metric_id] = {
            "id": metric_id,
            "title": metric_config["title"],
            "type": metric_config["type"],
            "value": formatted_value,
            "position": metric_config["position"],
        }

    return formatted_metrics


def prepare_charts_data(engine, config):
    """
    Prepare chart data for the dashboard

    Parameters:
    -----------
    engine : Engine
        Backtesting engine with results
    config : dict
        Dashboard configuration

    Returns:
    --------
    dict
        Formatted chart data
    """
    # Initialize charts data
    charts_data = {}

    # Get available data series from both results and plots
    data_series = {}

    # Add main equity series
    data_series["equity"] = engine.results.get("equity", None)

    # Add all plot data
    plots_data = engine.results.get("plots", {})

    # Debug: Print available plot keys
    print(f"Debug: Available plot keys: {list(plots_data.keys())}")

    # Map the plot data to expected data keys
    data_series.update(
        {
            "drawdown": plots_data.get("drawdown_series", None),
            "rolling_sharpe": plots_data.get("rolling_sharpe", None),
            "rolling_sortino": plots_data.get("rolling_sortino", None),
            "rolling_volatility": plots_data.get("rolling_volatility", None),
            "rolling_var": plots_data.get("rolling_var", None),
            "monthly_returns": plots_data.get("monthly_returns", None),
            "benchmark_comparison": plots_data.get("benchmark_equity_curve", None),
            "benchmark_equity_curve": plots_data.get("benchmark_equity_curve", None),
            "relative_performance": plots_data.get("relative_performance", None),
        }
    )

    # Prepare each chart's data based on configuration
    for chart_config in config["charts"]:
        chart_id = chart_config["id"]
        data_key = chart_config["data_key"]

        print(f"Debug: Processing chart '{chart_id}' with data_key '{data_key}'")

        # Get the data series
        series_data = data_series.get(data_key, None)

        # Check if data exists and is not empty
        if series_data is None:
            print(f"Debug: No data found for '{data_key}', skipping chart '{chart_id}'")
            continue

        # Check if it's a pandas Series and if it's empty
        if isinstance(series_data, pd.Series) and series_data.empty:
            print(f"Debug: Data for '{data_key}' is empty, skipping chart '{chart_id}'")
            continue

        # Format data based on chart type
        try:
            if chart_config["type"] == "LineChart":
                chart_data = format_line_chart_data(series_data, chart_config)
            elif chart_config["type"] == "HeatmapTable":
                chart_data = format_heatmap_table_data(series_data, chart_config)
            else:
                print(
                    f"Debug: Unsupported chart type '{chart_config['type']}' for chart '{chart_id}'"
                )
                continue
        except Exception as e:
            print(f"Debug: Error formatting data for chart '{chart_id}': {str(e)}")
            continue

        # Add to charts data
        charts_data[chart_id] = {
            "id": chart_id,
            "title": chart_config["title"],
            "type": chart_config["type"],
            "data": chart_data,
            "config": chart_config["config"],
            "position": chart_config["position"],
        }

        print(f"Debug: Successfully added chart '{chart_id}'")

    return charts_data


def format_line_chart_data(series, chart_config):
    """
    Format data for a line chart

    Parameters:
    -----------
    series : pd.Series
        Time series data
    chart_config : dict
        Chart configuration

    Returns:
    --------
    dict
        Formatted line chart data
    """
    # Check if series is None or empty
    if series is None:
        return {"labels": [], "datasets": []}

    if isinstance(series, pd.Series) and series.empty:
        return {"labels": [], "datasets": []}

    # Format labels (dates)
    labels = []
    data = []

    for date, value in series.items():
        # Format date
        date_str = date.strftime("%Y-%m-%d") if hasattr(date, "strftime") else str(date)
        labels.append(date_str)

        # Format value
        if isinstance(value, (np.integer, np.floating)):
            value_float = float(value.item())
        else:
            value_float = float(value) if pd.notna(value) else None

        data.append(value_float)

    # Create dataset with no dots
    dataset = {
        "label": chart_config["title"],
        "data": data,
        "borderColor": "#2ecc71",  # Default color - can be overridden in future
        "backgroundColor": "rgba(46, 204, 113, 0.1)",
        "fill": True,
        "tension": 0.1,
        "pointRadius": 0,
        "pointHoverRadius": 3,
        "pointHitRadius": 10,
        "pointBorderWidth": 0,
        "pointHoverBorderWidth": 1,
    }

    return {"labels": labels, "datasets": [dataset]}


def format_heatmap_table_data(series, chart_config):
    """
    Format data for a heatmap table

    Parameters:
    -----------
    series : pd.Series
        Monthly returns data
    chart_config : dict
        Chart configuration

    Returns:
    --------
    dict
        Formatted heatmap table data
    """
    # Check if series is None or empty
    if series is None:
        return {"years": [], "months": [], "data": {}}

    if isinstance(series, pd.Series) and series.empty:
        return {"years": [], "months": [], "data": {}}

    # Extract data
    years = set()
    monthly_data = {}

    for date, value in series.items():
        # Extract year and month
        year = date.year
        month = date.month

        # Add year to set
        years.add(year)

        # Format value
        if isinstance(value, (np.integer, np.floating)):
            value_float = float(value.item())
        else:
            value_float = float(value) if pd.notna(value) else None

        # Store value
        key = f"{year}-{month}"
        monthly_data[key] = value_float

    # Sort years
    years = sorted(list(years))

    # Define months
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    return {"years": years, "months": months, "data": monthly_data}


def calculate_drawdown(equity_series):
    """
    Calculate drawdown series from equity series

    Parameters:
    -----------
    equity_series : pd.Series
        Equity curve

    Returns:
    --------
    pd.Series
        Drawdown series
    """
    # Calculate running maximum
    running_max = equity_series.cummax()

    # Calculate drawdown
    drawdown = (equity_series / running_max) - 1

    return drawdown


def calculate_rolling_sharpe(equity_series, window=252):
    """
    Calculate rolling Sharpe ratio from equity series

    Parameters:
    -----------
    equity_series : pd.Series
        Equity curve
    window : int
        Rolling window size

    Returns:
    --------
    pd.Series
        Rolling Sharpe ratio series
    """
    # Calculate returns
    returns = equity_series.pct_change().dropna()

    # Calculate rolling mean (annualized)
    rolling_mean = returns.rolling(window=window).mean() * 252

    # Calculate rolling standard deviation (annualized)
    rolling_std = returns.rolling(window=window).std() * np.sqrt(252)

    # Calculate rolling Sharpe ratio
    rolling_sharpe = rolling_mean / rolling_std

    return rolling_sharpe


def calculate_monthly_returns(equity_series):
    """
    Calculate monthly returns from equity series

    Parameters:
    -----------
    equity_series : pd.Series
        Equity curve

    Returns:
    --------
    pd.Series
        Monthly returns series
    """
    # Resample to monthly frequency, taking the last value of each month
    monthly_values = equity_series.resample("M").last()

    # Calculate percentage change
    monthly_returns = monthly_values.pct_change().dropna()

    return monthly_returns
