import numpy as np
from scipy.optimize import minimize


def calculate_portfolio_return(weights, returns):
    """
    Calculate portfolio return given weights and asset returns.

    Parameters:
    -----------
    weights : numpy.ndarray
        Array of asset weights
    returns : pandas.DataFrame
        DataFrame of asset returns

    Returns:
    --------
    portfolio_return : float
        Expected portfolio return
    """
    return np.sum(returns.mean() * weights)


def calculate_portfolio_variance(weights, cov_matrix):
    """
    Calculate portfolio variance given weights and covariance matrix.

    Parameters:
    -----------
    weights : numpy.ndarray
        Array of asset weights
    cov_matrix : pandas.DataFrame
        Covariance matrix of asset returns

    Returns:
    --------
    portfolio_variance : float
        Portfolio variance
    """
    return np.dot(weights.T, np.dot(cov_matrix, weights))


def calculate_portfolio_std(weights, cov_matrix):
    """
    Calculate portfolio standard deviation.

    Parameters:
    -----------
    weights : numpy.ndarray
        Array of asset weights
    cov_matrix : pandas.DataFrame
        Covariance matrix of asset returns

    Returns:
    --------
    portfolio_std : float
        Portfolio standard deviation
    """
    return np.sqrt(calculate_portfolio_variance(weights, cov_matrix))


def calculate_sharpe_ratio(weights, returns, cov_matrix, risk_free_rate=0.0):
    """
    Calculate the Sharpe ratio for a portfolio.

    Parameters:
    -----------
    weights : numpy.ndarray
        Array of asset weights
    returns : pandas.DataFrame
        DataFrame of asset returns
    cov_matrix : pandas.DataFrame
        Covariance matrix of asset returns
    risk_free_rate : float, optional
        Risk-free rate, default is 0

    Returns:
    --------
    sharpe_ratio : float
        Sharpe ratio of the portfolio
    """
    portfolio_return = calculate_portfolio_return(weights, returns)
    portfolio_std = calculate_portfolio_std(weights, cov_matrix)
    return (portfolio_return - risk_free_rate) / portfolio_std


def negative_sharpe_ratio(weights, returns, cov_matrix, risk_free_rate=0.0):
    """
    Calculate the negative Sharpe ratio (for minimization).

    Parameters:
    -----------
    weights : numpy.ndarray
        Array of asset weights
    returns : pandas.DataFrame
        DataFrame of asset returns
    cov_matrix : pandas.DataFrame
        Covariance matrix of asset returns
    risk_free_rate : float, optional
        Risk-free rate, default is 0

    Returns:
    --------
    negative_sharpe : float
        Negative Sharpe ratio
    """
    return -calculate_sharpe_ratio(weights, returns, cov_matrix, risk_free_rate)


def optimize_portfolio(returns, risk_free_rate=0.0):
    """
    Optimize portfolio weights to maximize the Sharpe ratio.

    Parameters:
    -----------
    returns : pandas.DataFrame
        DataFrame of asset returns
    risk_free_rate : float, optional
        Risk-free rate, default is 0

    Returns:
    --------
    optimal_weights : numpy.ndarray
        Optimal weights for the portfolio
    performance : dict
        Dictionary containing performance metrics
    """
    n_assets = returns.shape[1]
    cov_matrix = returns.cov()

    # Initial guess (equal weights)
    initial_weights = np.array([1.0 / n_assets] * n_assets)

    # Constraints
    constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1.0}

    # Bounds (0 <= weight <= 1)
    bounds = tuple((0.0, 1.0) for _ in range(n_assets))

    # Optimize
    result = minimize(
        negative_sharpe_ratio,
        initial_weights,
        args=(returns, cov_matrix, risk_free_rate),
        bounds=bounds,
        constraints=constraints,
        method="SLSQP",
    )

    optimal_weights = result["x"]

    # Calculate performance metrics
    performance = {
        "sharpe_ratio": calculate_sharpe_ratio(
            optimal_weights, returns, cov_matrix, risk_free_rate
        ),
        "expected_return": calculate_portfolio_return(optimal_weights, returns),
        "volatility": calculate_portfolio_std(optimal_weights, cov_matrix),
    }

    return optimal_weights, performance


def calculate_efficient_frontier(returns, num_points=50, risk_free_rate=0.0):
    """
    Calculate the efficient frontier for a portfolio.

    Parameters:
    -----------
    returns : pandas.DataFrame
        DataFrame of asset returns
    num_points : int, optional
        Number of points to generate on the frontier, default is 50
    risk_free_rate : float, optional
        Risk-free rate, default is 0

    Returns:
    --------
    frontier_returns : numpy.ndarray
        Expected returns for frontier portfolios
    frontier_volatilities : numpy.ndarray
        Volatilities for frontier portfolios
    frontier_weights : list
        Weights for each portfolio on the frontier
    """
    n_assets = returns.shape[1]
    cov_matrix = returns.cov()

    def portfolio_volatility(weights):
        return calculate_portfolio_std(weights, cov_matrix)

    def portfolio_return(weights):
        return calculate_portfolio_return(weights, returns)

    # Function to minimize for a target return
    def minimize_volatility(weights, target_return):
        # Return should be target_return
        return_constraint = {
            "type": "eq",
            "fun": lambda x: portfolio_return(x) - target_return,
        }
        # Weights should sum to 1
        sum_constraint = {"type": "eq", "fun": lambda x: np.sum(x) - 1.0}

        constraints = [return_constraint, sum_constraint]
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))

        # Initial guess (equal weights)
        initial_weights = np.array([1.0 / n_assets] * n_assets)

        result = minimize(
            portfolio_volatility,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        return result["x"], result["fun"]

    # Find the minimum and maximum returns
    def target_function(weights):
        # Weights should sum to 1
        constraint = {"type": "eq", "fun": lambda x: np.sum(x) - 1.0}
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))

        # Initial guess (equal weights)
        initial_weights = np.array([1.0 / n_assets] * n_assets)

        result = minimize(
            lambda x: -portfolio_return(x),
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=[constraint],
        )

        min_return = -result["fun"]

        result = minimize(
            lambda x: portfolio_return(x),
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=[constraint],
        )

        max_return = -result["fun"]

        return min_return, max_return

    min_return, max_return = target_function(None)

    # Generate target returns
    target_returns = np.linspace(min_return, max_return, num_points)

    # Calculate the efficient frontier
    efficient_portfolios = [
        minimize_volatility(None, target) for target in target_returns
    ]

    frontier_weights = [portfolio[0] for portfolio in efficient_portfolios]
    frontier_volatilities = [portfolio[1] for portfolio in efficient_portfolios]
    frontier_returns = [portfolio_return(weights) for weights in frontier_weights]

    return np.array(frontier_returns), np.array(frontier_volatilities), frontier_weights
