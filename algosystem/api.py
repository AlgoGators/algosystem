from backtesting import Engine
from data.connectors import database
#from reporting import export
import pandas as pd

# Create a class-based API
class AlgoSystem:
    @staticmethod
    def run_backtest(data, strategy, start_date=None, end_date=None, 
                     initial_capital=100000.0, **kwargs):
        """Run a backtest programmatically"""
        engine = Engine(
            strategy=strategy,
            data=data,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
        )
        
        return engine.run()
    
    @staticmethod
    def save_results(results, output_path):
        """Save backtest results to file"""
        import pickle
        import os
        
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'wb') as f:
            pickle.dump(results, f)
        
        return output_path
    
    @staticmethod
    def load_results(file_path):
        """Load backtest results from file"""
        import pickle
        
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    
    @staticmethod
    def push_to_db(results, name, description='', strategy_type=''):
        """Push results to database"""
        return database.push_to_db(results, name, description, strategy_type)
    
    @staticmethod
    def get_from_db(db_id=None, name=None):
        """Get results from database"""
        return database.get_from_db(db_id, name)
    
    @staticmethod
    def list_backtests(strategy_type=None):
        """List backtests from database"""
        return database.list_from_db(strategy_type)
    
    @staticmethod
    def visualize_results(results, output=None):
        """Create an interactive visualization"""
        from backtesting.visualization import create_performance_dashboard
        dashboard = create_performance_dashboard(results)
        
        if output:
            dashboard.save(output)
            return output
        else:
            dashboard.show()
            return dashboard