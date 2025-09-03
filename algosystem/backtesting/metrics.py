import numpy as np
import pandas as pd
import quantstats as qs


def rolling_sharpe(returns, window=30):
    return qs.stats.rolling_sharpe(returns, window)


def rolling_sortino(returns, window=30):
    return qs.stats.rolling_sortino(returns, window)


def rolling_volatility(returns, window=30):
    return returns.rolling(window).std() * np.sqrt(252)  # Annualized


def calmar(returns):
    return qs.stats.calmar(returns)


def rolling_skew(returns, window=30):
    return returns.rolling(window).skew()


def rolling_var(returns, window=30, q=0.05):
    return returns.rolling(window).quantile(q)


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
    peak = equity.cummax()

    # 2. Underwater flag: 1 if below peak, else 0
    underwater = (equity < peak).astype(int)

    # 3. Convert that into a "current streak" series
    #    Group by cumulative sum of zeros to reset count on non‑underwater days
    group_id = (underwater == 0).cumsum()
    streak = (
        underwater.groupby(group_id).cumcount() + 1
    )  # counts 1,2,3… on underwater days
    streak = streak.where(underwater == 1, 0)  # but zero out non‑underwater days

    # 4. Rolling maximum streak length
    return streak.rolling(window).max()


def rolling_turnover(positions, window=30):
    # sum of daily changes in position size over the window
    daily_chg = positions.diff().abs()
    return daily_chg.rolling(window).sum()


def equity_curve(returns):
    return (1 + returns).cumprod()


def drawdown_series(returns):
    ec = equity_curve(returns)
    high = ec.cummax()
    return (ec / high) - 1


def calculate_time_series_data(strategy, benchmark=None, window=30):
    """
    Calculate time series data for a strategy and optional benchmark.
    Returns only data that changes over time (rolling metrics).

    Parameters
    ----------
    strategy : pd.Series
        Daily prices or returns of the strategy, indexed by date
    benchmark : pd.Series, optional
        Daily prices or returns of the benchmark, indexed by date
    window : int, default=30
        Rolling window size for metrics calculation

    Returns
    -------
    dict
        Dictionary containing all calculated time series data
    """
    # Convert to returns if prices are provided
    strategy_clean = strategy.dropna()
    if len(strategy_clean) > 1:
        pct_test = strategy_clean.pct_change().dropna()
        if len(pct_test) > 0 and (abs(pct_test) < 0.5).all() and not pct_test.isna().all():
            strategy_returns = pct_test
        else:
            strategy_returns = strategy_clean
    else:
        strategy_returns = strategy_clean

    # Handle benchmark if provided
    benchmark_returns = None
    if benchmark is not None:
        benchmark_clean = benchmark.dropna()
        if len(benchmark_clean) > 1:
            bench_pct_test = benchmark_clean.pct_change().dropna()
            if len(bench_pct_test) > 0 and (abs(bench_pct_test) < 0.5).all() and not bench_pct_test.isna().all():
                benchmark_returns = bench_pct_test
            else:
                benchmark_returns = benchmark_clean
        else:
            benchmark_returns = benchmark_clean

        # Align data
        strategy_returns, benchmark_returns = strategy_returns.align(
            benchmark_returns, join="inner"
        )

    # Initialize results dictionary
    time_series = {}

    # Calculate equity curves
    time_series["equity_curve"] = equity_curve(strategy_returns)
    time_series["drawdown_series"] = drawdown_series(strategy_returns)

    # Calculate rolling metrics with different windows
    # Use a longer window (252 days = 1 year) for more stable rolling metrics
    long_window = 252

    time_series["rolling_sharpe"] = rolling_sharpe(strategy_returns, long_window)
    time_series["rolling_sortino"] = rolling_sortino(strategy_returns, long_window)
    time_series["rolling_volatility"] = rolling_volatility(
        strategy_returns, long_window
    )
    time_series["rolling_skew"] = rolling_skew(strategy_returns, long_window)
    time_series["rolling_var"] = rolling_var(strategy_returns, long_window)
    time_series["rolling_drawdown_duration"] = rolling_drawdown_duration(
        strategy_returns, long_window
    )

    # Calculate benchmark-dependent time series if benchmark is provided
    if benchmark_returns is not None:
        time_series["benchmark_equity_curve"] = equity_curve(benchmark_returns)
        time_series["benchmark_drawdown_series"] = drawdown_series(benchmark_returns)
        time_series["benchmark_rolling_volatility"] = rolling_volatility(
            benchmark_returns, long_window
        )

        # Calculate relative performance
        time_series["relative_performance"] = (
            time_series["equity_curve"] / time_series["benchmark_equity_curve"]
        )

    # Calculate periodic returns (also time series)
    time_series["daily_returns"] = strategy_returns
    time_series["monthly_returns"] = strategy_returns.resample("ME").apply(
        lambda x: (1 + x).prod() - 1
    )
    time_series["yearly_returns"] = strategy_returns.resample("YE").apply(
        lambda x: (1 + x).prod() - 1
    )

    # Calculate rolling returns for different periods
    time_series["rolling_3m_returns"] = (
        (1 + strategy_returns).rolling(63).apply(lambda x: x.prod() - 1, raw=True)
    )
    time_series["rolling_6m_returns"] = (
        (1 + strategy_returns).rolling(126).apply(lambda x: x.prod() - 1, raw=True)
    )
    time_series["rolling_1y_returns"] = (
        (1 + strategy_returns).rolling(252).apply(lambda x: x.prod() - 1, raw=True)
    )

    return time_series


