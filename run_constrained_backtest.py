import os
import pandas as pd
from datetime import time as dtime
from backtest_engine import BacktestEngine

def run_constrained_backtest():
    initial_capital = 500000.0
    # Point to the Nifty 200 data folder
    data_dir = 'data/nifty200'
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('_1m.csv')]
    
    # Increase to first 10 files for test
    files = files[:10]
    
    engine = BacktestEngine(initial_capital=initial_capital)
    
    print(f"Starting unfiltered backtest for August 2025...")
    
    # Run backtest with no isolation filter, no day/time constraints (commented in engine)
    trades = engine.run_massive_backtest_v2(
        files=files,
        start_date="2025-08-01",
        end_date="2025-08-31"
    )
    
    print(f"Total trades: {len(trades)}")
    for t in trades:
        print(f"Date: {t['date']} | Time: {t['time']} | Type: {t['type']} | Setup: {t['setup']}")
    
    return trades

if __name__ == "__main__":
    run_constrained_backtest()
