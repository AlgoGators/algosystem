"""
Benchmark data fetching, processing and management module for AlgoSystem.
This module handles obtaining benchmark data from various sources and storing it in parquet format.
"""

import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

from algosystem.utils._logging import get_logger

logger = get_logger(__name__)

# Define the benchmark storage location
BENCHMARK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "benchmark")

# Ensure benchmark directory exists
os.makedirs(BENCHMARK_DIR, exist_ok=True)

# Define benchmark aliases and their corresponding tickers/symbols
BENCHMARK_ALIASES = {
    # Stock indices
    "sp500": "^GSPC",  # S&P 500
    "nasdaq": "^IXIC",  # NASDAQ Composite
    "djia": "^DJI",  # Dow Jones Industrial Average
    "russell2000": "^RUT",  # Russell 2000
    "vix": "^VIX",  # CBOE Volatility Index
    # Treasury yields
    "10y_treasury": "^TNX",  # 10-Year Treasury Yield
    "5y_treasury": "^FVX",  # 5-Year Treasury Yield
    "30y_treasury": "^TYX",  # 30-Year Treasury Yield
    "13w_treasury": "^IRX",  # 13-Week Treasury Yield
    # ETFs representing different asset classes
    "treasury_bonds": "TLT",  # iShares 20+ Year Treasury Bond ETF
    "corporate_bonds": "LQD",  # iShares iBoxx $ Investment Grade Corporate Bond ETF
    "high_yield_bonds": "HYG",  # iShares iBoxx $ High Yield Corporate Bond ETF
    "gold": "GLD",  # SPDR Gold Shares
    "commodities": "DBC",  # Invesco DB Commodity Index Tracking Fund
    "real_estate": "VNQ",  # Vanguard Real Estate ETF
    # International indices
    "europe": "^STOXX50E",  # EURO STOXX 50
    "uk": "^FTSE",  # FTSE 100
    "japan": "^N225",  # Nikkei 225
    "china": "000001.SS",  # Shanghai Composite
    "emerging_markets": "EEM",  # iShares MSCI Emerging Markets ETF
    # Alternative strategies
    "trend_following": "DBMF",  # iMGP DBi Managed Futures Strategy ETF
    "hedge_fund": "HFRX",  # HFRX Global Hedge Fund Index (approximation)
    "risk_parity": "RPAR",  # RPAR Risk Parity ETF
    "momentum": "MTUM",  # iShares MSCI USA Momentum Factor ETF
    "value": "VLUE",  # iShares MSCI USA Value Factor ETF
    "low_vol": "USMV",  # iShares MSCI USA Min Vol Factor ETF
    # Sectors
    "technology": "XLK",  # Technology Select Sector SPDR Fund
    "healthcare": "XLV",  # Health Care Select Sector SPDR Fund
    "financials": "XLF",  # Financial Select Sector SPDR Fund
    "energy": "XLE",  # Energy Select Sector SPDR Fund
    "utilities": "XLU",  # Utilities Select Sector SPDR Fund
}

# Default benchmark when none specified
DEFAULT_BENCHMARK = "sp500"


def get_benchmark_list():
    """
    Get a list of all available benchmark aliases.

    Returns:
    --------
    list
        List of available benchmark aliases
    """
    return sorted(list(BENCHMARK_ALIASES.keys()))


def get_benchmark_info():
    """
    Get information about all available benchmarks.

    Returns:
    --------
    pd.DataFrame
        DataFrame with benchmark information
    """
    data = []
    categories = {
        "Stock indices": ["sp500", "nasdaq", "djia", "russell2000", "vix"],
        "Treasury yields": [
            "10y_treasury",
            "5y_treasury",
            "30y_treasury",
            "13w_treasury",
        ],
        "ETFs": [
            "treasury_bonds",
            "corporate_bonds",
            "high_yield_bonds",
            "gold",
            "commodities",
            "real_estate",
        ],
        "International": ["europe", "uk", "japan", "china", "emerging_markets"],
        "Alternative strategies": [
            "trend_following",
            "hedge_fund",
            "risk_parity",
            "momentum",
            "value",
            "low_vol",
        ],
        "Sectors": ["technology", "healthcare", "financials", "energy", "utilities"],
    }

    for category, aliases in categories.items():
        for alias in aliases:
            if alias in BENCHMARK_ALIASES:
                data.append(
                    {
                        "Alias": alias,
                        "Category": category,
                        "Ticker/Symbol": BENCHMARK_ALIASES[alias],
                        "Description": get_benchmark_description(alias),
                    }
                )

    return pd.DataFrame(data)


