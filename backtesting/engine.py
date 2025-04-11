
import pandas as pd
import numpy as np
from datetime import datetime
from utils.logging import get_logger

logger = get_logger(__name__)

class Engine:
    """Backtesting engine for strategy evaluation."""
    
    def __init__(self, strategy, data, start_date=None, end_date=None, 
                 initial_capital=100000.0, commission=0.001):
        """
        Initialize the backtesting engine.
        
        Parameters:
        -----------
        strategy : callable
            A function that takes market data and returns positions
        data : pd.DataFrame
            Historical market data with datetime index
        start_date : str, optional
            Start date for backtesting (YYYY-MM-DD)
        end_date : str, optional
            End date for backtesting (YYYY-MM-DD)
        initial_capital : float, default 100000.0
            Initial capital for the backtest
        commission : float, default 0.001
            Commission rate as a fraction of trade value
        """
        self.strategy = strategy
        self.data = data
        self.start_date = pd.to_datetime(start_date) if start_date else data.index[0]
        self.end_date = pd.to_datetime(end_date) if end_date else data.index[-1]
        self.initial_capital = initial_capital
        self.commission = commission
        
        # Filter data based on date range
        mask = (data.index >= self.start_date) & (data.index <= self.end_date)
        self.data = data.loc[mask].copy()
        
        if self.data.empty:
            raise ValueError("No data available for the specified date range")
            
        logger.info(f"Initialized backtest from {self.start_date} to {self.end_date}")
        
    def run(self):
        """
        Run the backtest simulation.
        
        Returns:
        --------
        results : dict
            Dictionary containing backtest results
        """
        logger.info("Starting backtest simulation")
        
        # Initialize results containers
        equity = [self.initial_capital]
        positions = []
        trades = []
        
        # Run strategy through each data point
        for i, (date, row) in enumerate(self.data.iterrows()):
            # Get current market data up to this point
            current_data = self.data.iloc[:i+1]
            
            # Execute strategy to get positions
            try:
                current_positions = self.strategy(current_data)
                positions.append(current_positions)
            except Exception as e:
                logger.error(f"Strategy execution error on {date}: {str(e)}")
                positions.append({})  # Empty positions on error
            
            # Calculate equity based on positions and price changes
            if i > 0:
                prev_positions = positions[-2]
                current_positions = positions[-1]
                
                # Track trades
                for symbol in set(list(prev_positions.keys()) + list(current_positions.keys())):
                    prev_pos = prev_positions.get(symbol, 0)
                    curr_pos = current_positions.get(symbol, 0)
                    
                    if prev_pos != curr_pos:
                        price = row.get(f"{symbol}_close", 0)
                        trade_size = abs(curr_pos - prev_pos)
                        commission_cost = trade_size * price * self.commission
                        
                        trades.append({
                            'date': date,
                            'symbol': symbol,
                            'quantity': curr_pos - prev_pos,
                            'price': price,
                            'commission': commission_cost
                        })
                
                # Calculate new equity
                new_equity = equity[-1]
                
                # Add price changes for current positions
                for symbol, quantity in current_positions.items():
                    if f"{symbol}_close" in row and f"{symbol}_close" in self.data.iloc[i-1]:
                        price_change = row[f"{symbol}_close"] - self.data.iloc[i-1][f"{symbol}_close"]
                        new_equity += quantity * price_change
                
                # Subtract commissions from trades
                trade_commissions = sum(t['commission'] for t in trades if t['date'] == date)
                new_equity -= trade_commissions
                
                equity.append(new_equity)
            
        # Compile results
        equity_series = pd.Series(equity, index=self.data.index)
        
        results = {
            'equity': equity_series,
            'positions': positions,
            'trades': pd.DataFrame(trades),
            'initial_capital': self.initial_capital,
            'final_capital': equity[-1],
            'returns': (equity[-1] - self.initial_capital) / self.initial_capital,
            'data': self.data,
            'start_date': self.start_date,
            'end_date': self.end_date
        }
        
        logger.info(f"Backtest completed. Final return: {results['returns']:.2%}")
        
        return results
