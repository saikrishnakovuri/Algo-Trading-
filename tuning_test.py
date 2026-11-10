import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from modules.strategy_selector import MasterStrategySelector
from modules.strategy_router import STRATEGY_REGIME_MAP

def run_tuning_test():
    symbols = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "SBIN", "ICICIBANK", "INFY", "TCS"]
    start = pd.Timestamp("2026-03-24").tz_localize('Asia/Kolkata')
    end = pd.Timestamp("2026-04-24").tz_localize('Asia/Kolkata')
    
    master = MasterStrategySelector()
    total_trades = 0
    
    print(f"Tuning Test symbols: {symbols}")
    
    for symbol in symbols:
        filename = "nifty50_1m.csv" if symbol == "NIFTY" else "banknifty_1m.csv" if symbol == "BANKNIFTY" else f"{symbol}_1m.csv"
        path = f"data/angel_historical/{filename}"
        if not os.path.exists(path): continue
        
        df_1m = pd.read_csv(path)
        df_1m["Timestamp"] = pd.to_datetime(df_1m["Timestamp"])
        df_1m.set_index("Timestamp", inplace=True)
        df_1m = df_1m[(df_1m.index >= start) & (df_1m.index <= end)]
        
        df_5m = df_1m.resample("5min").agg({
            "Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"
        }).dropna()
        
        i = 50
        while i < len(df_5m):
            sub_df = df_5m.iloc[:i+1]
            now = sub_df.index[-1]
            signal = master.select_best_signal(sub_df, symbol, 15.0, current_time=now)
            
            if signal:
                total_trades += 1
                i += 78 # Simulate single position hold
            else:
                i += 1
                
    days = 22 # Approx trading days in a month
    avg_per_day = total_trades / days
    print(f"Total Trades: {total_trades}")
    print(f"Avg Trades/Day: {avg_per_day:.2f}")

if __name__ == "__main__":
    run_tuning_test()
