import pandas as pd
from algosystem.backtesting import Engine
from datetime import datetime, timedelta

# Create sample data
def create_sample_data():
    # Create a date range for the last year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # Create a simple trending price series
    import numpy as np
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.01, len(dates))  # Mean daily return of 0.05%
    prices = 100 * (1 + pd.Series(returns, index=dates)).cumprod()
    
    return prices

# Run backtest and export to database
def run_and_export_backtest():
    # Get sample data
    price_series = create_sample_data()
    
    # Create and run backtest
    engine = Engine(price_series)
    results = engine.run()
    
    # Print summary of results
    print(f"Total Return: {results['returns']:.2%}")
    print(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
    print(f"Max Drawdown: {results['metrics']['max_drawdown']:.2%}")
    
    # Export to database
    try:
        run_id = engine.export_db()
        print(f"Successfully exported to database with run_id: {run_id}")
    except Exception as e:
        print(f"Error exporting to database: {e}")
        
    return engine

if __name__ == "__main__":
    run_and_export_backtest()