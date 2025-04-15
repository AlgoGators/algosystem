import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import FuncFormatter

def create_equity_chart(equity_curve, benchmark=None, figsize=(10, 6)):
    """Create an equity curve chart with optional benchmark comparison."""
    plt.figure(figsize=figsize)
    
    # Plot equity curve
    plt.plot(equity_curve, label='Strategy', linewidth=2)
    
    # Plot benchmark if provided
    if benchmark is not None:
        # Reindex to match equity curve
        benchmark = benchmark.reindex(equity_curve.index, method='ffill')
        # Normalize to same starting value
        benchmark = benchmark * (equity_curve.iloc[0] / benchmark.iloc[0])
        plt.plot(benchmark, label='Benchmark', linewidth=2, alpha=0.7)
    
    # Add buy and hold line
    buy_hold = pd.Series(data=equity_curve.iloc[0], index=equity_curve.index)
    plt.plot(buy_hold, 'k--', label='Initial Capital', linewidth=1, alpha=0.5)
    
    # Format and label
    plt.grid(alpha=0.3)
    plt.xlabel('Date')
    plt.ylabel('Equity ($)')
    plt.title('Equity Curve')
    plt.legend()
    
    return plt.gcf()

def create_drawdown_chart(equity_curve, figsize=(10, 6)):
    """Create a drawdown chart from the equity curve."""
    # Calculate drawdown
    returns = equity_curve.pct_change().dropna()
    cum_returns = (1 + returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    
    plt.figure(figsize=figsize)
    plt.fill_between(drawdown.index, 0, drawdown, color='red', alpha=0.3)
    plt.plot(drawdown, color='red', linewidth=1)
    
    # Format and label
    plt.grid(alpha=0.3)
    plt.xlabel('Date')
    plt.ylabel('Drawdown (%)')
    plt.title('Drawdown Chart')
    
    # Format y-axis as percentage
    plt.gca().yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.0%}'))
    
    return plt.gcf()

def create_monthly_returns_heatmap(equity_curve, figsize=(10, 6)):
    """Create a monthly returns heatmap."""
    # Calculate monthly returns
    monthly_returns = equity_curve.resample('M').last().pct_change().dropna()
    
    # Transform to a 12x? matrix (years x months)
    returns_matrix = monthly_returns.groupby([monthly_returns.index.year, monthly_returns.index.month]).first().unstack()
    
    plt.figure(figsize=figsize)
    
    # Create heatmap
    sns.heatmap(returns_matrix, annot=True, fmt='.1%', cmap='RdYlGn',
                cbar_kws={'label': 'Monthly Return'}, linewidths=0.5)
    
    plt.title('Monthly Returns Heatmap')
    plt.xlabel('Month')
    plt.ylabel('Year')
    
    return plt.gcf()

def create_rolling_sharpe_chart(equity_curve, window=252, figsize=(10, 6)):
    """Create a rolling Sharpe ratio chart."""
    returns = equity_curve.pct_change().dropna()
    
    # Calculate rolling Sharpe ratio (assuming risk-free rate = 0)
    rolling_return = returns.rolling(window).mean() * 252
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)
    rolling_sharpe = rolling_return / rolling_vol
    
    plt.figure(figsize=figsize)
    plt.plot(rolling_sharpe, linewidth=2)
    
    # Add horizontal line at Sharpe = 1
    plt.axhline(y=1, color='green', linestyle='--', alpha=0.7)
    plt.axhline(y=0, color='red', linestyle='--', alpha=0.7)
    
    # Format and label
    plt.grid(alpha=0.3)
    plt.xlabel('Date')
    plt.ylabel('Sharpe Ratio (Rolling)')
    plt.title(f'Rolling {window//252}-Year Sharpe Ratio')
    
    return plt.gcf()

