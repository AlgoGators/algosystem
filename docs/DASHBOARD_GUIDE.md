# Dashboard Customization Guide

## Dashboard Types

### 1. Interactive Dashboard
Multi-page HTML with navigation and interactive charts
```bash
algosystem render strategy.csv --output-dir ./dashboard/
```

### 2. Standalone Dashboard
Self-contained HTML file
```bash
algosystem dashboard strategy.csv --output-file dashboard.html
```

### 3. Visual Editor
Drag-and-drop interface
```bash
algosystem launch
```

## Available Metrics (20+)

### Performance Metrics
- **Total Return** - Overall strategy return
- **Annualized Return** - Annualized performance
- **Volatility** - Annualized volatility
- **Positive Days** - Days with positive returns
- **Win Rate** - Percentage of positive days

### Risk Metrics
- **Max Drawdown** - Maximum peak-to-trough decline
- **VaR 95%** - Value at Risk (95% confidence)
- **CVaR 95%** - Conditional Value at Risk
- **Skewness** - Return distribution skewness

### Ratio Metrics
- **Sharpe Ratio** - Risk-adjusted return
- **Sortino Ratio** - Downside-adjusted return
- **Calmar Ratio** - Return/max drawdown ratio

### Benchmark Metrics (when benchmark provided)
- **Alpha** - Excess return vs benchmark
- **Beta** - Sensitivity to benchmark
- **Correlation** - Correlation with benchmark
- **Information Ratio** - Alpha/tracking error

## Available Charts (15+)

### Core Charts
- **Equity Curve** - Portfolio value over time
- **Drawdown Series** - Drawdown periods
- **Daily Returns** - Daily return distribution

### Rolling Metrics
- **Rolling Sharpe** - Rolling Sharpe ratio
- **Rolling Sortino** - Rolling Sortino ratio
- **Rolling Volatility** - Rolling volatility
- **Rolling Skewness** - Rolling skewness

### Returns Analysis
- **Monthly Returns** - Monthly performance
- **Yearly Returns** - Annual performance
- **Rolling Periods** - 3M, 6M, 1Y rolling returns

### Benchmark Comparison
- **Strategy vs Benchmark** - Performance comparison
- **Relative Performance** - Relative returns
- **Benchmark Drawdown** - Benchmark drawdowns

## Configuration System

### Basic Structure
```json
{
  "metrics": [
    {
      "id": "total_return",
      "type": "Percentage",
      "title": "Total Return",
      "value_key": "total_return",
      "position": {"row": 0, "col": 0}
    }
  ],
  "charts": [
    {
      "id": "equity_curve",
      "type": "LineChart",
      "title": "Equity Curve",
      "data_key": "equity_curve",
      "position": {"row": 1, "col": 0},
      "config": {"y_axis_label": "Value"}
    }
  ],
  "layout": {
    "max_cols": 2,
    "title": "Trading Dashboard"
  }
}
```

### Metric Types
- **Percentage** - Displays as percentage (e.g., 15.2%)
- **Value** - Displays as number (e.g., 1.25)
- **Currency** - Displays as currency (e.g., $10,000)

### Chart Types
- **LineChart** - Line plot for time series
- **BarChart** - Bar chart for categorical data
- **HeatmapTable** - Heatmap for matrix data

## Customization Examples

### Custom Metric
```python
from algosystem.api import AlgoSystem

config = AlgoSystem.load_config()
config["metrics"].append({
    "id": "custom_metric",
    "type": "Value",
    "title": "Custom Sharpe",
    "value_key": "sharpe_ratio",
    "position": {"row": 0, "col": 3}
})
AlgoSystem.save_config(config, "custom.json")
```

### Custom Chart
```python
config["charts"].append({
    "id": "custom_chart",
    "type": "LineChart",
    "title": "Custom Analysis",
    "data_key": "rolling_volatility",
    "position": {"row": 2, "col": 0},
    "config": {
        "y_axis_label": "Volatility",
        "line_color": "#2ecc71"
    }
})
```

### Layout Customization
```python
config["layout"] = {
    "max_cols": 3,  # 3 columns per row
    "title": "Custom Strategy Dashboard",
    "subtitle": "Performance Analysis"
}
```

## Position System

