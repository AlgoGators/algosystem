import os
import sys
import json
import numpy as np
import pandas as pd
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QLabel, QMenu, QDialog,
    QGridLayout, QComboBox, QColorDialog, QSlider, QSpinBox,
    QDoubleSpinBox, QCheckBox, QGroupBox, QToolButton, QScrollArea,
    QFileDialog, QTabWidget, QLineEdit, QMessageBox, QListWidget,
    QSplitter, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize
from PyQt6.QtGui import QIcon, QDrag, QPixmap
import pyqtgraph as pg
from PyQt6.QtGui import QPainter, QDrag, QPixmap
from PyQt6.QtCore import QMimeData
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# Import AlgoSystem modules
from algosystem.utils.config import load_config, save_config

# Import performance functions
from algosystem.analysis.performance import (
    calculate_returns_stats,
    calculate_rolling_stats,
    compare_strategies,
    analyze_returns_by_period
)

# Import portfolio functions
from algosystem.analysis.portfolio import (
    calculate_portfolio_return,
    calculate_portfolio_variance,
    calculate_portfolio_std,
    calculate_sharpe_ratio,
    optimize_portfolio,
    calculate_efficient_frontier
)

# Import risk functions
from algosystem.analysis.risk import (
    calculate_var,
    calculate_cvar,
    calculate_risk_metrics,
    stress_test
)

from algosystem.backtesting.engine import Engine
from algosystem.backtesting.visualization import (
    create_equity_chart,
    create_drawdown_chart,
    create_monthly_returns_heatmap,
    create_rolling_sharpe_chart,
    create_performance_dashboard
)

