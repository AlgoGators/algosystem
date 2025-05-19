# File: algosystem/backtesting/dashboard/utils/default_config.py

import json
import os

# Path to the default configuration
DEFAULT_CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "default_config.json")
)


def get_default_config():
    """Load the default dashboard configuration."""
    try:
        with open(DEFAULT_CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Return a minimal default configuration if file not found
        return {
            "metrics": [
                {
                    "id": "annual_return",
                    "type": "Percentage",
                    "title": "Annualized Return",
                    "value_key": "annualized_return",
                    "position": {"row": 0, "col": 0},
                },
                {
                    "id": "total_return",
                    "type": "Percentage",
                    "title": "Total Return",
                    "value_key": "total_return",
                    "position": {"row": 0, "col": 1},
                },
                {
                    "id": "sharpe_ratio",
                    "type": "Value",
                    "title": "Sharpe Ratio",
                    "value_key": "sharpe_ratio",
                    "position": {"row": 0, "col": 2},
                },
                {
                    "id": "max_drawdown",
                    "type": "Percentage",
                    "title": "Max Drawdown",
                    "value_key": "max_drawdown",
                    "position": {"row": 0, "col": 3},
                },
            ],
            "charts": [
                {
                    "id": "equity_curve",
                    "type": "LineChart",
                    "title": "Equity Curve",
                    "data_key": "equity",
                    "position": {"row": 1, "col": 0},
                    "config": {"y_axis_label": "Value ($)"},
                },
                {
                    "id": "drawdown",
                    "type": "LineChart",
                    "title": "Drawdown Chart",
                    "data_key": "drawdown",
                    "position": {"row": 1, "col": 1},
                    "config": {
                        "y_axis_label": "Drawdown (%)",
                        "percentage_format": True,
                    },
                },
            ],
            "layout": {"max_cols": 2, "title": "AlgoSystem Trading Dashboard"},
        }
