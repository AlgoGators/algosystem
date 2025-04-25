import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

# Import visualization functions
from algosystem.backtesting.visualization import (
    create_equity_chart,
    create_drawdown_chart,
    create_monthly_returns_heatmap,
    create_rolling_sharpe_chart
)

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


# Utility function to create a plot registry with default plots
def create_plot_registry():
    """Create and return a plot registry with default plots"""
    return PlotRegistry()