class PlotRegistry:
    """Registry of available plot types and their associated functions"""
    
    def __init__(self):
        self.plot_types = {}
        self.register_default_plots()
    
    def register_plot(self, name, function, description, required_data, parameters=None):
        """Register a new plot type"""
        self.plot_types[name] = {
            'function': function,
            'description': description,
            'required_data': required_data,
            'parameters': parameters or {}
        }
    
    def register_default_plots(self):
        """Register the default plot types that come with AlgoSystem"""
        
        # Performance plots
        self.register_plot(
            name="Equity Curve",
            function=create_equity_chart,
            description="Shows the growth of portfolio value over time",
            required_data=["equity"],
            parameters={
                'benchmark': {'type': 'data', 'required': False, 'default': None},
                'figsize': {'type': 'tuple', 'required': False, 'default': (10, 6)}
            }
        )
        
        self.register_plot(
            name="Drawdown Chart",
            function=create_drawdown_chart,
            description="Shows the drawdown periods for the strategy",
            required_data=["equity"],
            parameters={
                'figsize': {'type': 'tuple', 'required': False, 'default': (10, 6)}
            }
        )
        
        self.register_plot(
            name="Monthly Returns Heatmap",
            function=create_monthly_returns_heatmap,
            description="Displays monthly returns as a heatmap",
            required_data=["equity"],
            parameters={
                'figsize': {'type': 'tuple', 'required': False, 'default': (10, 6)}
            }
        )
        
        self.register_plot(
            name="Rolling Sharpe Ratio",
            function=create_rolling_sharpe_chart,
            description="Shows the rolling Sharpe ratio over time",
            required_data=["equity"],
            parameters={
                'window': {'type': 'int', 'required': False, 'default': 252},
                'figsize': {'type': 'tuple', 'required': False, 'default': (10, 6)}
            }
        )
        
        # Risk analysis plots - using functions from risk.py
        self.register_plot(
            name="Value at Risk (VaR)",
            function=self._create_var_plot,
            description="Shows the Value at Risk at different confidence levels",
            required_data=["returns"],
            parameters={
                'confidence_levels': {'type': 'list', 'required': False, 'default': [0.9, 0.95, 0.99]},
                'method': {'type': 'choice', 'required': False, 'default': 'historical', 
                           'choices': ['historical', 'parametric', 'monte_carlo']}
            }
        )
        
        # Portfolio optimization plots - using functions from portfolio.py
        self.register_plot(
            name="Efficient Frontier",
            function=self._create_efficient_frontier_plot,
            description="Shows the efficient frontier for a portfolio of assets",
            required_data=["returns_matrix"],
            parameters={
                'num_points': {'type': 'int', 'required': False, 'default': 50},
                'risk_free_rate': {'type': 'float', 'required': False, 'default': 0.0}
            }
        )
        
        # Add more plot types from performance.py
        self.register_plot(
            name="Returns by Period",
            function=self._create_returns_by_period_plot,
            description="Shows returns broken down by different time periods",
            required_data=["returns"],
            parameters={}
        )
        
        self.register_plot(
            name="Rolling Performance",
            function=self._create_rolling_performance_plot,
            description="Shows rolling performance metrics over time",
            required_data=["returns"],
            parameters={
                'window': {'type': 'int', 'required': False, 'default': 252}
            }
        )
        
        # Add more plot types from risk.py
        self.register_plot(
            name="Return Distribution",
            function=self._create_return_distribution_plot,
            description="Histogram of returns with normal distribution overlay",
            required_data=["returns"],
            parameters={
                'bins': {'type': 'int', 'required': False, 'default': 50}
            }
        )
        
        self.register_plot(
            name="Risk Metrics",
            function=self._create_risk_metrics_plot,
            description="Visual summary of key risk metrics",
            required_data=["returns"],
            parameters={
                'risk_free_rate': {'type': 'float', 'required': False, 'default': 0.0}
            }
        )
    
    def _create_var_plot(self, returns, confidence_levels=[0.9, 0.95, 0.99], method='historical'):
        """Create VaR plot using calculate_var from risk.py"""
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Calculate VaR at different confidence levels using risk.py function
        var_values = [calculate_var(returns, cl, method) for cl in confidence_levels]
        
        # Plot returns histogram
        returns.hist(bins=50, ax=ax, alpha=0.5)
        
        # Add VaR lines
        colors = ['green', 'orange', 'red']
        for i, (cl, var) in enumerate(zip(confidence_levels, var_values)):
            ax.axvline(-var, color=colors[i], linestyle='--', 
                       label=f'VaR {cl*100:.0f}%: {var:.2%}')
        
        ax.set_title(f'Value at Risk ({method.capitalize()})')
        ax.set_xlabel('Returns')
        ax.set_ylabel('Frequency')
        ax.legend()
        
        return fig
    
    def _create_efficient_frontier_plot(self, returns_matrix, num_points=50, risk_free_rate=0.0):
        """Create efficient frontier plot using functions from portfolio.py"""
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Calculate the efficient frontier using portfolio.py function
        frontier_returns, frontier_volatilities, frontier_weights = calculate_efficient_frontier(
            returns_matrix, num_points, risk_free_rate
        )
        
        # Plot the efficient frontier
        ax.plot(frontier_volatilities, frontier_returns, 'b-', linewidth=3, label='Efficient Frontier')
        
        # Calculate and plot the optimal portfolio (maximum Sharpe ratio)
        optimal_weights, performance = optimize_portfolio(returns_matrix, risk_free_rate)
        optimal_return = performance['expected_return']
        optimal_volatility = performance['volatility']
        
        ax.scatter(optimal_volatility, optimal_return, marker='*', s=200, color='red',
                   label=f'Optimal Portfolio (Sharpe: {performance["sharpe_ratio"]:.2f})')
        
        # Add capital market line if risk-free rate is provided
        if risk_free_rate > 0:
            max_vol = frontier_volatilities[-1] * 1.2
            x_values = np.linspace(0, max_vol, 100)
            slope = (optimal_return - risk_free_rate) / optimal_volatility
            y_values = risk_free_rate + slope * x_values
            ax.plot(x_values, y_values, 'g--', label='Capital Market Line')
            ax.scatter(0, risk_free_rate, marker='o', color='green', label='Risk-Free Asset')
        
        ax.set_title('Efficient Frontier')
        ax.set_xlabel('Volatility (Standard Deviation)')
        ax.set_ylabel('Expected Return')
        ax.legend()
        ax.grid(True)
        
        return fig
    
    def _create_return_distribution_plot(self, returns, bins=50):
        """Create histogram of returns with normal distribution overlay"""
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Plot histogram
        n, bins, patches = ax.hist(returns, bins=bins, density=True, alpha=0.6, color='blue')
        
        # Fit normal distribution
        mu = returns.mean()
        sigma = returns.std()
        x = np.linspace(mu - 4*sigma, mu + 4*sigma, 100)
        y = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(- (x - mu)**2 / (2 * sigma**2))
        
        # Plot normal distribution
        ax.plot(x, y, 'r--', linewidth=2, label='Normal Distribution')
        
        # Add mean line
        ax.axvline(mu, color='green', linestyle='-', linewidth=2, 
                   label=f'Mean: {mu:.2%}')
        
        # Calculate and display skewness and kurtosis
        skew = returns.skew()
        kurt = returns.kurtosis()
        stats_text = f'Skewness: {skew:.2f}\nKurtosis: {kurt:.2f}'
        ax.text(0.95, 0.95, stats_text, transform=ax.transAxes, verticalalignment='top',
                horizontalalignment='right', bbox={'facecolor': 'white', 'alpha': 0.8})
        
        ax.set_title('Return Distribution')
        ax.set_xlabel('Returns')
        ax.set_ylabel('Density')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def _create_risk_metrics_plot(self, returns, risk_free_rate=0.0):
        """Create visual summary of risk metrics using calculate_risk_metrics from risk.py"""
        # Calculate risk metrics
        metrics = calculate_risk_metrics(returns, risk_free_rate)
        
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        
        # Create bar chart of key metrics
        metric_names = ['annual_return', 'volatility', 'sharpe_ratio', 'sortino_ratio', 'max_drawdown']
        metric_labels = ['Annual Return', 'Volatility', 'Sharpe Ratio', 'Sortino Ratio', 'Max Drawdown']
        metric_values = [metrics[name] for name in metric_names]
        
        # Adjust max_drawdown to positive for visualization
        metric_values[4] = abs(metric_values[4])
        
        x = np.arange(len(metric_names))
        bars = ax.bar(x, metric_values, width=0.6, alpha=0.7)
        
        # Add value labels on top of bars
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        ax.set_title('Risk Metrics Summary')
        ax.set_xticks(x)
        ax.set_xticklabels(metric_labels, rotation=45)
        ax.grid(True, alpha=0.3, axis='y')
        
        return fig
    
    def _create_returns_by_period_plot(self, returns):
        """Create returns by period plot using analyze_returns_by_period from performance.py"""
        # Get period analysis
        period_analysis = analyze_returns_by_period(returns)
        
        fig = plt.figure(figsize=(12, 10))
        
        # Create subplot for monthly returns
        ax1 = fig.add_subplot(2, 2, 1)
        monthly_returns = period_analysis['monthly']['returns']
        monthly_returns.plot(kind='bar', ax=ax1)
        ax1.set_title('Monthly Returns')
        ax1.set_ylabel('Return')
        ax1.grid(True, alpha=0.3)
        
        # Create subplot for day of week analysis
        ax2 = fig.add_subplot(2, 2, 2)
        dow_analysis = period_analysis['day_of_week']
        dow_analysis['mean'].plot(kind='bar', ax=ax2)
        ax2.set_title('Average Return by Day of Week')
        ax2.set_ylabel('Return')
        ax2.grid(True, alpha=0.3)
        
        # Create subplot for month of year analysis
        ax3 = fig.add_subplot(2, 2, 3)
        moy_analysis = period_analysis['month_of_year']
        moy_analysis['mean'].plot(kind='bar', ax=ax3)
        ax3.set_title('Average Return by Month')
        ax3.set_ylabel('Return')
        ax3.grid(True, alpha=0.3)
        
        # Create subplot for positive percentage by period
        ax4 = fig.add_subplot(2, 2, 4)
        periods = ['daily', 'monthly', 'quarterly', 'annual']
        period_labels = ['Daily', 'Monthly', 'Quarterly', 'Annual']
        positive_pcts = [period_analysis[p]['positive_pct'] for p in periods]
        
        ax4.bar(period_labels, positive_pcts)
        ax4.set_title('Percentage of Positive Returns by Period')
        ax4.set_ylabel('Percentage')
        ax4.set_ylim([0, 1])
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def _create_rolling_performance_plot(self, returns, window=252):
        """Create rolling performance plot using calculate_rolling_stats from performance.py"""
        # Calculate rolling statistics
        rolling_stats = calculate_rolling_stats(returns, window)
        
        fig = plt.figure(figsize=(12, 10))
        
        # Create subplot for rolling return
        ax1 = fig.add_subplot(2, 2, 1)
        rolling_stats['rolling_return'].plot(ax=ax1)
        ax1.set_title(f'Rolling {window}-Day Return (Annualized)')
        ax1.set_ylabel('Return')
        ax1.grid(True, alpha=0.3)
        
        # Create subplot for rolling volatility
        ax2 = fig.add_subplot(2, 2, 2)
        rolling_stats['rolling_volatility'].plot(ax=ax2)
        ax2.set_title(f'Rolling {window}-Day Volatility (Annualized)')
        ax2.set_ylabel('Volatility')
        ax2.grid(True, alpha=0.3)
        
        # Create subplot for rolling Sharpe ratio
        ax3 = fig.add_subplot(2, 2, 3)
        rolling_stats['rolling_sharpe'].plot(ax=ax3)
        ax3.set_title(f'Rolling {window}-Day Sharpe Ratio')
        ax3.set_ylabel('Sharpe Ratio')
        ax3.grid(True, alpha=0.3)
        
        # Create subplot for rolling max drawdown
        ax4 = fig.add_subplot(2, 2, 4)
        rolling_stats['rolling_max_drawdown'].plot(ax=ax4)
        ax4.set_title(f'Rolling {window}-Day Max Drawdown')
        ax4.set_ylabel('Drawdown')
        ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        return fig
    
    def get_plot_types(self):
        """Get list of available plot types"""
        return list(self.plot_types.keys())
    
    def get_plot_info(self, name):
        """Get information about a specific plot type"""
        return self.plot_types.get(name)
    
    def create_plot(self, plot_type, data, **kwargs):
        """Create a plot of the specified type using the provided data"""
        if plot_type not in self.plot_types:
            raise ValueError(f"Unknown plot type: {plot_type}")
        
        plot_info = self.plot_types[plot_type]
        plot_func = plot_info['function']
        
        # Check if we have the required data
        required_data = plot_info['required_data']
        for req in required_data:
            if req not in data:
                raise ValueError(f"Missing required data for {plot_type}: {req}")
        
        # Extract required data from data dictionary
        plot_data = {req: data[req] for req in required_data if req in data}
        
        # Merge kwargs with default parameters
        parameters = plot_info['parameters']
        for param_name, param_info in parameters.items():
            if param_name not in kwargs and 'default' in param_info:
                kwargs[param_name] = param_info['default']
        
        # Create the plot
        return plot_func(**plot_data, **kwargs)