### Grid Layout
- **row**: Zero-based row index (0 = first row)
- **col**: Zero-based column index (0 = first column)
- **max_cols**: Maximum columns per row (default: 2)

### Example Layout
```
Row 0: [Metric1] [Metric2] [Metric3]  (max_cols: 3)
Row 1: [Chart1]  [Chart2]             (max_cols: 2)
Row 2: [Chart3]                       (max_cols: 1)
```

## Configuration Management

### CLI Commands
```bash
# Create new configuration
algosystem create-config my_config.json

# View configuration
algosystem show-config my_config.json

# Use in dashboard
algosystem dashboard strategy.csv --config my_config.json
```

### Python API
```python
# Load and modify
config = AlgoSystem.load_config()
config["layout"]["title"] = "My Dashboard"

# Save and use
AlgoSystem.save_config(config, "modified.json")
dashboard_path = AlgoSystem.generate_dashboard(
    engine,
    config_path="modified.json"
)
```

## Visual Editor Features

### Access Editor
```bash
algosystem launch --port 8080
# Visit: http://localhost:8080
```

### Editor Capabilities
- **Drag-and-Drop** - Arrange metrics and charts
- **Live Preview** - See changes in real-time
- **Data Upload** - Test with your CSV files
- **Export Config** - Save custom layouts
- **Template Library** - Pre-built configurations

## Chart Configuration Options

### Common Options
```json
{
  "config": {
    "y_axis_label": "Value",
    "x_axis_label": "Date",
    "line_color": "#3498db",
    "line_width": 2,
    "show_grid": true,
    "percentage_format": false
  }
}
```

### Chart-Specific Options

#### LineChart
- `line_color` - Line color (hex code)
- `line_width` - Line thickness
- `fill_area` - Fill area under line

#### BarChart
- `bar_color` - Bar color
- `show_values` - Display values on bars

#### HeatmapTable
- `color_scheme` - Color palette
- `show_values` - Display cell values

## Template Configurations

### Performance Focus
```json
{
  "metrics": [
    {"id": "total_return", "type": "Percentage", "title": "Total Return", "value_key": "total_return", "position": {"row": 0, "col": 0}},
    {"id": "sharpe_ratio", "type": "Value", "title": "Sharpe Ratio", "value_key": "sharpe_ratio", "position": {"row": 0, "col": 1}},
    {"id": "max_drawdown", "type": "Percentage", "title": "Max Drawdown", "value_key": "max_drawdown", "position": {"row": 0, "col": 2}}
  ],
  "charts": [
    {"id": "equity_curve", "type": "LineChart", "title": "Equity Curve", "data_key": "equity_curve", "position": {"row": 1, "col": 0}},
    {"id": "monthly_returns", "type": "BarChart", "title": "Monthly Returns", "data_key": "monthly_returns", "position": {"row": 1, "col": 1}}
  ],
  "layout": {"max_cols": 3, "title": "Performance Dashboard"}
}
```

### Risk Analysis
```json
{
  "metrics": [
    {"id": "volatility", "type": "Percentage", "title": "Volatility", "value_key": "volatility", "position": {"row": 0, "col": 0}},
    {"id": "var_95", "type": "Percentage", "title": "VaR 95%", "value_key": "var_95", "position": {"row": 0, "col": 1}},
    {"id": "skewness", "type": "Value", "title": "Skewness", "value_key": "skewness", "position": {"row": 0, "col": 2}}
  ],
  "charts": [
    {"id": "drawdown_series", "type": "LineChart", "title": "Drawdown", "data_key": "drawdown_series", "position": {"row": 1, "col": 0}},
    {"id": "rolling_volatility", "type": "LineChart", "title": "Rolling Volatility", "data_key": "rolling_volatility", "position": {"row": 1, "col": 1}}
  ],
  "layout": {"max_cols": 2, "title": "Risk Analysis Dashboard"}
}
```

## Export Options

### Standalone HTML
```python
# Self-contained file
standalone_path = engine.generate_standalone_dashboard(
    output_path="standalone.html"
)
```

### Chart Images
```python
# Export all charts as PNG
chart_paths = AlgoSystem.export_charts(
    engine,
    output_dir="./charts",
    dpi=300
)
```

### Data Export
```python
# Export underlying data
csv_path = AlgoSystem.export_data(
    engine,
    output_path="dashboard_data.csv"
)
```