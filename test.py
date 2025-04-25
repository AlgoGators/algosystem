import quantstats as qs
import numpy as np
import pandas as pd

from algosystem.backtesting.metrics import quant_stats
from algosystem.backtesting.engine import Engine

from rich import print


if __name__ == "__main__":
    dates = pd.date_range(start="2020-01-01", periods=1000, freq="B")  
    data = pd.Series(np.random.randn(1000).cumsum(), index=dates, name="Strategy")
    benchmark = pd.Series(np.random.randn(1000).cumsum(), index=dates, name="Benchmark")

    data.to_csv("strategy.csv")
    benchmark.to_csv("benchmark.csv")
    engine = Engine(data)

    engine.run()
    results = engine.get_results()

    for key, value in results.items():
        print(f"{key}: {type(value)}, {value}")

    