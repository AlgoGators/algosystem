

import csv
import random
from datetime import datetime, timedelta

def generate_strategy_csv(filename="strategy.csv", 
                          start_date="2022-01-01", 
                          start_value=100000.0, 
                          num_days=1000):
    """Generate a CSV file with random strategy values."""
    
    date = datetime.strptime(start_date, "%Y-%m-%d")
    value = start_value

    with open(filename, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Date", "Strategy"])
        
        for _ in range(num_days):
            # Simulate a small daily return between -0.5% and +0.7%
            daily_return = random.uniform(-0.005, 0.007)
            value *= (1 + daily_return)
            
            writer.writerow([date.strftime("%Y-%m-%d"), f"{value:.2f}"])
            date += timedelta(days=1)
    
    print(f"✅ CSV with {num_days} lines saved as '{filename}'")

# Example usage:
generate_strategy_csv()
