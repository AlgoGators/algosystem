import numpy as np
import pandas as pd
from scipy import stats


def calculate_returns_stats(returns):
    """
    Calculate comprehensive statistics for a returns series.

    Parameters:
    -----------
    returns : pandas.Series
        Returns series

    Returns:
    --------
    stats : dict
        Dictionary containing return statistics
    """
    if returns.empty:
        return {}

    # Basic statistics
    total_return = (1 + returns).prod() - 1
    annual_return = (1 + returns.mean()) ** 252 - 1
    volatility = returns.std() * np.sqrt(252)

    # Distribution statistics
    skewness = returns.skew()
    kurtosis = returns.kurtosis()

    # Normality test (Jarque-Bera)
    jb_stat, jb_pvalue = stats.jarque_bera(returns.dropna())

    # Return all statistics
    return {
        "total_return": total_return,
        "annual_return": annual_return,
        "volatility": volatility,
        "sharpe_ratio": annual_return / volatility if volatility != 0 else 0,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "jarque_bera_stat": jb_stat,
        "jarque_bera_pvalue": jb_pvalue,
        "normality": "Normal" if jb_pvalue > 0.05 else "Non-normal",
    }


def calculate_rolling_stats(returns, window=252):
    """
    Calculate rolling performance statistics.

    Parameters:
    -----------
    returns : pandas.Series
        Returns series
    window : int, default 252
        Rolling window size

    Returns:
    --------
    stats : pandas.DataFrame
        DataFrame of rolling statistics
    """
    # Ensure we have enough data
    if len(returns) < window:
        window = len(returns) // 2  # Use at least half the data

    if window < 1:
        return pd.DataFrame()

    # Calculate rolling metrics
    rolling_return = returns.rolling(window).mean() * 252
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)
    rolling_sharpe = rolling_return / rolling_vol

    # Calculate rolling max drawdown
    cum_returns = (1 + returns).cumprod()
    rolling_max_dd = pd.Series(index=returns.index, dtype=float)

    for i in range(window, len(cum_returns)):
        window_cum_returns = cum_returns.iloc[i - window : i + 1]
        window_peak = window_cum_returns.cummax()
        window_dd = (window_cum_returns / window_peak) - 1
        rolling_max_dd.iloc[i] = window_dd.min()

    # Combine all metrics
    stats = pd.DataFrame(
        {
            "rolling_return": rolling_return,
            "rolling_volatility": rolling_vol,
            "rolling_sharpe": rolling_sharpe,
            "rolling_max_drawdown": rolling_max_dd,
        }
    )

    return stats


def compare_strategies(strategies_results, benchmark=None):
    """
    Compare multiple strategy backtests.

    Parameters:
    -----------
    strategies_results : dict
        Dictionary of strategy names and their backtest results
    benchmark : pandas.Series, optional
        Benchmark returns series

    Returns:
    --------
    comparison : dict
        Dictionary containing comparison results
    """
    from ..backtesting.metrics import calculate_metrics

    # Extract equity curves and calculate returns
    equity_curves = {}
    returns = {}
    metrics = {}

    for name, results in strategies_results.items():
        equity = results["equity"]
        equity_curves[name] = equity
        returns[name] = equity.pct_change().dropna()
        metrics[name] = calculate_metrics(equity)

    # Add benchmark if provided
    if benchmark is not None:
        equity_curves["Benchmark"] = benchmark
        returns["Benchmark"] = benchmark.pct_change().dropna()
        metrics["Benchmark"] = calculate_metrics(benchmark)

    # Align all returns series to the same dates
    aligned_returns = pd.DataFrame(returns)

    # Calculate correlation matrix
    correlation = aligned_returns.corr()

    # Create comparison DataFrame
    comparison_data = []

    for name, metric in metrics.items():
        comparison_data.append(
            {
                "Strategy": name,
                "Total Return": metric["total_return"],
                "Annual Return": metric["annual_return"],
                "Volatility": metric["volatility"],
                "Sharpe Ratio": metric["sharpe_ratio"],
                "Sortino Ratio": metric["sortino_ratio"],
                "Max Drawdown": metric["max_drawdown"],
            }
        )

    comparison_df = pd.DataFrame(comparison_data)

    # Return results
    return {
        "metrics": comparison_df,
        "correlation": correlation,
        "equity_curves": equity_curves,
        "returns": aligned_returns,
    }


def analyze_returns_by_period(returns):
    """
    Analyze returns across different time periods.

    Parameters:
    -----------
    returns : pandas.Series
        Returns series with datetime index

    Returns:
    --------
    analysis : dict
        Dictionary containing period analysis
    """
    if returns.empty:
        return {}

    # Check if the index is datetime
    if not isinstance(returns.index, pd.DatetimeIndex):
        try:
            returns.index = pd.to_datetime(returns.index)
        except:
            return {"error": "Returns index must be convertible to datetime"}

    # Daily analysis
    daily_returns = returns.copy()
    daily_mean = daily_returns.mean()
    daily_positive = (daily_returns > 0).mean()

    # Monthly analysis
    monthly_returns = returns.resample("M").apply(lambda x: (1 + x).prod() - 1)
    monthly_mean = monthly_returns.mean()
    monthly_positive = (monthly_returns > 0).mean()

    # Quarterly analysis
    quarterly_returns = returns.resample("Q").apply(lambda x: (1 + x).prod() - 1)
    quarterly_mean = quarterly_returns.mean()
    quarterly_positive = (quarterly_returns > 0).mean()

    # Annual analysis
    annual_returns = returns.resample("A").apply(lambda x: (1 + x).prod() - 1)
    annual_mean = annual_returns.mean()
    annual_positive = (annual_returns > 0).mean()

    # Day of week analysis
    dow_returns = pd.DataFrame(
        {"returns": daily_returns, "day_of_week": daily_returns.index.day_name()}
    )
    dow_analysis = (
        dow_returns.groupby("day_of_week")["returns"]
        .agg(["mean", "std", "count", lambda x: (x > 0).mean()])
        .rename(columns={"<lambda_0>": "positive_pct"})
    )

    # Month of year analysis
    moy_returns = pd.DataFrame(
        {"returns": monthly_returns, "month": monthly_returns.index.month_name()}
    )
    moy_analysis = (
        moy_returns.groupby("month")["returns"]
        .agg(["mean", "std", "count", lambda x: (x > 0).mean()])
        .rename(columns={"<lambda_0>": "positive_pct"})
    )

    return {
        "daily": {"mean": daily_mean, "positive_pct": daily_positive},
        "monthly": {
            "mean": monthly_mean,
            "positive_pct": monthly_positive,
            "returns": monthly_returns,
        },
        "quarterly": {
            "mean": quarterly_mean,
            "positive_pct": quarterly_positive,
            "returns": quarterly_returns,
        },
        "annual": {
            "mean": annual_mean,
            "positive_pct": annual_positive,
            "returns": annual_returns,
        },
        "day_of_week": dow_analysis,
        "month_of_year": moy_analysis,
    }
