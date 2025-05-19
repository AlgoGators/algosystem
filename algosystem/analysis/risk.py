import numpy as np
from scipy import stats


def calculate_var(returns, confidence_level=0.95, method="historical"):
    """
    Calculate Value at Risk (VaR).

    Parameters:
    -----------
    returns : pandas.Series
        Daily returns series
    confidence_level : float, default 0.95
        Confidence level for VaR
    method : str, default 'historical'
        Method to calculate VaR ('historical', 'parametric', or 'monte_carlo')

    Returns:
    --------
    var : float
        Value at Risk as a positive percentage
    """
    if method == "historical":
        # Historical VaR - simply use the percentile of historical returns
        var = -np.percentile(returns, 100 * (1 - confidence_level))

    elif method == "parametric":
        # Parametric VaR - assume normal distribution
        z_score = stats.norm.ppf(1 - confidence_level)
        var = -(returns.mean() + z_score * returns.std())

    elif method == "monte_carlo":
        # Monte Carlo VaR - simulate returns based on historical parameters
        mean = returns.mean()
        std = returns.std()

        # Simulate 10,000 random returns
        np.random.seed(42)  # For reproducibility
        simulated_returns = np.random.normal(mean, std, 10000)

        var = -np.percentile(simulated_returns, 100 * (1 - confidence_level))

    else:
        raise ValueError(
            f"Unknown method: {method}. Use 'historical', 'parametric', or 'monte_carlo'."
        )

    return var


def calculate_cvar(returns, confidence_level=0.95):
    """
    Calculate Conditional Value at Risk (CVaR), also known as Expected Shortfall.

    Parameters:
    -----------
    returns : pandas.Series
        Daily returns series
    confidence_level : float, default 0.95
        Confidence level for CVaR

    Returns:
    --------
    cvar : float
        Conditional Value at Risk as a positive percentage
    """
    # Calculate VaR first
    var = calculate_var(returns, confidence_level, "historical")

    # CVaR is the mean of returns below VaR
    tail_returns = returns[returns < -var]
    cvar = -tail_returns.mean() if not tail_returns.empty else var

    return cvar


def calculate_risk_metrics(returns, risk_free_rate=0.0, periods_per_year=252):
    """
    Calculate comprehensive risk metrics for a returns series.

    Parameters:
    -----------
    returns : pandas.Series
        Daily returns series
    risk_free_rate : float, default 0.0
        Annual risk-free rate
    periods_per_year : int, default 252
        Number of periods in a year

    Returns:
    --------
    metrics : dict
        Dictionary containing risk metrics
    """
    # Convert annual risk-free rate to per-period
    rf_per_period = (1 + risk_free_rate) ** (1 / periods_per_year) - 1

    # Excess returns over risk-free rate
    excess_returns = returns - rf_per_period

    # Annualized return
    avg_return = returns.mean()
    ann_return = (1 + avg_return) ** periods_per_year - 1

    # Volatility
    volatility = returns.std() * np.sqrt(periods_per_year)

    # Downside deviation (semi-standard deviation)
    downside_returns = returns[returns < 0]
    downside_deviation = (
        downside_returns.std() * np.sqrt(periods_per_year)
        if len(downside_returns) > 0
        else 0
    )

    # Maximum drawdown
    cum_returns = (1 + returns).cumprod()
    running_max = cum_returns.cummax()
    drawdown = (cum_returns / running_max) - 1
    max_drawdown = drawdown.min()

    # Ratios
    sharpe_ratio = (ann_return - risk_free_rate) / volatility if volatility != 0 else 0
    sortino_ratio = (
        (ann_return - risk_free_rate) / downside_deviation
        if downside_deviation != 0
        else 0
    )

    # VaR and CVaR
    var_95 = calculate_var(returns, 0.95, "historical")
    var_99 = calculate_var(returns, 0.99, "historical")
    cvar_95 = calculate_cvar(returns, 0.95)

    # Return all metrics
    return {
        "annual_return": ann_return,
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "downside_deviation": downside_deviation,
        "max_drawdown": max_drawdown,
        "var_95": var_95,
        "var_99": var_99,
        "cvar_95": cvar_95,
    }


def stress_test(strategy, data, scenarios, initial_capital=100000.0):
    """
    Perform stress testing on a strategy under different scenarios.

    Parameters:
    -----------
    strategy : callable
        Strategy function that takes data and returns positions
    data : pandas.DataFrame
        Historical market data
    scenarios : dict
        Dictionary of scenarios to test with adjustment factors
    initial_capital : float, default 100000.0
        Initial capital for the backtest

    Returns:
    --------
    results : dict
        Dictionary of stress test results
    """
    from ..backtesting import Engine

    results = {}

    # Base case - original data
    base_engine = Engine(strategy=strategy, data=data, initial_capital=initial_capital)
    base_results = base_engine.run()
    results["base_case"] = {
        "returns": base_results["returns"],
        "max_drawdown": base_results.get("metrics", {}).get("max_drawdown", 0),
    }

    # Test each scenario
    for scenario_name, adjustments in scenarios.items():
        # Create adjusted data for the scenario
        adjusted_data = data.copy()

        for column, factor in adjustments.items():
            if column in adjusted_data.columns:
                adjusted_data[column] = adjusted_data[column] * factor

        # Run backtest with adjusted data
        scenario_engine = Engine(
            strategy=strategy, data=adjusted_data, initial_capital=initial_capital
        )
        scenario_results = scenario_engine.run()

        results[scenario_name] = {
            "returns": scenario_results["returns"],
            "max_drawdown": scenario_results.get("metrics", {}).get("max_drawdown", 0),
        }

    return results
