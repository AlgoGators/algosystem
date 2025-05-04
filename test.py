import numpy as np
import pandas as pd

from algosystem.backtesting.engine import Engine

from rich import print


if __name__ == "__main__":
    # Create more realistic market data
    dates = pd.date_range(start="2020-01-01", periods=1000, freq="B")
    
    # Create percentage returns (more realistic than random walk)
    strategy_returns = np.random.normal(0.0005, 0.01, 1000)  # mean of 0.05% daily, 1% std
    benchmark_returns = np.random.normal(0.0004, 0.012, 1000)  # slightly lower mean, higher vol
    
    # Convert returns to price series (starting at 100)
    strategy_prices = 100 * (1 + pd.Series(strategy_returns, index=dates)).cumprod()
    benchmark_prices = 100 * (1 + pd.Series(benchmark_returns, index=dates)).cumprod()
    
    # Name the series
    strategy_prices.name = "Strategy"
    benchmark_prices.name = "Benchmark"
    
    # Save to CSV
    strategy_prices.to_csv("strategy.csv")
    benchmark_prices.to_csv("benchmark.csv")
    
    print("Running backtest...")
    
    # Create and run engine
    engine = Engine(strategy_prices, benchmark_prices)
    engine.run()
    
    print("Backtest complete!")
    
    # Print key metrics
    results = engine.get_results()
    metrics = results.get('metrics', {})
    
    print("\nKey Performance Metrics:")
    important_metrics = [
        'total_return', 'annualized_return', 'annualized_volatility', 
        'sharpe_ratio', 'max_drawdown', 'calmar_ratio'
    ]
    
    for metric in important_metrics:
        if metric in metrics:
            print(f"{metric}: {metrics[metric]:.4f}")