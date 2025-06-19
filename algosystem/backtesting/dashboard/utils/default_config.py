"""
Default dashboard configuration.
"""

import os
import json

# Path to default config file
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'default_dashboard_config.json')

def get_default_config():
    """
    Get the default dashboard configuration.
    
    Returns:
    --------
    dict
        Default dashboard configuration
    """
    default_config = {
        "metrics": [
            {
                "id": "total_return",
                "type": "Percentage", 
                "title": "Total Return",
                "value_key": "total_return",
                "position": {"row": 0, "col": 0}
            },
            {
                "id": "sharpe_ratio",
                "type": "Value",
                "title": "Sharpe Ratio", 
                "value_key": "sharpe_ratio",
                "position": {"row": 0, "col": 1}
            },
            {
                "id": "max_drawdown",
                "type": "Percentage",
                "title": "Max Drawdown",
                "value_key": "max_drawdown", 
                "position": {"row": 0, "col": 2}
            },
            {
                "id": "volatility",
                "type": "Percentage",
                "title": "Volatility",
                "value_key": "annualized_volatility",
                "position": {"row": 1, "col": 0}
            }
        ],
        "charts": [
            {
                "id": "equity_curve",
                "type": "LineChart",
                "title": "Equity Curve",
                "data_key": "equity_curve",
                "position": {"row": 2, "col": 0},
                "config": {"y_axis_label": "Value"}
            },
            {
                "id": "drawdown_series", 
                "type": "LineChart",
                "title": "Drawdown",
                "data_key": "drawdown_series",
                "position": {"row": 2, "col": 1},
                "config": {"y_axis_label": "Drawdown (%)"}
            },
            {
                "id": "rolling_sharpe",
                "type": "LineChart", 
                "title": "Rolling Sharpe Ratio",
                "data_key": "rolling_sharpe",
                "position": {"row": 3, "col": 0},
                "config": {"y_axis_label": "Sharpe Ratio"}
            },
            {
                "id": "monthly_returns",
                "type": "BarChart",
                "title": "Monthly Returns", 
                "data_key": "monthly_returns",
                "position": {"row": 3, "col": 1},
                "config": {"y_axis_label": "Return (%)"}
            }
        ],
        "layout": {
            "max_cols": 3,
            "title": "AlgoSystem Dashboard"
        }
    }
    
    # Try to load from file if it exists
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    return default_config