def create_performance_dashboard(backtest_results, benchmark=None, save_path=None):
    """
    Create a comprehensive performance dashboard from backtest results.
    
    Parameters:
    -----------
    backtest_results : dict
        Dictionary containing backtest results
    benchmark : pandas.Series, optional
        Benchmark price series for comparison
    save_path : str, optional
        Path to save the dashboard figure
        
    Returns:
    --------
    fig : matplotlib.Figure
        The dashboard figure
    """
    # Extract equity curve
    equity = backtest_results['equity']
    
    # Set up figure and grid
    fig = plt.figure(figsize=(15, 12))
    gs = GridSpec(3, 2, figure=fig)
    
    # Equity curve
    ax1 = fig.add_subplot(gs[0, :])
    equity_plot = create_equity_chart(equity, benchmark)
    equity_plot_ax = equity_plot.axes[0]
    equity_plot_ax.get_figure().delaxes(equity_plot_ax)
    ax1.plot(equity, label='Strategy', linewidth=2)
    
    if benchmark is not None:
        # Normalize to same starting value
        benchmark = benchmark.reindex(equity.index, method='ffill')
        benchmark = benchmark * (equity.iloc[0] / benchmark.iloc[0])
        ax1.plot(benchmark, label='Benchmark', linewidth=2, alpha=0.7)
    
    ax1.axhline(y=equity.iloc[0], color='k', linestyle='--', linewidth=1, alpha=0.5, label='Initial Capital')
    ax1.set_title('Equity Curve')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Equity ($)')
    ax1.grid(alpha=0.3)
    ax1.legend()
    
    # Drawdown chart
    ax2 = fig.add_subplot(gs[1, 0])
    returns = equity.pct_change().dropna()
    cum_returns = (1 + returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    
    ax2.fill_between(drawdown.index, 0, drawdown, color='red', alpha=0.3)
    ax2.plot(drawdown, color='red', linewidth=1)
    ax2.set_title('Drawdown Chart')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Drawdown (%)')
    ax2.grid(alpha=0.3)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.0%}'))
    
    # Rolling Sharpe ratio
    ax3 = fig.add_subplot(gs[1, 1])
    window = min(252, len(returns) // 2)  # Use 1 year or half the data length
    rolling_return = returns.rolling(window).mean() * 252
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)
    rolling_sharpe = rolling_return / rolling_vol
    
    ax3.plot(rolling_sharpe, linewidth=2)
    ax3.axhline(y=1, color='green', linestyle='--', alpha=0.7)
    ax3.axhline(y=0, color='red', linestyle='--', alpha=0.7)
    ax3.set_title(f'Rolling Sharpe Ratio ({window} days)')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Sharpe Ratio')
    ax3.grid(alpha=0.3)
    
    # Monthly returns heatmap
    ax4 = fig.add_subplot(gs[2, :])
    monthly_returns = equity.resample('M').last().pct_change().dropna()
    
    # Create more meaningful representation if very few months
    if len(monthly_returns) <= 6:
        # Use bar chart for few months
        ax4.bar(monthly_returns.index, monthly_returns, color='blue', alpha=0.7)
        ax4.set_title('Monthly Returns')
        ax4.set_xlabel('Date')
        ax4.set_ylabel('Return (%)')
        ax4.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.1%}'))
        ax4.grid(alpha=0.3)
    else:
        # Use heatmap for many months
        years = monthly_returns.index.year.unique()
        months = range(1, 13)
        
        # Create a matrix of returns with years as rows and months as columns
        returns_matrix = pd.DataFrame(index=years, columns=months, dtype=float)
        
        for date, ret in monthly_returns.items():
            returns_matrix.loc[date.year, date.month] = ret
        
        sns.heatmap(returns_matrix, annot=True, fmt='.1%', cmap='RdYlGn', 
                  ax=ax4, cbar_kws={'label': 'Return'}, linewidths=0.5)
        ax4.set_title('Monthly Returns Heatmap')
        ax4.set_xlabel('Month')
        ax4.set_ylabel('Year')
    
    # Add key metrics as text
    from ..backtesting.metrics import calculate_metrics
    metrics = calculate_metrics(equity)
    
    # Calculate additional stats
    total_return = metrics['total_return']
    annual_return = metrics['annual_return']
    sharpe = metrics['sharpe_ratio']
    max_dd = metrics['max_drawdown']
    volatility = metrics['volatility']
    
    # Create a text box with metrics
    metrics_text = (
        f"Total Return: {total_return:.2%}\n"
        f"Annual Return: {annual_return:.2%}\n"
        f"Sharpe Ratio: {sharpe:.2f}\n"
        f"Max Drawdown: {max_dd:.2%}\n"
        f"Volatility: {volatility:.2%}"
    )
    
    fig.text(0.02, 0.02, metrics_text, fontsize=10, 
             bbox=dict(facecolor='lightgray', alpha=0.5))
    
    # Add title
    strategy_name = backtest_results.get('strategy_name', 'Strategy Backtest')
    fig.suptitle(strategy_name, fontsize=16)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])
    
    # Save if path provided
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    
    return fig

def create_simple_performance_chart(backtest_results, output_path=None):
    """Create a simple performance chart for command-line usage."""
    equity = backtest_results['equity']
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # Equity curve
    ax1.plot(equity, linewidth=2)
    ax1.set_title('Equity Curve')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Equity ($)')
    ax1.grid(alpha=0.3)
    
    # Drawdown
    returns = equity.pct_change().dropna()
    cum_returns = (1 + returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    
    ax2.fill_between(drawdown.index, 0, drawdown, color='red', alpha=0.3)
    ax2.plot(drawdown, color='red', linewidth=1)
    ax2.set_title('Drawdown')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Drawdown (%)')
    ax2.grid(alpha=0.3)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f'{y:.0%}'))
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close(fig)
        return output_path
    else:
        return fig
    