class DataManager:
    """Handles loading and preprocessing of strategy data"""
    
    def __init__(self):
        self.data_sources = {}
        self.current_data = None
        self.prepared_data = {}  # Store preprocessed data for charts
    
    def load_csv(self, file_path, name=None):
        """Load data from a CSV file"""
        try:
            # Auto-generate name from filename if not provided
            if name is None:
                name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Load the CSV data
            data = pd.read_csv(file_path, index_col=0, parse_dates=True)
            
            # Store the data
            self.data_sources[name] = {
                'type': 'csv',
                'path': file_path,
                'data': data
            }
            
            # Preprocess the data for charts
            self._prepare_data_for_charts(name)
            
            return name
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return None
    
    def load_backtest_results(self, results_dict, name=None):
        """Load data from backtest results"""
        try:
            # Auto-generate name if not provided
            if name is None:
                name = f"Backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Store the data
            self.data_sources[name] = {
                'type': 'backtest',
                'data': results_dict
            }
            
            # Preprocess the data for charts
            self._prepare_data_for_charts(name)
            
            return name
        except Exception as e:
            print(f"Error loading backtest results: {e}")
            return None
    
    def _prepare_data_for_charts(self, source_name):
        """Preprocess data for charts when data is loaded"""
        if source_name not in self.data_sources:
            return
        
        source_info = self.data_sources[source_name]
        source_type = source_info['type']
        source_data = source_info['data']
        
        # Initialize prepared data for this source
        self.prepared_data[source_name] = {}
        
        # For backtest results
        if source_type == 'backtest':
            # Extract equity curve
            if 'equity' in source_data:
                equity = source_data['equity']
                self.prepared_data[source_name]['equity'] = equity
                
                # Calculate returns
                returns = equity.pct_change().dropna()
                self.prepared_data[source_name]['returns'] = returns
                
                # Calculate drawdown
                cumulative_returns = (1 + returns).cumprod()
                drawdown = (cumulative_returns / cumulative_returns.cummax()) - 1
                self.prepared_data[source_name]['drawdown'] = drawdown
                
                # If there are positions, calculate turnover
                if 'positions' in source_data:
                    positions = source_data['positions']
                    daily_turnover = positions.diff().abs().sum(axis=1)
                    self.prepared_data[source_name]['turnover'] = daily_turnover
                
                # Calculate performance metrics
                try:
                    from algosystem.analysis.risk import calculate_risk_metrics
                    metrics = calculate_risk_metrics(returns)
                    self.prepared_data[source_name]['metrics'] = metrics
                except Exception as e:
                    print(f"Error calculating risk metrics: {e}")
        
        # For CSV data
        elif source_type == 'csv':
            data = source_data
            
            # If it's a DataFrame with a single column, treat it as an equity curve
            if isinstance(data, pd.DataFrame) and data.shape[1] == 1:
                equity = data.iloc[:, 0]
                self.prepared_data[source_name]['equity'] = equity
                
                # Calculate returns
                returns = equity.pct_change().dropna()
                self.prepared_data[source_name]['returns'] = returns
                
                # Calculate drawdown
                cumulative_returns = (1 + returns).cumprod()
                drawdown = (cumulative_returns / cumulative_returns.cummax()) - 1
                self.prepared_data[source_name]['drawdown'] = drawdown
                
                # Calculate performance metrics
                try:
                    from algosystem.analysis.risk import calculate_risk_metrics
                    metrics = calculate_risk_metrics(returns)
                    self.prepared_data[source_name]['metrics'] = metrics
                except Exception as e:
                    print(f"Error calculating risk metrics: {e}")
            
            # If it's a DataFrame with multiple columns, treat it as returns of multiple assets
            elif isinstance(data, pd.DataFrame) and data.shape[1] > 1:
                # Store the data as returns matrix for portfolio analysis
                self.prepared_data[source_name]['returns_matrix'] = data
                
                # Calculate correlation matrix
                correlation = data.corr()
                self.prepared_data[source_name]['correlation'] = correlation
                
                # Calculate efficient frontier
                try:
                    from algosystem.analysis.portfolio import calculate_efficient_frontier, optimize_portfolio
                    frontier_returns, frontier_volatilities, frontier_weights = calculate_efficient_frontier(data, 20, 0.0)
                    optimal_weights, performance = optimize_portfolio(data, 0.0)
                    
                    self.prepared_data[source_name]['frontier_returns'] = frontier_returns
                    self.prepared_data[source_name]['frontier_volatilities'] = frontier_volatilities
                    self.prepared_data[source_name]['frontier_weights'] = frontier_weights
                    self.prepared_data[source_name]['optimal_weights'] = optimal_weights
                    self.prepared_data[source_name]['optimal_performance'] = performance
                except Exception as e:
                    print(f"Error calculating portfolio optimization: {e}")
    
    def get_data_source_names(self):
        """Get list of available data sources"""
        return list(self.data_sources.keys())
    
    def get_data(self, name):
        """Get data for a specific source"""
        if name in self.data_sources:
            return self.data_sources[name]['data']
        return None
    
    def get_prepared_data(self, name, data_type=None):
        """Get prepared data for a specific source and data type"""
        if name in self.prepared_data:
            if data_type is not None:
                return self.prepared_data[name].get(data_type)
            return self.prepared_data[name]
        return None
    
    def generate_returns(self, data_name, price_column=None):
        """Generate returns series from price data"""
        # First check if returns are already prepared
        prepared_returns = self.get_prepared_data(data_name, 'returns')
        if prepared_returns is not None:
            return prepared_returns
        
        # If not, calculate returns from the data
        data = self.get_data(data_name)
        if data is None:
            return None
        
        # If it's a backtest result, extract the equity curve
        if self.data_sources[data_name]['type'] == 'backtest':
            if 'equity' in data:
                equity = data['equity']
                returns = equity.pct_change().dropna()
                # Store the results for future use
                if data_name in self.prepared_data:
                    self.prepared_data[data_name]['returns'] = returns
                return returns
        
        # Otherwise, treat as a DataFrame with a price column
        elif isinstance(data, pd.DataFrame):
            if price_column is None:
                if data.shape[1] == 1:
                    price_column = data.columns[0]
                else:
                    raise ValueError("DataFrame has multiple columns; specify price_column.")
            
            prices = data[price_column]
            returns = prices.pct_change().dropna()
            # Store the results for future use
            if data_name in self.prepared_data:
                self.prepared_data[data_name]['returns'] = returns
            return returns
        
        return None


