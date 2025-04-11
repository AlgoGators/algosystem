import pandas as pd
import numpy as np

# Import the base engine and decorator
from backtesting.engine import Engine
from utils.decorators import strategy

# Import risk functions
from analysis.risk import calculate_var, calculate_cvar, calculate_risk_metrics, stress_test as risk_stress_test

# Import performance functions
from analysis.performance import calculate_rolling_stats, calculate_returns_stats as performance_stress_test, compare_strategies

# Import portfolio functions
from analysis.portfolio import (
    calculate_portfolio_return,
    calculate_portfolio_variance,
    calculate_portfolio_std,
    calculate_sharpe_ratio,
    negative_sharpe_ratio,
    optimize_portfolio
)

# ============================================================
# A simple strategy (using your decorator) for demonstration.
# This strategy goes long 100 shares of "AAPL" if the closing price
# increases from the previous day.
# ============================================================
@strategy(timeframe='1d', asset_class='equity')
def example_strategy(data):
    if len(data) < 2:
        return {}
    if data['AAPL_close'].iloc[-1] > data['AAPL_close'].iloc[-2]:
        return {'AAPL': 100}
    else:
        return {'AAPL': 0}

# ============================================================
# ExtendedEngine definition
# ============================================================
class ExtendedEngine(Engine):
    """
    An extended backtesting engine that, after running the base simulation,
    computes additional risk and performance metrics and performs portfolio optimization.
    
    Additional parameters for risk, performance, and portfolio functions can be provided
    as dictionaries. For example:
    
      risk_params = {
          'calculate_var': {'confidence_level': 0.95, 'method': 'historical'},
          'calculate_cvar': {'confidence_level': 0.95},
          'calculate_risk_metrics': {'risk_free_rate': 0.01, 'periods_per_year': 252},
          'scenarios': {'scenario1': 0.9, 'scenario2': 0.8}  # Custom stress test scenarios
      }
      
      performance_params = {
          'calculate_rolling_stats': {'window': 30},
          'scenarios': {'scenario1': 0.95, 'scenario2': 0.85}  # If using performance stress test
      }
      
      portfolio_params = {
          'optimize_portfolio': {'risk_free_rate': 0.01},
          'calculate_sharpe_ratio': {'risk_free_rate': 0.01}
      }
    
    The inferred return values for functions are:
      - Risk functions return floats or dictionaries (see above note).
      - Performance statistics functions return DataFrames or dictionaries.
      - Portfolio optimization returns a tuple of (optimal_weights, optimal_sharpe).
    """
    def __init__(self, strategy, data, start_date=None, end_date=None, 
                 initial_capital=100000.0, commission=0.001,
                 risk_params=None, performance_params=None, portfolio_params=None):
        super().__init__(strategy, data, start_date, end_date, initial_capital, commission)
        # Parameters for risk, performance, and portfolio functions
        self.risk_params = risk_params or {}
        self.performance_params = performance_params or {}
        self.portfolio_params = portfolio_params or {}

    def run(self):
        # Run the base backtest simulation
        results = super().run()
        
        # Calculate daily returns from the equity time series
        returns = results['equity'].pct_change().dropna()
        
        # ===============================
        # Risk Metrics
        # ===============================
        var = calculate_var(returns, **self.risk_params.get('calculate_var', {}))
        cvar = calculate_cvar(returns, **self.risk_params.get('calculate_cvar', {}))
        risk_metrics = calculate_risk_metrics(returns, **self.risk_params.get('calculate_risk_metrics', {}))
        
        # Stress testing: if scenarios are provided in risk_params, run stress test.
        scenarios = self.risk_params.get('scenarios', None)
        if scenarios:
            stress_results = risk_stress_test(self.strategy, self.data, scenarios, initial_capital=self.initial_capital)
        else:
            stress_results = None

        # ===============================
        # Performance Statistics
        # ===============================
        rolling_stats = calculate_rolling_stats(returns, **self.performance_params.get('calculate_rolling_stats', {}))
        
        # ===============================
        # Portfolio Optimization
        # ===============================
        # Note: For a single asset, the optimization is trivial. In a multi-asset setting,
        # optimize_portfolio() returns optimal weights (e.g., a dict of {"AAPL": weight1, ...})
        # and an optimal Sharpe ratio.
        optimized_weights, optimal_sharpe = optimize_portfolio(returns, **self.portfolio_params.get('optimize_portfolio', {}))
        
        # Calculate portfolio performance assuming the 'returns' represent asset returns.
        # For a multi-asset portfolio, returns would typically be a DataFrame.
        portfolio_return = calculate_portfolio_return(optimized_weights, returns)
        
        # Compute covariance matrix from returns (if multiple assets, use DataFrame.cov())
        cov_matrix = returns.cov()
        portfolio_variance = calculate_portfolio_variance(optimized_weights, cov_matrix)
        portfolio_std = calculate_portfolio_std(optimized_weights, cov_matrix)
        calculated_sharpe = calculate_sharpe_ratio(optimized_weights, returns, cov_matrix, **self.portfolio_params.get('calculate_sharpe_ratio', {}))
        
        # ===============================
        # Compile Extended Results
        # ===============================
        extended_results = {
            'var': var,
            'cvar': cvar,
            'risk_metrics': risk_metrics,
            'stress_test': stress_results,
            'rolling_stats': rolling_stats,
            'optimized_weights': optimized_weights,
            'optimal_sharpe': optimal_sharpe,
            'portfolio_return': portfolio_return,
            'portfolio_variance': portfolio_variance,
            'portfolio_std': portfolio_std,
            'calculated_sharpe': calculated_sharpe,
        }
        
        # Merge the base backtest results with the extended analytics.
        results.update(extended_results)
        return results

