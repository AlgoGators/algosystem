import quantstats as qs
import numpy as np
import pandas as pd


# Time series
def rolling_sharpe(returns, window=30):
    return qs.stats.rolling_sharpe(returns, window)

def rolling_sortino(returns, window=30):
    return qs.stats.rolling_sortino(returns, window)

def rolling_volatility(returns, window=30):
    return returns.rolling(window).std() * np.sqrt(252)  # Annualized

def rolling_max_drawdown(returns, window=30):
    return qs.stats.rolling_max_drawdown(returns, window)

def calmar(returns):
    return qs.stats.calmar(returns)

def rolling_information_ratio(returns, benchmark, window=30):
    return qs.stats.rolling_information_ratio(returns, benchmark, window)

def rolling_beta(returns, benchmark, window=30):
    return qs.stats.rolling_beta(returns, benchmark, window)

def rolling_skew(returns, window=30):
    return returns.rolling(window).skew()

def rolling_kurtosis(returns, window=30):
    return returns.rolling(window).kurtosis()

def rolling_var(returns, window=30, q=0.05):
    return returns.rolling(window).quantile(q)

def rolling_cvar(returns, window=30, q=0.05):
    # conditional (expected shortfall) below the q‑quantile
    return returns.rolling(window).apply(
        lambda x: x[x <= x.quantile(q)].mean(), raw=True
    )

def rolling_drawdown_duration(returns: pd.Series, window: int = 30) -> pd.Series:
    """
    Computes the rolling maximum drawdown duration over a given window.
    
    For each date:
      1. Build the equity curve and its running high-water mark.
      2. Flag days under water (equity < high-water mark).
      3. Compute the current underwater streak length.
      4. Take a rolling max of that streak over `window` periods.
    
    Parameters
    ----------
    returns : pd.Series
        Daily return series, indexed by a DatetimeIndex.
    window : int
        Look-back window (in trading days) over which to report the max drawdown duration.
    
    Returns
    -------
    pd.Series
        Rolling max drawdown duration (in days), indexed same as `returns`.
    """
    # 1. Equity curve & running peak
    equity = (1 + returns).cumprod()
    peak   = equity.cummax()
    
    # 2. Underwater flag: 1 if below peak, else 0
    underwater = (equity < peak).astype(int)
    
    # 3. Convert that into a “current streak” series
    #    Group by cumulative sum of zeros to reset count on non‑underwater days
    group_id  = (underwater == 0).cumsum()
    streak    = underwater.groupby(group_id).cumcount() + 1  # counts 1,2,3… on underwater days
    streak    = streak.where(underwater == 1, 0)             # but zero out non‑underwater days
    
    # 4. Rolling maximum streak length
    return streak.rolling(window).max()

def rolling_turnover(positions, window=30):
    # sum of daily changes in position size over the window
    daily_chg = positions.diff().abs()
    return daily_chg.rolling(window).sum()

# 7. Equity curve & drawdown series (static, but very informative)
def equity_curve(returns):
    return (1 + returns).cumprod()

def drawdown_series(returns):
    ec = equity_curve(returns)
    high = ec.cummax()
    return (ec / high) - 1

def quant_stats(strategy, benchmark):
    """Utilizes the quantstats library and other processing to return the results dictionary

    Parameters
    ----------
    strategy_name : str
        The name of the over-arching strategy behind the positions obtained from the system
    strategy : pd.Series
        The positions of the strategy
    benchmark_name : str
        The name of the benchmark used to find performance metrics
    benchmark : pd.Series
        The positions of the benchmark
        

    Returns
    -------
    dict
        The processed data
    """
    strategy = strategy.pct_change().dropna()
    benchmark = benchmark.pct_change().dropna()
    
    # Calculate distributions with serialized dates
    functions_list = [
        "adjusted_sortino", "avg_loss", "avg_return", "avg_win", "best", "cagr", "calmar",
        "common_sense_ratio", "comp", "conditional_value_at_risk", "consecutive_losses",
        "consecutive_wins", "cpc_index", "cvar", "expected_return",
        "expected_shortfall", "exposure", "gain_to_pain_ratio", "geometric_mean", "ghpr", "greeks",
        "information_ratio", "kelly_criterion", "kurtosis", "max_drawdown", "omega",
        "outlier_loss_ratio", "outlier_win_ratio", "payoff_ratio",
        "probabilistic_adjusted_sortino_ratio", "probabilistic_ratio", "probabilistic_sharpe_ratio",
        "risk_of_ruin", "risk_return_ratio", "ror", "serenity_index", "sharpe", "skew", "smart_sharpe",
        "smart_sortino", "sortino", "tail_ratio", "ulcer_index", "ulcer_performance_index", "upi",
        "value_at_risk", "var", "volatility", "win_loss_ratio", "win_rate", "worst",
    ]

    results = {}
    
    # Add calculated metrics to the results
    for func_name in functions_list:
        try:
            func = getattr(qs.stats, func_name)

            # Handle functions requiring additional arguments
            if func_name in ["information_ratio", "r_squared"]:
                result = func(strategy, benchmark)
            else:
                result = func(strategy)

            results[func_name] = result

        except Exception as e:
            results[func_name] = f"Error in {func_name}: {e}"

    return results

if __name__ == "__main__":
    dates = pd.date_range(start="2020-01-01", periods=1000, freq="B")  
    data = pd.Series(np.random.randn(1000).cumsum(), index=dates, name="Strategy")
    benchmark = pd.Series(np.random.randn(1000).cumsum(), index=dates, name="Benchmark")

    results = quant_stats(data, benchmark)

    for key, value in results.items():
        print(f"{key}: {type(value)}, {value}")

    