class EnhancedGraphModule(pg.GraphicsLayoutWidget):
    """A modular plot widget that can be customized and placed in the dashboard"""
    
    removed = pyqtSignal(object)  # Signal emitted when plot is removed
    
    def __init__(self, parent=None, plot_id=None, plot_type=None, title="Plot", config=None):
        super().__init__(parent)
        self.plot_id = plot_id if plot_id else id(self)  # Unique identifier
        self.plot_type = plot_type
        self.plot_title = title
        self.config = config or {}
        
        # Set the background and size
        self.setBackground('w')
        self.setMinimumSize(300, 200)
        
        # Create a plot area
        self.plot_item = self.addPlot(title=title)
        
        # Add controls as overlay
        self.controls = QWidget(self)
        self.controls_layout = QHBoxLayout(self.controls)
        self.controls_layout.setContentsMargins(5, 5, 5, 5)
        self.controls_layout.setSpacing(2)
        
        # Title label
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("background-color: rgba(255, 255, 255, 0.7); padding: 2px;")
        self.controls_layout.addWidget(self.title_label)
        
        # Spacer to push buttons to the right
        self.controls_layout.addStretch()
        
        # Settings button
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        self.settings_btn.setStyleSheet("background-color: rgba(255, 255, 255, 0.7);")
        self.settings_btn.clicked.connect(self.show_settings)
        self.controls_layout.addWidget(self.settings_btn)
        
        # Remove button with black x
        self.remove_btn = QToolButton()
        self.remove_btn.setText("✕")
        self.remove_btn.setStyleSheet("background-color: rgba(255, 255, 255, 0.7); color: black; font-weight: bold;")
        self.remove_btn.clicked.connect(self.remove_self)
        self.controls_layout.addWidget(self.remove_btn)
        
        # Position the controls at the top
        self.controls.setGeometry(0, 0, self.width(), 30)
        
        # Apply the configuration if available
        self.apply_config()
    
    def resizeEvent(self, event):
        """Handle resize event to reposition controls"""
        super().resizeEvent(event)
        # Make sure controls exist before setting geometry
        if hasattr(self, 'controls'):
            self.controls.setGeometry(0, 0, self.width(), 30)
    
    def apply_config(self):
        """Apply saved configuration to the plot"""
        if not self.config:
            return
        
        # Apply plot-specific settings
        if "title" in self.config:
            self.plot_title = self.config["title"]
            self.title_label.setText(self.plot_title)
            self.plot_item.setTitle(self.plot_title)
        
        if "grid" in self.config:
            self.plot_item.showGrid(x=self.config["grid"].get("x", True),
                                   y=self.config["grid"].get("y", True))
    
    def update_plot_data(self, data):
        """Update the plot with new data"""
        self.plot_item.clear()
        
        # Example: Simple line plot
        if isinstance(data, pd.Series):
            x = np.arange(len(data))
            y = data.values
            self.plot_item.plot(x, y, pen=pg.mkPen(color='b', width=2))
        elif isinstance(data, pd.DataFrame):
            for column in data.columns:
                y = data[column].values
                x = np.arange(len(y))
                self.plot_item.plot(x, y, pen=pg.mkPen(width=2), name=column)
        
        # Add legend if multiple series
        if isinstance(data, pd.DataFrame) and len(data.columns) > 1:
            self.plot_item.addLegend()
    
    def show_settings(self):
        """Open settings dialog for this plot"""
        settings_dialog = PlotSettingsDialog(self, self.config, self.plot_type)
        if settings_dialog.exec():
            # Update configuration based on dialog results
            self.config = settings_dialog.get_config()
            self.apply_config()
    
    def remove_self(self):
        """Remove this plot from the dashboard"""
        self.removed.emit(self)
        self.deleteLater()
    
    def get_config_dict(self):
        """Return a dictionary with configuration for saving"""
        return {
            "id": self.plot_id,
            "type": self.plot_type,
            "title": self.plot_title,
            "config": self.config
        }