def get_benchmark_description(alias):
    """
    Get a description for a benchmark alias.

    Parameters:
    -----------
    alias : str
        Benchmark alias

    Returns:
    --------
    str
        Description of the benchmark
    """
    descriptions = {
        "sp500": "S&P 500 Index - 500 of the largest US companies",
        "nasdaq": "NASDAQ Composite Index - US tech-heavy stock market index",
        "djia": "Dow Jones Industrial Average - 30 prominent US companies",
        "russell2000": "Russell 2000 Index - 2000 small-cap US companies",
        "vix": "CBOE Volatility Index - Market's expectation of 30-day volatility",
        "10y_treasury": "10-Year US Treasury Yield",
        "5y_treasury": "5-Year US Treasury Yield",
        "30y_treasury": "30-Year US Treasury Yield",
        "13w_treasury": "13-Week US Treasury Yield",
        "treasury_bonds": "iShares 20+ Year Treasury Bond ETF (TLT)",
        "corporate_bonds": "iShares iBoxx $ Investment Grade Corporate Bond ETF (LQD)",
        "high_yield_bonds": "iShares iBoxx $ High Yield Corporate Bond ETF (HYG)",
        "gold": "SPDR Gold Shares (GLD)",
        "commodities": "Invesco DB Commodity Index Tracking Fund (DBC)",
        "real_estate": "Vanguard Real Estate ETF (VNQ)",
        "europe": "EURO STOXX 50 - 50 of the largest Eurozone companies",
        "uk": "FTSE 100 Index - 100 companies listed on the London Stock Exchange",
        "japan": "Nikkei 225 - Japan's leading stock market index",
        "china": "Shanghai Composite Index",
        "emerging_markets": "iShares MSCI Emerging Markets ETF (EEM)",
        "trend_following": "iMGP DBi Managed Futures Strategy ETF (DBMF)",
        "hedge_fund": "HFRX Global Hedge Fund Index (approximation)",
        "risk_parity": "RPAR Risk Parity ETF",
        "momentum": "iShares MSCI USA Momentum Factor ETF (MTUM)",
        "value": "iShares MSCI USA Value Factor ETF (VLUE)",
        "low_vol": "iShares MSCI USA Min Vol Factor ETF (USMV)",
        "technology": "Technology Select Sector SPDR Fund (XLK)",
        "healthcare": "Health Care Select Sector SPDR Fund (XLV)",
        "financials": "Financial Select Sector SPDR Fund (XLF)",
        "energy": "Energy Select Sector SPDR Fund (XLE)",
        "utilities": "Utilities Select Sector SPDR Fund (XLU)",
    }

    return descriptions.get(alias, f"Benchmark for {alias}")


def get_benchmark_path(alias):
    """
    Get the file path for a benchmark's parquet file.

    Parameters:
    -----------
    alias : str
        Benchmark alias

    Returns:
    --------
    str
        Path to the benchmark's parquet file
    """
    return os.path.join(BENCHMARK_DIR, f"{alias}.parquet")


def fetch_benchmark_data(alias, start_date=None, end_date=None, force_refresh=False):
    """
    Fetch benchmark data, using cached parquet if available.

    Parameters:
    -----------
    alias : str
        Benchmark alias
    start_date : str or datetime, optional
        Start date for the data
    end_date : str or datetime, optional
        End date for the data
    force_refresh : bool, optional
        Whether to force fetching new data even if cached data exists

    Returns:
    --------
    pd.Series
        Benchmark price series
    """
    # Handle alias
    if alias not in BENCHMARK_ALIASES:
        logger.warning(
            f"Unknown benchmark alias: {alias}. Using {DEFAULT_BENCHMARK} instead."
        )
        alias = DEFAULT_BENCHMARK

    ticker = BENCHMARK_ALIASES[alias]

    # Set default end date to today if not provided
    if end_date is None:
        end_date = datetime.now()
    elif isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)

    # Set default start date to 20 years ago if not provided
    if start_date is None:
        start_date = end_date - timedelta(days=365 * 20)  # 20 years of data
    elif isinstance(start_date, str):
        start_date = pd.to_datetime(start_date)

    # Check if cached data exists and is up to date
    parquet_path = get_benchmark_path(alias)
    if os.path.exists(parquet_path) and not force_refresh:
        # Load cached data
        cached_data = pd.read_parquet(parquet_path)

        # Check if we need to update
        if cached_data.index[-1].date() >= (end_date - timedelta(days=1)).date():
            logger.info(f"Using cached benchmark data for {alias} from {parquet_path}")

            # Filter to the requested date range
            mask = (cached_data.index >= start_date) & (cached_data.index <= end_date)
            return cached_data.loc[mask]

    # Fetch new data
    logger.info(
        f"Fetching benchmark data for {alias} ({ticker}) from {start_date.date()} to {end_date.date()}"
    )

    try:
        # Try to fetch as much historical data as possible
        data = yf.download(
            ticker,
            start=start_date
            - timedelta(days=365 * 5),  # Get extra history in case needed
            end=end_date,
            progress=False,
        )

        if data.empty:
            logger.error(f"Failed to fetch data for {alias} ({ticker})")
            raise ValueError(f"No data returned for {alias} ({ticker})")

        # Use Adjusted Close or Close if Adjusted Close isn't available
        if "Adj Close" in data.columns:
            prices = data["Adj Close"]
        else:
            prices = data["Close"]

        # Save to parquet
        prices.to_parquet(parquet_path)
        logger.info(f"Saved benchmark data for {alias} to {parquet_path}")

        # Return filtered to requested date range
        mask = (prices.index >= start_date) & (prices.index <= end_date)
        return prices.loc[mask]

    except Exception as e:
        logger.error(f"Error fetching benchmark data for {alias} ({ticker}): {str(e)}")

        # Try to use cached data if available, even if it's outdated
        if os.path.exists(parquet_path):
            logger.info(f"Using outdated cached data for {alias} from {parquet_path}")
            cached_data = pd.read_parquet(parquet_path)
            mask = (cached_data.index >= start_date) & (cached_data.index <= end_date)
            return cached_data.loc[mask]

        # If no cached data, raise the exception
        raise


