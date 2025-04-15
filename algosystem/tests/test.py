import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from algosystem.backtesting.engine import Engine

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

if __name__ == "__main__":
    # Generate synthetic stock data
    data = generate_stock_data()
        
    # Initialize the backtesting engine
    engine = Engine(data=data['AAPL_close'], start_date='2025-01-01', end_date='2025-07-01')
    
    # Run the backtest
    results = engine.run()
    print("Backtest Results:")
    #print(results['equity'])
    
    print("\nMetrics:")
    metrics = engine.get_metrics()
    
    plots = engine.get_plots(show_charts=True)  # This saves the plots and returns the figure objects
    

