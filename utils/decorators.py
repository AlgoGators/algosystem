def strategy(timeframe='1d', asset_class='equity', **params):
    """
    Decorator to transform a function into a strategy object
    
    Args:
        timeframe (str): The timeframe for the strategy
        asset_class (str): Type of assets the strategy trades
        **params: Additional parameters for the strategy
    """
    def decorator(func):
        class StrategyWrapper:
            def __init__(self):
                self.timeframe = timeframe
                self.asset_class = asset_class
                self.params = params
                self.func = func
                self.__name__ = func.__name__
                self.__doc__ = func.__doc__
                
            def __call__(self, *args, **kwargs):
                return self.func(*args, **kwargs)
                
            def generate_signals(self, data):
                return self.func(data)
                
        return StrategyWrapper()
    
    return decorator