# ============================================================
# Function to generate simulated stock data for a single stock "AAPL".
# This data has 200 rows with OHLCV columns.
# ============================================================
def generate_stock_data():
    np.random.seed(42)
    n_rows = 200
    dates = pd.date_range(start='2025-01-01', periods=n_rows, freq='B')
    
    open_prices = np.random.uniform(100, 200, size=n_rows)
    high_prices = open_prices + np.random.uniform(0, 10, size=n_rows)
    low_prices = open_prices - np.random.uniform(0, 10, size=n_rows)
    close_prices = np.array([np.random.uniform(low, high) for low, high in zip(low_prices, high_prices)])
    volume = np.random.randint(100000, 1000000, size=n_rows)
    
    # Prefix columns with "AAPL_" so they match what the strategy expects.
    df = pd.DataFrame({
        'AAPL_open': open_prices,
        'AAPL_high': high_prices,
        'AAPL_low': low_prices,
        'AAPL_close': close_prices,
        'AAPL_volume': volume
    }, index=dates)
    
    return df

# ============================================================
# Main block to set up and run the extended backtest.
# ============================================================
if __name__ == '__main__':
    # Generate simulated OHLCV stock data
    stock_data = generate_stock_data()
    
    # Define parameter dictionaries for risk, performance, and portfolio functions.
    risk_params = {
        'calculate_var': {'confidence_level': 0.95, 'method': 'historical'},
        'calculate_cvar': {'confidence_level': 0.95},
        'calculate_risk_metrics': {'risk_free_rate': 0.01, 'periods_per_year': 252},
        'scenarios': {'down_10%': 0.9, 'down_20%': 0.8}
    }
    
    performance_params = {
        'calculate_rolling_stats': {'window': 30}
        # Additional performance parameters (e.g. for stress test scenarios) can be added here.
    }
    
    portfolio_params = {
        'optimize_portfolio': {'risk_free_rate': 0.01},
        'calculate_sharpe_ratio': {'risk_free_rate': 0.01}
    }
    
    # Instantiate the ExtendedEngine with the example strategy and simulated data.
    engine_instance = ExtendedEngine(
        strategy=example_strategy,
        data=stock_data,
        risk_params=risk_params,
        performance_params=performance_params,
        portfolio_params=portfolio_params
    )
    
    # Run the extended backtest simulation
    results = engine_instance.run()
    
    # ===============================
    # Output the base and extended metrics.
    # ===============================
    print("=== Base Backtest Metrics ===")
    print("Initial Capital:", results['initial_capital'])
    print("Final Capital:", results['final_capital'])
    print("Total Return: {:.2%}".format(results['returns']))
    print("\nSample Equity Time Series:")
    print(results['equity'].head())
    
    print("\n=== Extended Analytics ===")
    print("Value at Risk (VaR):", results['var'])
    print("Conditional VaR (CVaR):", results['cvar'])
    print("Risk Metrics:", results['risk_metrics'])
    if results['stress_test']:
        print("Stress Test Results:", results['stress_test'])
    
    print("\nRolling Statistics:")
    print(results['rolling_stats'].head(strategy))
    
    print("\nReturns Statistics:")
    print(results['returns_stats'])
    
    print("\n--- Portfolio Optimization ---")
    print("Optimized Weights:", results['optimized_weights'])
    print("Optimal Sharpe Ratio (from optimization):", results['optimal_sharpe'])
    print("Portfolio Return:", results['portfolio_return'])
    print("Portfolio Variance:", results['portfolio_variance'])
    print("Portfolio Standard Deviation:", results['portfolio_std'])
    print("Calculated Sharpe Ratio:", results['calculated_sharpe'])
