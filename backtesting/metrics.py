import numpy as np
import pandas as pd
from scipy import stats

def calculate_metrics(equity_curve):
    """Calculate standard performance metrics from an equity curve."""
    if not isinstance(equity_curve, pd.Series):
        equity_curve = pd.Series(equity_curve)
    
    # Calculate returns
    returns = equity_curve.pct_change().dropna()
    
    # Basic metrics
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    annual_return = (1 + total_return) ** (252 / len(returns)) - 1
    
    # Risk metrics
    volatility = returns.std() * np.sqrt(252)
    downside_returns = returns[returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
    
    # Maximum drawdown
    cum_returns = (1 + returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    max_drawdown = drawdown.min()
    
    # Ratios
    sharpe_ratio = annual_return / volatility if volatility != 0 else 0
    sortino_ratio = annual_return / downside_volatility if downside_volatility != 0 else 0
    
    # Win rate (assuming we have a separate trades dataframe)
    # This would typically come from the backtest results
    
    return {
        'total_return': total_return,
        'annual_return': annual_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'downside_volatility': downside_volatility
    }

def calculate_advanced_metrics(backtest_results, benchmark=None):
    """Calculate advanced metrics including benchmark comparison."""
    equity = backtest_results['equity']
    returns = equity.pct_change().dropna()
    
    metrics = calculate_metrics(equity)
    
    # Calculate additional metrics if benchmark is provided
    if benchmark is not None:
        # Ensure benchmark aligns with equity series
        benchmark = benchmark.reindex(equity.index, method='ffill')
        benchmark_returns = benchmark.pct_change().dropna()
        
        # Calculate beta and alpha
        if len(returns) == len(benchmark_returns):
            covariance = returns.cov(benchmark_returns)
            benchmark_variance = benchmark_returns.var()
            beta = covariance / benchmark_variance if benchmark_variance != 0 else 0
            
            # Calculate alpha (Jensen's alpha)
            risk_free_rate = 0.02 / 252  # Assuming 2% annual risk-free rate
            benchmark_annual_return = (1 + benchmark_returns.mean()) ** 252 - 1
            alpha = metrics['annual_return'] - (risk_free_rate + beta * (benchmark_annual_return - risk_free_rate))
            
            # Information ratio
            tracking_error = (returns - benchmark_returns).std() * np.sqrt(252)
            information_ratio = (metrics['annual_return'] - benchmark_annual_return) / tracking_error if tracking_error != 0 else 0
            
            # Add to metrics
            metrics.update({
                'beta': beta,
                'alpha': alpha,
                'information_ratio': information_ratio,
                'tracking_error': tracking_error,
                'benchmark_return': benchmark_annual_return
            })
    
    # Drawdown analysis
    drawdown_info = analyze_drawdowns(equity)
    metrics.update(drawdown_info)
    
    return metrics

def analyze_drawdowns(equity):
    """Analyze drawdowns in the equity curve."""
    returns = equity.pct_change().dropna()
    cum_returns = (1 + returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    
    # Find drawdown periods
    is_drawdown = drawdown < 0
    drawdown_start = is_drawdown & ~is_drawdown.shift(1).fillna(False)
    drawdown_end = ~is_drawdown & is_drawdown.shift(1).fillna(False)
    
    # Extract start and end dates
    start_dates = drawdown[drawdown_start].index
    end_dates = drawdown[drawdown_end].index
    
    # Make sure we have matching pairs
    if len(end_dates) < len(start_dates):
        # We're still in a drawdown, so the last end date is the current date
        end_dates = end_dates.append(pd.Index([equity.index[-1]]))
    
    # Calculate drawdown statistics
    drawdowns = []
    
    for i in range(min(len(start_dates), len(end_dates))):
        start = start_dates[i]
        end = end_dates[i]
        
        # Calculate drawdown depth and duration
        period_drawdown = drawdown.loc[start:end]
        depth = period_drawdown.min()
        duration = len(period_drawdown)
        
        drawdowns.append({
            'start': start,
            'end': end,
            'depth': depth,
            'duration': duration
        })
    
    # Sort by depth
    drawdowns = sorted(drawdowns, key=lambda x: x['depth'])
    
    # Return top 3 drawdowns and average statistics
    top_drawdowns = drawdowns[:3] if len(drawdowns) >= 3 else drawdowns
    
    avg_drawdown = np.mean([d['depth'] for d in drawdowns]) if drawdowns else 0
    avg_duration = np.mean([d['duration'] for d in drawdowns]) if drawdowns else 0
    
    return {
        'top_drawdowns': top_drawdowns,
        'avg_drawdown': avg_drawdown,
        'avg_drawdown_duration': avg_duration,
        'num_drawdowns': len(drawdowns)
    }