def fetch_all_benchmarks(start_date=None, end_date=None, force_refresh=False):
    """
    Fetch data for all benchmarks.

    Parameters:
    -----------
    start_date : str or datetime, optional
        Start date for the data
    end_date : str or datetime, optional
        End date for the data
    force_refresh : bool, optional
        Whether to force fetching new data even if cached data exists

    Returns:
    --------
    dict
        Dictionary of benchmark alias -> price series
    """
    results = {}

    for alias in BENCHMARK_ALIASES:
        try:
            logger.info(f"Fetching benchmark data for {alias}")
            results[alias] = fetch_benchmark_data(
                alias, start_date, end_date, force_refresh
            )
        except Exception as e:
            logger.error(f"Error fetching benchmark {alias}: {str(e)}")

    return results


def get_benchmark_returns(alias, start_date=None, end_date=None):
    """
    Get benchmark returns series.

    Parameters:
    -----------
    alias : str
        Benchmark alias
    start_date : str or datetime, optional
        Start date for the data
    end_date : str or datetime, optional
        End date for the data

    Returns:
    --------
    pd.Series
        Benchmark returns series
    """
    prices = fetch_benchmark_data(alias, start_date, end_date)
    return prices.pct_change().dropna()


def compare_benchmarks(benchmarks, start_date=None, end_date=None):
    """
    Compare multiple benchmarks over the same period.

    Parameters:
    -----------
    benchmarks : list
        List of benchmark aliases to compare
    start_date : str or datetime, optional
        Start date for the data
    end_date : str or datetime, optional
        End date for the data

    Returns:
    --------
    pd.DataFrame
        DataFrame with normalized price series for each benchmark
    """
    results = {}

    for alias in benchmarks:
        try:
            prices = fetch_benchmark_data(alias, start_date, end_date)
            # Normalize to start at 100
            results[alias] = 100 * (prices / prices.iloc[0])
        except Exception as e:
            logger.error(f"Error fetching benchmark {alias}: {str(e)}")

    return pd.DataFrame(results)


def get_benchmark_metrics(alias, start_date=None, end_date=None):
    """
    Calculate performance metrics for a benchmark.

    Parameters:
    -----------
    alias : str
        Benchmark alias
    start_date : str or datetime, optional
        Start date for the data
    end_date : str or datetime, optional
        End date for the data

    Returns:
    --------
    dict
        Dictionary of performance metrics
    """
    prices = fetch_benchmark_data(alias, start_date, end_date)
    returns = prices.pct_change().dropna()

    # Calculate basic metrics
    total_return = (prices.iloc[-1] / prices.iloc[0]) - 1
    annualized_return = (1 + total_return) ** (252 / len(returns)) - 1
    volatility = returns.std() * np.sqrt(252)
    sharpe_ratio = annualized_return / volatility if volatility != 0 else 0

    # Calculate drawdown
    drawdown = (prices / prices.cummax()) - 1
    max_drawdown = drawdown.min()

    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "volatility": volatility,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
    }


# Simple implementation to convert ETF yield to a price index for treasuries
def yield_to_price_index(yield_series):
    """
    Convert a yield series to a price index (approximately).
    Used for treasury yield benchmarks.

    Parameters:
    -----------
    yield_series : pd.Series
        Yield series (in %)

    Returns:
    --------
    pd.Series
        Price index series
    """
    # Simple approximation: higher yields = lower prices
    # Starting from 100, adjust by the change in yield (inverse relationship)
    yield_pct = yield_series / 100  # Convert from percent to decimal
    price = 100 * (1 / yield_pct) / (1 / yield_pct.iloc[0])
    return price


if __name__ == "__main__":
    # When run directly, refresh all benchmark data
    print("Refreshing all benchmark data...")
    fetch_all_benchmarks(force_refresh=True)
    print("Done!")
