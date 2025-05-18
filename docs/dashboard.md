# Dashboard Customization Guide

AlgoSystem provides powerful capabilities for creating and customizing interactive trading dashboards. This guide shows you how to create professional-grade dashboards that rival institutional trading platforms.

## Table of Contents

- [Overview](#overview)
- [Dashboard Structure](#dashboard-structure)
- [Creating Dashboards](#creating-dashboards)
- [Visual Dashboard Editor](#visual-dashboard-editor)
- [Configuration Format](#configuration-format)
- [Available Metrics](#available-metrics)
- [Available Charts](#available-charts)
- [Customizing Layouts](#customizing-layouts)
- [Saving and Loading Configurations](#saving-and-loading-configurations)
- [Exporting Dashboards](#exporting-dashboards)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

AlgoSystem dashboards provide:

- **Visual performance insights**: Interactive charts and metrics displaying strategy performance
- **Risk analysis**: Comprehensive risk metrics and visualizations
- **Benchmark comparison**: Performance relative to market indices
- **Time series analysis**: Rolling metrics showing performance over time
- **Fully customizable layouts**: Drag-and-drop interface for arranging components

## Dashboard Structure

AlgoSystem dashboards consist of these main components:

1. **Header**: Displays dashboard title, date range, and summary statistics
2. **Metrics Section**: Shows performance metrics in card format
3. **Charts Section**: Displays interactive charts for time series data
4. **Export Options**: Tools to save or share the dashboard

## Creating Dashboards

### Command Line Method

Generate a dashboard from CSV strategy data:

```bash
# Basic dashboard generation
algosystem dashboard strategy.csv

# With benchmark comparison
algosystem dashboard strategy.csv --benchmark sp500

# Specify custom configuration
algosystem dashboard strategy.csv --config my_config.json

# Custom output location
algosystem dashboard strategy.csv --output-file custom_dashboard.html
```

### Python API Method

```python
from algosystem.backtesting import Engine
from algosystem.api import AlgoSystem

# Method 1: Using Engine class
engine = Engine(data=price_series)
results = engine.run()
dashboard_path = engine.generate_dashboard(
    output_dir="./dashboard",
    open_browser=True
)

# Method 2: Using AlgoSystem API
engine = AlgoSystem.run_backtest(price_series)
dashboard_path = AlgoSystem.generate_dashboard(
    engine,
    output_dir="./dashboard",
    open_browser=True
)
```

## Visual Dashboard Editor

AlgoSystem includes a visual dashboard editor for drag-and-drop customization:

1. **Launch the editor**:
   ```bash
   algosystem launch
   ```

2. **Editor Interface**:
   - **Left Panel**: Available metrics and charts
   - **Right Panel**: Dashboard preview with drag-and-drop areas
   - **Controls**: Save, reset, and view dashboard

3. **Workflow**:
   - Upload strategy CSV data
   - Drag metrics and charts to desired positions
   - Arrange in multiple rows
   - Save configuration
   - View the generated dashboard

4. **Editor Options**:
   ```bash
   # Use custom configuration as starting point
   algosystem launch --config my_config.json
   
   # Save changes to specific location
   algosystem launch --save-config my_custom_config.json
   
   # Run on different port
   algosystem launch --port 8080
   ```

## Configuration Format

Dashboard configurations are JSON files with this structure:

```json
{
  "metrics": [
    {
      "id": "annual_return",
      "type": "Percentage",
      "title": "Annualized Return",
      "value_key": "annualized_return",
      "position": {"row": 0, "col": 0}
    },
    // More metrics...
  ],
  "charts": [
    {
      "id": "equity_curve",
      "type": "LineChart",
      "title": "Equity Curve",
      "data_key": "equity",
      "position": {"row": 1, "col": 0},
      "config": {"y_axis_label": "Value ($)"}
    },
    // More charts...
  ],
  "layout": {
    "max_cols": 2,
    "title": "AlgoSystem Trading Dashboard"
  }
}
```

## Available Metrics

AlgoSystem provides various metric types to display on dashboards:

### Performance Metrics
- **Total Return**: Total return over the full period
- **Annualized Return**: Annualized return of the strategy
- **Volatility**: Annualized volatility of the strategy

### Risk Metrics
- **Max Drawdown**: Maximum drawdown of the strategy
- **Value at Risk (95%)**: 95% Value at Risk
- **Conditional VaR (95%)**: 95% Conditional Value at Risk
- **Skewness**: Skewness of returns distribution

### Ratio Metrics
- **Sharpe Ratio**: Sharpe ratio of the strategy
- **Sortino Ratio**: Sortino ratio of the strategy
- **Calmar Ratio**: Calmar ratio of the strategy

### Trade Statistics
- **Positive Days**: Number of days with positive returns
- **Negative Days**: Number of days with negative returns
- **Win Rate**: Percentage of days with positive returns
- **Best Month**: Best monthly return
- **Worst Month**: Worst monthly return
- **Avg Monthly Return**: Average monthly return
- **Monthly Volatility**: Standard deviation of monthly returns
- **Monthly Win Rate**: Percentage of months with positive returns

### Benchmark Metrics (when benchmark is provided)
- **Alpha**: Alpha relative to benchmark
- **Beta**: Beta relative to benchmark
- **Correlation**: Correlation with benchmark
- **Tracking Error**: Tracking error relative to benchmark
- **Information Ratio**: Information ratio relative to benchmark
- **Upside Capture**: Upside capture ratio
- **Downside Capture**: Downside capture ratio

Each metric requires:
- **id**: Unique identifier
- **type**: Metric type (Percentage, Value, Currency)
- **title**: Display name
- **value_key**: Key to look up value in results
- **position**: Row and column position in dashboard

## Available Charts

AlgoSystem supports various chart types:

### Line Charts
- **Equity Curve**: Shows the growth of portfolio value
- **Drawdown Chart**: Shows drawdown periods for the strategy
- **Daily Returns**: Shows daily returns of the strategy

### Rolling Metrics Charts
- **Rolling Sharpe Ratio**: Shows the rolling Sharpe ratio
- **Rolling Sortino Ratio**: Shows the rolling Sortino ratio
- **Rolling Volatility**: Shows the rolling volatility
- **Rolling Skewness**: Shows the rolling skewness
- **Rolling VaR (5%)**: Shows the rolling 5% Value at Risk
- **Rolling Max Drawdown Duration**: Shows the rolling maximum drawdown duration

### Returns Analysis Charts
- **Monthly Returns Heatmap**: Displays monthly returns as a heatmap
- **Yearly Returns**: Shows yearly returns as a bar chart
- **Rolling 3-Month Returns**: Shows rolling 3-month returns
- **Rolling 6-Month Returns**: Shows rolling 6-month returns
- **Rolling 1-Year Returns**: Shows rolling 1-year returns

### Benchmark Comparison Charts
- **Strategy vs Benchmark**: Compares strategy and benchmark performance
- **Relative Performance**: Shows performance relative to benchmark
- **Benchmark Drawdown**: Shows benchmark drawdown periods
- **Benchmark Rolling Volatility**: Shows benchmark rolling volatility

Each chart requires:
- **id**: Unique identifier
- **type**: Chart type (LineChart, HeatmapTable, BarChart)
- **title**: Display name
- **data_key**: Key to look up data in results
- **position**: Row and column position in dashboard
- **config**: Chart-specific configuration

## Customizing Layouts

### Row and Column Positioning

Metrics and charts are organized in rows and columns:

```json
"position": {"row": 0, "col": 0}
```

- **row**: Zero-based row index (0 = first row)
- **col**: Zero-based column index within the row (0 = first column)

Guidelines:
- Metrics rows typically have 4 metrics per row
- Chart rows typically have 2 charts per row
- Set in the `max_cols` property of the layout section

### Chart Configuration

Customize chart appearance:

```json
"config": {
  "y_axis_label": "Value ($)",
  "percentage_format": true,
  "line_color": "#2ecc71",
  "line_width": 2
}
```

Options:
- **y_axis_label**: Label for the Y-axis
- **percentage_format**: Format values as percentages
- **line_color**: Color for line charts (hex code)
- **line_width**: Width of lines in pixels
- **window_size**: For rolling metrics, window size in days

## Saving and Loading Configurations

### Create a New Configuration

Command line:
```bash
# Create new configuration
algosystem create-config my_config.json

# Base on existing configuration
algosystem create-config new_config.json --based-on existing.json
```

Python API:
```python
from algosystem.api import AlgoSystem

# Load default or user configuration
config = AlgoSystem.load_config()

# Modify configuration
config["layout"]["title"] = "My Custom Dashboard"

# Save to new file
AlgoSystem.save_config(config, "my_config.json")
```

### List and View Configurations

```bash
# List available configurations
algosystem list-configs

# Show configuration contents
algosystem show-config my_config.json
```

### Reset to Default Configuration

```bash
# Reset user configuration to defaults
algosystem reset-user-config
```

## Exporting Dashboards

### Standalone HTML Dashboard

Generate a self-contained HTML file that can be shared and viewed without a web server:

```bash
# Command line
algosystem dashboard strategy.csv --output-file standalone.html

# Python API
engine.generate_standalone_dashboard("standalone.html")
```

### Exporting Chart Images

```python
from algosystem.api import AlgoSystem

# Export all charts as PNG images
chart_paths = AlgoSystem.export_charts(
    engine,
    output_dir="./plots",
    dpi=300  # Higher resolution
)
```

### Exporting Data

```python
# Export all time series data
data_path = AlgoSystem.export_data(
    engine,
    output_path="./exports/strategy_data.csv",
    format="csv"
)
```

## Best Practices

1. **Consistent Layout**: Keep similar metrics together for easy comparison

2. **Essential Metrics First**: Place most important metrics in the first row
   - Total Return
   - Annualized Return
   - Max Drawdown
   - Sharpe Ratio

3. **Logical Grouping**: Group related charts together
   - Performance charts (Equity Curve, Drawdown)
   - Risk charts (Rolling Volatility, VaR)
   - Returns analysis (Monthly Returns, Yearly Returns)
   - Benchmark comparison (if applicable)

4. **Use Dashboard Templates**: Create template configurations for different strategy types
   - Equity strategies
   - Fixed income strategies
   - Multi-asset strategies
   - Day trading strategies (more frequent data)

5. **Customize for Audience**:
   - Traders: Focus on performance and trade statistics
   - Risk managers: Highlight risk metrics and drawdowns
   - Investors: Emphasize long-term performance and benchmark comparison

6. **Meaningful Titles**: Use descriptive titles for charts and dashboards

7. **Custom Metrics**: Add custom metrics to highlight strategy-specific KPIs

## Troubleshooting

### "No data available" on charts

- Check that the data key in chart configuration matches available data
- Ensure your data has sufficient history for rolling metrics
- Verify there's enough data for the selected date range

### Missing metrics

- Confirm the value_key in metric configuration matches available metrics
- Some metrics (like benchmark metrics) require specific data (e.g., benchmark)
- Check if metric calculation failed in the logs

### Layout issues

- Ensure position.row and position.col are valid integers
- Check max_cols in layout configuration
- Verify you're not placing more items in a row than max_cols

### Benchmark charts not showing

- Confirm you've provided benchmark data
- Check that benchmark_data_key is correct
- Ensure benchmark and strategy data have overlapping dates

### Editor not loading

- Check that Flask is installed (`pip install flask`)
- Ensure the port is not in use by another application
- Try using a different browser

### Configuration not saving

- Check write permissions for the output directory
- Ensure the configuration is valid JSON
- Try using an absolute path for the config file

### Chart rendering issues

- Ensure you have internet access for loading Chart.js libraries
- Try using a standalone dashboard which includes all libraries
- Check browser console for JavaScript errors