def calculate_metrics(strategy, benchmark=None):
    """
    Calculate static performance metrics for a strategy and optional benchmark.
    Returns only point-in-time metrics (not time series data).

    Parameters
    ----------
    strategy : pd.Series
        Daily prices or returns of the strategy, indexed by date
    benchmark : pd.Series, optional
        Daily prices or returns of the benchmark, indexed by date

    Returns
    -------
    dict
        Dictionary containing all calculated performance metrics
    """
    # Convert to returns if prices are provided
    strategy_clean = strategy.dropna()
    if len(strategy_clean) == 0:
        return {"error": "No valid data after removing NaN values"}
    
    if len(strategy_clean) > 1:
        pct_test = strategy_clean.pct_change().dropna()
        if len(pct_test) > 0 and (abs(pct_test) < 0.5).all() and not pct_test.isna().all():
            strategy_returns = pct_test
        else:
            strategy_returns = strategy_clean
    else:
        strategy_returns = strategy_clean

    # Handle benchmark if provided
    benchmark_returns = None
    if benchmark is not None:
        benchmark_clean = benchmark.dropna()
        if len(benchmark_clean) > 1:
            bench_pct_test = benchmark_clean.pct_change().dropna()
            if len(bench_pct_test) > 0 and (abs(bench_pct_test) < 0.5).all() and not bench_pct_test.isna().all():
                benchmark_returns = bench_pct_test
            else:
                benchmark_returns = benchmark_clean
        else:
            benchmark_returns = benchmark_clean

        # Align data
        strategy_returns, benchmark_returns = strategy_returns.align(
            benchmark_returns, join="inner"
        )

    metrics = {}

    # Validate we have data
    if len(strategy_returns) == 0:
        return {"error": "No valid returns data"}

    # Validate reasonable ranges
    max_abs_return = abs(strategy_returns).max()
    if max_abs_return > 10:
        return {"error": f"Unrealistic return detected: {max_abs_return:.2f}"}

    # Basic return statistics
    try:
        metrics["total_return"] = (strategy_returns + 1).prod() - 1
        if not np.isfinite(metrics["total_return"]):
            metrics["total_return"] = strategy_returns.sum()
    except:
        metrics["total_return"] = strategy_returns.sum()

    if len(strategy_returns) > 0:
        try:
            periods_ratio = 252 / len(strategy_returns)
            if abs(metrics["total_return"]) < 100 and metrics["total_return"] > -0.99:
                metrics["annualized_return"] = (1 + metrics["total_return"]) ** periods_ratio - 1
            else:
                metrics["annualized_return"] = strategy_returns.mean() * 252
            
            if not np.isfinite(metrics["annualized_return"]):
                metrics["annualized_return"] = strategy_returns.mean() * 252
                
        except (OverflowError, ValueError, ZeroDivisionError):
            metrics["annualized_return"] = strategy_returns.mean() * 252
    else:
        metrics["annualized_return"] = 0.0

    try:
        vol = strategy_returns.std() * np.sqrt(252)
        metrics["annualized_volatility"] = vol if np.isfinite(vol) else 0.0
    except:
        metrics["annualized_volatility"] = 0.0

    # Add alternative key names for backward compatibility
    metrics["annual_return"] = metrics["annualized_return"]
    metrics["volatility"] = metrics["annualized_volatility"]

    # Risk metrics
    try:
        metrics["max_drawdown"] = qs.stats.max_drawdown(strategy_returns)
        metrics["var_95"] = qs.stats.value_at_risk(strategy_returns, cutoff=0.05)
        metrics["cvar_95"] = qs.stats.conditional_value_at_risk(
            strategy_returns, cutoff=0.05
        )
        metrics["skewness"] = strategy_returns.skew()
    except Exception as e:
        # Fallback calculations
        try:
            cumulative = (1 + strategy_returns).cumprod()
            running_max = cumulative.cummax()
            drawdown = (cumulative / running_max) - 1
            metrics["max_drawdown"] = drawdown.min()
        except:
            metrics["max_drawdown"] = 0.0
        
        try:
            metrics["var_95"] = -np.percentile(strategy_returns, 5)
        except:
            metrics["var_95"] = 0.0
        
        metrics["cvar_95"] = metrics.get("var_95", 0.0) * 1.3
        metrics["skewness"] = strategy_returns.skew() if len(strategy_returns) > 2 else 0.0
        metrics["risk_metrics_error"] = str(e)

    # Ratios
    try:
        metrics["sharpe_ratio"] = qs.stats.sharpe(strategy_returns)
        metrics["sortino_ratio"] = qs.stats.sortino(strategy_returns)
        metrics["calmar_ratio"] = qs.stats.calmar(strategy_returns)
    except Exception as e:
        # Fallback calculations
        ann_return = metrics.get("annualized_return", 0)
        ann_vol = metrics.get("annualized_volatility", 1)
        metrics["sharpe_ratio"] = ann_return / ann_vol if ann_vol > 0 else 0
        metrics["sortino_ratio"] = metrics["sharpe_ratio"]
        max_dd = metrics.get("max_drawdown", -0.01)
        metrics["calmar_ratio"] = ann_return / abs(max_dd) if max_dd < 0 else 0
        metrics["ratio_metrics_error"] = str(e)

    # Trade statistics
    metrics["positive_days"] = (strategy_returns > 0).sum()
    metrics["negative_days"] = (strategy_returns < 0).sum()
    metrics["pct_positive_days"] = (strategy_returns > 0).mean()

    # Monthly statistics
    try:
        monthly_returns = strategy_returns.resample("ME").apply(
            lambda x: (1 + x).prod() - 1
        )
        metrics["best_month"] = monthly_returns.max()
        metrics["worst_month"] = monthly_returns.min()
        metrics["avg_monthly_return"] = monthly_returns.mean()
        metrics["monthly_volatility"] = monthly_returns.std()
        metrics["pct_positive_months"] = (monthly_returns > 0).mean()
    except:
        metrics["best_month"] = 0.0
        metrics["worst_month"] = 0.0
        metrics["avg_monthly_return"] = 0.0
        metrics["monthly_volatility"] = 0.0
        metrics["pct_positive_months"] = 0.0

    # Calculate additional benchmark-dependent metrics if benchmark is provided
    if benchmark_returns is not None:
        try:
            metrics["alpha"] = qs.stats.greeks(strategy_returns, benchmark_returns)[
                "alpha"
            ]
            metrics["beta"] = qs.stats.greeks(strategy_returns, benchmark_returns)[
                "beta"
            ]
            metrics["correlation"] = strategy_returns.corr(benchmark_returns)
            metrics["tracking_error"] = qs.stats.greeks(
                strategy_returns, benchmark_returns
            )["risk"]
            metrics["information_ratio"] = qs.stats.information_ratio(
                strategy_returns, benchmark_returns
            )
            metrics["capture_ratio_up"] = qs.stats.capture(
                strategy_returns, benchmark_returns, up=True
            )
            metrics["capture_ratio_down"] = qs.stats.capture(
                strategy_returns, benchmark_returns, up=False
            )
        except Exception as e:
            metrics["alpha"] = 0.0
            metrics["beta"] = 1.0
            metrics["correlation"] = strategy_returns.corr(benchmark_returns) if len(strategy_returns) > 1 else 0.0
            metrics["tracking_error"] = 0.0
            metrics["information_ratio"] = 0.0
            metrics["capture_ratio_up"] = 1.0
            metrics["capture_ratio_down"] = 1.0
            metrics["benchmark_metrics_error"] = str(e)

    return metrics