class PlotSettingsDialog(QDialog):
    """Dialog for editing plot settings"""
    
    def __init__(self, parent=None, config=None, plot_type=None):
        super().__init__(parent)
        self.config = config or {}
        self.plot_type = plot_type
        
        self.setWindowTitle("Plot Settings")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Title settings
        title_group = QGroupBox("Title")
        title_layout = QHBoxLayout()
        title_group.setLayout(title_layout)
        
        self.title_edit = QLineEdit()
        if "title" in self.config:
            self.title_edit.setText(self.config["title"])
        else:
            self.title_edit.setText(f"{plot_type or 'Plot'}")
        title_layout.addWidget(self.title_edit)
        
        layout.addWidget(title_group)
        
        # Data source settings
        data_group = QGroupBox("Data Source")
        data_layout = QGridLayout()
        data_group.setLayout(data_layout)
        
        data_layout.addWidget(QLabel("Source:"), 0, 0)
        self.data_source = QComboBox()
        # These would be populated from the dashboard's data manager
        self.data_source.addItems(["Strategy 1", "Benchmark", "Custom"])
        data_layout.addWidget(self.data_source, 0, 1)
        
        data_layout.addWidget(QLabel("Column:"), 1, 0)
        self.data_column = QComboBox()
        # These would be populated based on the selected data source
        self.data_column.addItems(["Close", "Open", "High", "Low", "Volume"])
        data_layout.addWidget(self.data_column, 1, 1)
        
        layout.addWidget(data_group)
        
        # Visual settings
        visual_group = QGroupBox("Visual Settings")
        visual_layout = QGridLayout()
        visual_group.setLayout(visual_layout)
        
        # Line color
        visual_layout.addWidget(QLabel("Line Color:"), 0, 0)
        self.line_color_btn = QPushButton()
        self.line_color = self.config.get("line_color", "#0000FF")
        self.line_color_btn.setStyleSheet(f"background-color: {self.line_color}")
        self.line_color_btn.clicked.connect(self.choose_line_color)
        visual_layout.addWidget(self.line_color_btn, 0, 1)
        
        # Line width
        visual_layout.addWidget(QLabel("Line Width:"), 1, 0)
        self.line_width = QSpinBox()
        self.line_width.setRange(1, 10)
        self.line_width.setValue(self.config.get("line_width", 2))
        visual_layout.addWidget(self.line_width, 1, 1)
        
        # Grid options
        visual_layout.addWidget(QLabel("Show Grid:"), 2, 0)
        grid_layout = QHBoxLayout()
        
        self.grid_x = QCheckBox("X")
        self.grid_y = QCheckBox("Y")
        
        grid_config = self.config.get("grid", {"x": True, "y": True})
        self.grid_x.setChecked(grid_config.get("x", True))
        self.grid_y.setChecked(grid_config.get("y", True))
        
        grid_layout.addWidget(self.grid_x)
        grid_layout.addWidget(self.grid_y)
        visual_layout.addLayout(grid_layout, 2, 1)
        
        layout.addWidget(visual_group)
        
        # Plot-specific settings
        if self.plot_type:
            specific_group = QGroupBox(f"{self.plot_type} Settings")
            specific_layout = QGridLayout()
            specific_group.setLayout(specific_layout)
            
            # Add plot-specific settings based on plot type
            if self.plot_type == "Equity Curve":
                specific_layout.addWidget(QLabel("Show Benchmark:"), 0, 0)
                self.show_benchmark = QCheckBox()
                self.show_benchmark.setChecked(self.config.get("show_benchmark", False))
                specific_layout.addWidget(self.show_benchmark, 0, 1)
                
                specific_layout.addWidget(QLabel("Benchmark:"), 1, 0)
                self.benchmark_source = QComboBox()
                # Would be populated from dashboard's data manager
                self.benchmark_source.addItems(["S&P 500", "Nasdaq", "Custom"])
                specific_layout.addWidget(self.benchmark_source, 1, 1)
            
            elif self.plot_type == "Rolling Sharpe Ratio":
                specific_layout.addWidget(QLabel("Window (days):"), 0, 0)
                self.window_size = QSpinBox()
                self.window_size.setRange(5, 500)
                self.window_size.setValue(self.config.get("window_size", 252))
                specific_layout.addWidget(self.window_size, 0, 1)
            
            layout.addWidget(specific_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
    
    def choose_line_color(self):
        """Open color picker for line color"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.line_color = color.name()
            self.line_color_btn.setStyleSheet(f"background-color: {self.line_color}")
    
    def get_config(self):
        """Return the updated configuration"""
        config = {
            "title": self.title_edit.text(),
            "line_color": self.line_color,
            "line_width": self.line_width.value(),
            "grid": {
                "x": self.grid_x.isChecked(),
                "y": self.grid_y.isChecked()
            },
            "data_source": self.data_source.currentText(),
            "data_column": self.data_column.currentText()
        }
        
        # Add plot-specific settings
        if self.plot_type == "Equity Curve":
            config["show_benchmark"] = self.show_benchmark.isChecked()
            config["benchmark_source"] = self.benchmark_source.currentText()
        elif self.plot_type == "Rolling Sharpe Ratio":
            config["window_size"] = self.window_size.value()
        
        return config


class PlotPalette(QTreeWidget):
    """Widget displaying available plot types categorized by function"""
    
    def __init__(self, parent=None, plot_registry=None):
        super().__init__(parent)
        self.plot_registry = plot_registry or PlotRegistry()
        
        # Set up the tree widget
        self.setHeaderLabel("Available Plots")
        self.setDragEnabled(True)
        
        # Populate the tree with plot types
        self.populate()
    
    def populate(self):
        """Populate the tree with available plot types"""
        self.clear()
        
        # Create categories
        performance_category = QTreeWidgetItem(self, ["Performance"])
        risk_category = QTreeWidgetItem(self, ["Risk Analysis"])
        portfolio_category = QTreeWidgetItem(self, ["Portfolio Optimization"])
        
        # Categorize plot types
        plot_types = self.plot_registry.get_plot_types()
        for plot_type in plot_types:
            item = QTreeWidgetItem([plot_type])
            
            # Add to appropriate category
            if "Equity" in plot_type or "Drawdown" in plot_type or "Sharpe" in plot_type or "Monthly Returns" in plot_type:
                performance_category.addChild(item)
            elif "VaR" in plot_type or "Risk" in plot_type or "Return Distribution" in plot_type:
                risk_category.addChild(item)
            elif "Efficient" in plot_type or "Portfolio" in plot_type:
                portfolio_category.addChild(item)
            else:
                self.addTopLevelItem(item)
        
        # Expand all categories
        self.expandAll()
    
    def mousePressEvent(self, event):
        """Handle mouse press event for dragging"""
        super().mousePressEvent(event)
        
        if event.button() == Qt.MouseButton.LeftButton:
            # Get the item under the cursor
            item = self.itemAt(event.pos())
            if item and item.parent():  # Only allow dragging leaf nodes
                # Store the plot type
                self.drag_plot_type = item.text(0)
                
                # Start drag operation
                drag = QDrag(self)
                mime_data = QMimeData()
                mime_data.setText(self.drag_plot_type)
                drag.setMimeData(mime_data)
                
                # Create a pixmap for the drag icon
                pixmap = QPixmap(100, 30)
                pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(pixmap)
                painter.drawText(0, 20, self.drag_plot_type)
                painter.end()
                
                drag.setPixmap(pixmap)
                drag.exec(Qt.DropAction.CopyAction)


class DashboardArea(QWidget):
    """Widget containing the dashboard grid where plots are arranged"""
    
    def __init__(self, parent=None, data_manager=None, plot_registry=None):
        super().__init__(parent)
        self.data_manager = data_manager or DataManager()
        self.plot_registry = plot_registry or PlotRegistry()
        
        # Set up layout
        self.layout = QGridLayout(self)
        self.layout.setSpacing(10)
        
        # Track plots
        self.plots = []
        self.grid_positions = {}  # Map plot ID to grid position
        self.current_row = 0
        self.current_col = 0
        self.max_cols = 2
        
        # Currently active data source
        self.active_data_source = None
        
        # Accept drops
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event):
        """Handle drag enter event"""
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        """Handle drop event"""
        if event.mimeData().hasText():
            plot_type = event.mimeData().text()
            
            # Add the plot to the grid
            self.add_plot(plot_type)
            
            event.accept()
        else:
            event.ignore()
    
    def add_plot(self, plot_type, config=None):
        """Add a new plot to the dashboard"""
        # Create the plot
        plot = EnhancedGraphModule(plot_type=plot_type, title=plot_type, config=config)
        plot.removed.connect(self.remove_plot)
        
        # Add to grid layout
        grid_pos = (self.current_row, self.current_col)
        self.layout.addWidget(plot, *grid_pos)
        self.grid_positions[plot.plot_id] = grid_pos
        
        # Update grid position for next plot
        self.current_col += 1
        if self.current_col >= self.max_cols:
            self.current_col = 0
            self.current_row += 1
        
        self.plots.append(plot)
        
        # If there's active data, update the plot with it
        if self.active_data_source:
            self.update_plot_with_source(plot, self.active_data_source)
        else:
            # No data available, generate sample data
            self.update_plot_with_sample_data(plot)
        
        return plot
    
    def update_plot_with_source(self, plot, source_name):
        """Update a plot with data from a specific source"""
        # Get prepared data for this source
        prepared_data = self.data_manager.get_prepared_data(source_name)
        if not prepared_data:
            # If no prepared data, use sample data
            self.update_plot_with_sample_data(plot)
            return
        
        # Get plot info
        plot_info = self.plot_registry.get_plot_info(plot.plot_type)
        if not plot_info:
            return
        
        # Check if we have all required data
        required_data = plot_info['required_data']
        missing_data = [req for req in required_data if req not in prepared_data]
        
        if missing_data:
            # Try to generate missing data
            for req in missing_data:
                if req == 'returns' and 'equity' in prepared_data:
                    # Generate returns from equity
                    equity = prepared_data['equity']
                    prepared_data['returns'] = equity.pct_change().dropna()
                elif req == 'returns_matrix' and 'equity' in prepared_data:
                    # For single-asset data, create a dummy returns matrix with just this asset
                    returns = prepared_data.get('returns')
                    if returns is None:
                        returns = prepared_data['equity'].pct_change().dropna()
                    prepared_data['returns_matrix'] = pd.DataFrame(returns, columns=['Asset'])
                elif req == 'drawdown' and 'returns' in prepared_data:
                    # Generate drawdown series from returns
                    returns = prepared_data['returns']
                    cumulative_returns = (1 + returns).cumprod()
                    prepared_data['drawdown'] = (cumulative_returns / cumulative_returns.cummax()) - 1
        
        # If we still have missing data after trying to generate it, use sample data
        missing_data = [req for req in required_data if req not in prepared_data]
        if missing_data:
            self.update_plot_with_sample_data(plot)
            return
            
        # Extract required data for the plot
        plot_data = {req: prepared_data[req] for req in required_data}
        
        # Get default parameters
        parameters = plot_info['parameters']
        kwargs = {}
        for param_name, param_info in parameters.items():
            if 'default' in param_info:
                kwargs[param_name] = param_info['default']
        
        # Apply configuration parameters if available
        if plot.config and 'parameters' in plot.config:
            for param_name, value in plot.config['parameters'].items():
                kwargs[param_name] = value
                
        try:
            # Create the plot figure using the plot registry function
            figure = self.plot_registry.create_plot(plot.plot_type, plot_data, **kwargs)
            
            # Convert matplotlib figure to PyQtGraph plot data
            self._update_pyqtgraph_from_matplotlib(plot, figure)
        except Exception as e:
            print(f"Error updating plot {plot.plot_type}: {e}")
            self.update_plot_with_sample_data(plot)
    
    def _update_pyqtgraph_from_matplotlib(self, plot_widget, matplotlib_figure):
        """Convert matplotlib figure to data for PyQtGraph plot"""
        # This is a simplified conversion that extracts data from the first axes of the matplotlib figure
        # For a complete solution, you would need to handle multiple axes, different plot types, etc.
        try:
            # Extract data from the first axes
            axes = matplotlib_figure.axes[0]
            
            # Clear existing plot items
            plot_widget.plot_item.clear()
            
            # Get all line plots from the axes
            for line in axes.get_lines():
                x_data = line.get_xdata()
                y_data = line.get_ydata()
                
                # Convert data to numpy arrays if needed
                if not isinstance(x_data, np.ndarray):
                    x_data = np.array(x_data)
                if not isinstance(y_data, np.ndarray):
                    y_data = np.array(y_data)
                
                # Get color and create pen
                color = line.get_color()
                if isinstance(color, tuple) and len(color) == 3:
                    color = tuple(int(c * 255) for c in color) + (255,)  # RGBA
                elif isinstance(color, str):
                    # Convert matplotlib color string to RGBA tuple
                    from matplotlib.colors import to_rgba
                    rgba = to_rgba(color)
                    color = tuple(int(c * 255) for c in rgba)
                
                pen = pg.mkPen(color=color, width=line.get_linewidth())
                
                # Add to plot
                plot_widget.plot_item.plot(x_data, y_data, pen=pen, name=line.get_label())
            
            # Update plot title and labels
            plot_widget.plot_item.setTitle(axes.get_title())
            plot_widget.plot_item.setLabel('bottom', axes.get_xlabel())
            plot_widget.plot_item.setLabel('left', axes.get_ylabel())
            
            # Add legend if needed
            if axes.get_legend():
                plot_widget.plot_item.addLegend()
            
            # Close matplotlib figure to free resources
            plt.close(matplotlib_figure)
            
        except Exception as e:
            print(f"Error converting matplotlib figure to PyQtGraph: {e}")
            # Fall back to sample data
            self.update_plot_with_sample_data(plot_widget)
    
    def update_plot_with_sample_data(self, plot):
        """Update a plot with sample data if no real data is available"""
        # Generate sample data based on plot type
        plot.plot_item.clear()
        
        if plot.plot_type == "Equity Curve":
            # Sample equity curve
            x = np.arange(100)
            y = 100 * (1 + 0.001 * np.cumsum(np.random.normal(0.001, 0.01, 100)))
            plot.plot_item.plot(x, y, pen=pg.mkPen(color='b', width=2))
            
        elif plot.plot_type == "Drawdown Chart":
            # Sample drawdown chart
            x = np.arange(100)
            drawdown = -0.01 * np.abs(np.cumsum(np.random.normal(0, 1, 100)))
            drawdown = np.maximum(drawdown, -0.3)  # Cap at -30%
            plot.plot_item.plot(x, drawdown, pen=pg.mkPen(color='r', width=2))
            
        elif plot.plot_type == "Monthly Returns Heatmap":
            # For heatmap, we need a different approach since PyQtGraph doesn't directly support heatmaps
            # Create a colorful grid as placeholder
            img = np.random.normal(0, 1, (12, 5))  # 12 months x 5 years
            colormap = pg.colormap.get('viridis')
            image_item = pg.ImageItem(img)
            image_item.setLookupTable(colormap.getLookupTable())
            plot.plot_item.addItem(image_item)
            
        elif plot.plot_type == "Rolling Sharpe Ratio":
            # Sample rolling sharpe ratio
            x = np.arange(100)
            y = np.cumsum(np.random.normal(0, 0.2, 100))
            y = y - np.min(y)  # Make all positive
            y = y / np.max(y) * 3  # Scale to reasonable Sharpe values
            plot.plot_item.plot(x, y, pen=pg.mkPen(color='g', width=2))
            
        elif "VaR" in plot.plot_type:
            # Sample VaR distribution
            x = np.linspace(-0.05, 0.05, 100)
            y = np.exp(-(x-0.001)**2/(2*0.01**2)) / (0.01 * np.sqrt(2*np.pi))
            plot.plot_item.plot(x, y, pen=pg.mkPen(color='b', width=2))
            
            # Add VaR lines
            var_95 = -0.02
            plot.plot_item.addLine(x=var_95, pen=pg.mkPen(color='r', width=2, style=Qt.PenStyle.DashLine))
            
        elif "Efficient Frontier" in plot.plot_type:
            # Sample efficient frontier
            risk = np.linspace(0.05, 0.3, 100)
            return_values = 0.02 + 0.3 * risk + 0.05 * np.random.random(100)
            plot.plot_item.plot(risk, return_values, pen=pg.mkPen(color='b', width=2))
            
            # Add points
            scatter = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(255, 0, 0, 255))
            scatter.addPoints([0.1, 0.2], [0.05, 0.12])
            plot.plot_item.addItem(scatter)
            
        else:
            # Generic line plot for other plot types
            x = np.arange(100)
            y = np.cumsum(np.random.normal(0, 1, 100))
            plot.plot_item.plot(x, y, pen=pg.mkPen(color='b', width=2))
    
    def set_active_data_source(self, source_name):
        """Set the active data source and update all plots"""
        self.active_data_source = source_name
        
        # Update all existing plots with the new data source
        for plot in self.plots:
            self.update_plot_with_source(plot, source_name)
    
    def remove_plot(self, plot):
        """Remove a plot from the dashboard"""
        if plot in self.plots:
            self.plots.remove(plot)
            self.layout.removeWidget(plot)
            
            # Delete from grid positions
            if plot.plot_id in self.grid_positions:
                del self.grid_positions[plot.plot_id]
            
            # Rearrange the remaining plots
            self.rearrange_plots()
    
    def rearrange_plots(self):
        """Rearrange all plots in the grid"""
        # Remove all plots from grid layout
        for plot in self.plots:
            self.layout.removeWidget(plot)
        
        # Reset grid positions
        self.grid_positions = {}
        self.current_row = 0
        self.current_col = 0
        
        # Re-add plots to layout
        for plot in self.plots:
            grid_pos = (self.current_row, self.current_col)
            self.layout.addWidget(plot, *grid_pos)
            self.grid_positions[plot.plot_id] = grid_pos
            
            # Update grid position for next plot
            self.current_col += 1
            if self.current_col >= self.max_cols:
                self.current_col = 0
                self.current_row += 1
    
    def get_dashboard_config(self):
        """Get the dashboard configuration for saving"""
        plot_configs = []
        for plot in self.plots:
            config = plot.get_config_dict()
            # Add grid position
            if plot.plot_id in self.grid_positions:
                row, col = self.grid_positions[plot.plot_id]
                config['position'] = {'row': row, 'col': col}
            plot_configs.append(config)
        
        return {
            'plots': plot_configs,
            'max_cols': self.max_cols,
            'active_data_source': self.active_data_source
        }
    
    def load_dashboard_config(self, config):
        """Load dashboard from configuration"""
        if not config or 'plots' not in config:
            return
        
        # Clear existing plots
        for plot in self.plots[:]:
            self.remove_plot(plot)
        
        # Set max columns
        self.max_cols = config.get('max_cols', 2)
        
        # Set active data source
        if 'active_data_source' in config:
            self.active_data_source = config['active_data_source']
        
        # Add plots from config
        for plot_config in config['plots']:
            plot_type = plot_config.get('type')
            if not plot_type:
                continue
            
            # Create the plot
            plot = self.add_plot(plot_type, plot_config.get('config'))
            
            # Set position if specified
            if 'position' in plot_config:
                pos = plot_config['position']
                if plot.plot_id in self.grid_positions:
                    del self.grid_positions[plot.plot_id]
                self.layout.removeWidget(plot)
                
                row, col = pos.get('row', 0), pos.get('col', 0)
                self.layout.addWidget(plot, row, col)
                self.grid_positions[plot.plot_id] = (row, col)

    def load_data(self):
        """Load data from a file and add it to the data manager."""
        # Open file dialog to select data file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Data File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                # Load the data into the data manager
                source_name = self.data_manager.load_csv(file_path)
                
                if source_name:
                    # Update data source selector
                    self.update_data_sources()
                    
                    # Select the newly loaded data source
                    index = self.data_source_selector.findText(source_name)
                    if index >= 0:
                        self.data_source_selector.setCurrentIndex(index)
                    
                    QMessageBox.information(
                        self,
                        "Data Loaded",
                        f"Successfully loaded data from {os.path.basename(file_path)}"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Load Error",
                        "Failed to load data from the selected file."
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while loading the data: {str(e)}"
                )

    def update_data_sources(self):
        """Update the data source selector with available data sources."""
        # Get list of data sources
        sources = self.data_manager.get_data_source_names()
        
        # Save current selection
        current_text = self.data_source_selector.currentText()
        
        # Clear and repopulate
        self.data_source_selector.clear()
        self.data_source_selector.addItems(sources)
        
        # Restore selection if possible
        if current_text:
            index = self.data_source_selector.findText(current_text)
            if index >= 0:
                self.data_source_selector.setCurrentIndex(index)
            elif self.data_source_selector.count() > 0:
                # Otherwise select the first item
                self.data_source_selector.setCurrentIndex(0)

    def on_data_source_changed(self, source_name):
        """Handle changes to the selected data source."""
        if source_name:
            # Set the active data source in the dashboard area
            self.dashboard_area.set_active_data_source(source_name)

    def refresh_all_charts(self):
        """Refresh all charts with current data."""
        current_source = self.data_source_selector.currentText()
        if current_source:
            self.dashboard_area.set_active_data_source(current_source)
            QMessageBox.information(
                self,
                "Refresh Complete",
                "All charts have been refreshed with the current data."
            )
        else:
            QMessageBox.warning(
                self,
                "No Data Selected",
                "Please select a data source to refresh charts."
            )

    def save_configuration(self):
        """Save the current dashboard configuration."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Dashboard Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                # Get configuration from dashboard area
                dashboard_config = self.dashboard_area.get_dashboard_config()
                
                # Save configuration to file
                with open(file_path, 'w') as f:
                    import json
                    json.dump(dashboard_config, f, indent=4)
                
                QMessageBox.information(
                    self,
                    "Save Complete",
                    f"Dashboard configuration saved to {os.path.basename(file_path)}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while saving the configuration: {str(e)}"
                )

    def load_configuration(self):
        """Load a dashboard configuration from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Dashboard Configuration",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                # Load configuration from file
                with open(file_path, 'r') as f:
                    import json
                    dashboard_config = json.load(f)
                
                # Apply configuration to dashboard area
                self.dashboard_area.load_dashboard_config(dashboard_config)
                
                # Update active data source if specified
                if 'active_data_source' in dashboard_config and dashboard_config['active_data_source']:
                    source_name = dashboard_config['active_data_source']
                    index = self.data_source_selector.findText(source_name)
                    if index >= 0:
                        self.data_source_selector.setCurrentIndex(index)
                
                QMessageBox.information(
                    self,
                    "Load Complete",
                    f"Dashboard configuration loaded from {os.path.basename(file_path)}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while loading the configuration: {str(e)}"
                )

    def load_config_from_env(self):
        """Load configuration from environment variable."""
        config_path = os.environ.get('ALGO_DASHBOARD_CONFIG')
        if config_path and os.path.exists(config_path):
            try:
                # Load configuration from file
                with open(config_path, 'r') as f:
                    import json
                    dashboard_config = json.load(f)
                
                # Apply configuration to dashboard area
                self.dashboard_area.load_dashboard_config(dashboard_config)
                
                print(f"Loaded configuration from environment variable: {config_path}")
            except Exception as e:
                print(f"Error loading configuration from environment: {e}")

    def load_data_from_env(self):
        """Load data from directory specified in environment variable."""
        data_dir = os.environ.get('ALGO_DASHBOARD_DATA_DIR')
        if data_dir and os.path.exists(data_dir):
            try:
                # Look for CSV files in the directory
                import glob
                csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
                
                for csv_file in csv_files:
                    source_name = self.data_manager.load_csv(csv_file)
                    if source_name:
                        print(f"Loaded data from: {csv_file}")
                
                # Update data source selector
                self.update_data_sources()
                
                # Select the first data source if available
                if self.data_source_selector.count() > 0:
                    self.data_source_selector.setCurrentIndex(0)
                    
                print(f"Loaded data from environment variable directory: {data_dir}")
            except Exception as e:
                print(f"Error loading data from environment: {e}")

def launch_dashboard():
    """Launch the AlgoSystem Dashboard application."""
    import sys
    
    class DashboardApp(QMainWindow):
        def __init__(self):
            super().__init__()
            # Set window properties
            self.setWindowTitle("AlgoSystem Dashboard")
            self.resize(1200, 800)
            
            # Initialize core components
            self.plot_registry = PlotRegistry()  # Registry of available chart types
            self.data_manager = DataManager()    # Handles loading and preprocessing data
            
            # Set up the main layout
            self.central_widget = QWidget()
            self.setCentralWidget(self.central_widget)
            self.main_layout = QVBoxLayout(self.central_widget)
            
            # Create toolbar with buttons and data source selector
            toolbar_layout = QHBoxLayout()
            
            # Add Load Data button
            self.load_data_btn = QPushButton("Load Data")
            self.load_data_btn.clicked.connect(self.load_data)
            toolbar_layout.addWidget(self.load_data_btn)
            
            # Add data source selector dropdown
            toolbar_layout.addWidget(QLabel("Data Source:"))
            self.data_source_selector = QComboBox()
            self.data_source_selector.currentTextChanged.connect(self.on_data_source_changed)
            toolbar_layout.addWidget(self.data_source_selector)
            
            # Add Refresh Charts button
            self.refresh_btn = QPushButton("Refresh Charts")
            self.refresh_btn.clicked.connect(self.refresh_all_charts)
            toolbar_layout.addWidget(self.refresh_btn)
            
            toolbar_layout.addStretch()  # Push remaining buttons to the right
            
            # Add Save/Load Configuration buttons
            self.save_config_btn = QPushButton("Save Configuration")
            self.save_config_btn.clicked.connect(self.save_configuration)
            toolbar_layout.addWidget(self.save_config_btn)
            
            self.load_config_btn = QPushButton("Load Configuration")
            self.load_config_btn.clicked.connect(self.load_configuration)
            toolbar_layout.addWidget(self.load_config_btn)
            
            self.main_layout.addLayout(toolbar_layout)
            
            # Create split view with plot palette on left and dashboard area on right
            self.splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # Add plot palette (left side)
            self.plot_palette = PlotPalette(plot_registry=self.plot_registry)
            self.splitter.addWidget(self.plot_palette)
            
            # Add dashboard area (right side)
            self.dashboard_area = DashboardArea(
                data_manager=self.data_manager, 
                plot_registry=self.plot_registry
            )
            self.splitter.addWidget(self.dashboard_area)
            
            # Set initial sizes for the splitter (palette vs. dashboard)
            self.splitter.setSizes([300, 900])
            
            self.main_layout.addWidget(self.splitter)
            
            # Load configuration from environment variable if available
            self.load_config_from_env()
            
            # Load data from directory if available
            self.load_data_from_env()
            
        # ADDING MISSING METHODS
        def load_data(self):
            """Load data from a file and add it to the data manager."""
            # Open file dialog to select data file
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Data File",
                "",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if file_path:
                try:
                    # Load the data into the data manager
                    source_name = self.data_manager.load_csv(file_path)
                    
                    if source_name:
                        # Update data source selector
                        self.update_data_sources()
                        
                        # Select the newly loaded data source
                        index = self.data_source_selector.findText(source_name)
                        if index >= 0:
                            self.data_source_selector.setCurrentIndex(index)
                        
                        QMessageBox.information(
                            self,
                            "Data Loaded",
                            f"Successfully loaded data from {os.path.basename(file_path)}"
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Load Error",
                            "Failed to load data from the selected file."
                        )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"An error occurred while loading the data: {str(e)}"
                    )

        def update_data_sources(self):
            """Update the data source selector with available data sources."""
            # Get list of data sources
            sources = self.data_manager.get_data_source_names()
            
            # Save current selection
            current_text = self.data_source_selector.currentText()
            
            # Clear and repopulate
            self.data_source_selector.clear()
            self.data_source_selector.addItems(sources)
            
            # Restore selection if possible
            if current_text:
                index = self.data_source_selector.findText(current_text)
                if index >= 0:
                    self.data_source_selector.setCurrentIndex(index)
                elif self.data_source_selector.count() > 0:
                    # Otherwise select the first item
                    self.data_source_selector.setCurrentIndex(0)

        def on_data_source_changed(self, source_name):
            """Handle changes to the selected data source."""
            if source_name:
                # Set the active data source in the dashboard area
                self.dashboard_area.set_active_data_source(source_name)

        def refresh_all_charts(self):
            """Refresh all charts with current data."""
            current_source = self.data_source_selector.currentText()
            if current_source:
                self.dashboard_area.set_active_data_source(current_source)
                QMessageBox.information(
                    self,
                    "Refresh Complete",
                    "All charts have been refreshed with the current data."
                )
            else:
                QMessageBox.warning(
                    self,
                    "No Data Selected",
                    "Please select a data source to refresh charts."
                )

        def save_configuration(self):
            """Save the current dashboard configuration."""
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Dashboard Configuration",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                try:
                    # Get configuration from dashboard area
                    dashboard_config = self.dashboard_area.get_dashboard_config()
                    
                    # Save configuration to file
                    with open(file_path, 'w') as f:
                        import json
                        json.dump(dashboard_config, f, indent=4)
                    
                    QMessageBox.information(
                        self,
                        "Save Complete",
                        f"Dashboard configuration saved to {os.path.basename(file_path)}"
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"An error occurred while saving the configuration: {str(e)}"
                    )

        def load_configuration(self):
            """Load a dashboard configuration from a file."""
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Dashboard Configuration",
                "",
                "JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                try:
                    # Load configuration from file
                    with open(file_path, 'r') as f:
                        import json
                        dashboard_config = json.load(f)
                    
                    # Apply configuration to dashboard area
                    self.dashboard_area.load_dashboard_config(dashboard_config)
                    
                    # Update active data source if specified
                    if 'active_data_source' in dashboard_config and dashboard_config['active_data_source']:
                        source_name = dashboard_config['active_data_source']
                        index = self.data_source_selector.findText(source_name)
                        if index >= 0:
                            self.data_source_selector.setCurrentIndex(index)
                    
                    QMessageBox.information(
                        self,
                        "Load Complete",
                        f"Dashboard configuration loaded from {os.path.basename(file_path)}"
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Error",
                        f"An error occurred while loading the configuration: {str(e)}"
                    )

        def load_config_from_env(self):
            """Load configuration from environment variable."""
            config_path = os.environ.get('ALGO_DASHBOARD_CONFIG')
            if config_path and os.path.exists(config_path):
                try:
                    # Load configuration from file
                    with open(config_path, 'r') as f:
                        import json
                        dashboard_config = json.load(f)
                    
                    # Apply configuration to dashboard area
                    self.dashboard_area.load_dashboard_config(dashboard_config)
                    
                    print(f"Loaded configuration from environment variable: {config_path}")
                except Exception as e:
                    print(f"Error loading configuration from environment: {e}")

        def load_data_from_env(self):
            """Load data from directory specified in environment variable."""
            data_dir = os.environ.get('ALGO_DASHBOARD_DATA_DIR')
            if data_dir and os.path.exists(data_dir):
                try:
                    # Look for CSV files in the directory
                    import glob
                    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
                    
                    for csv_file in csv_files:
                        source_name = self.data_manager.load_csv(csv_file)
                        if source_name:
                            print(f"Loaded data from: {csv_file}")
                    
                    # Update data source selector
                    self.update_data_sources()
                    
                    # Select the first data source if available
                    if self.data_source_selector.count() > 0:
                        self.data_source_selector.setCurrentIndex(0)
                        
                    print(f"Loaded data from environment variable directory: {data_dir}")
                except Exception as e:
                    print(f"Error loading data from environment: {e}")
    
    # Create and run the application
    app = QApplication(sys.argv)
    dashboard = DashboardApp()
    dashboard.show()
    sys.exit(app.exec())


