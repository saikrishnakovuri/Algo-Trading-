import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import json
import logging
from modules.strategy_selector import MasterStrategySelector
from modules.v3_utils import NIFTY_LOT_SIZE, BANKNIFTY_LOT_SIZE, BROKERAGE_OPTIONS
from modules.indicator_cache import precompute_indicators
from modules.portfolio_manager import PortfolioManager

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"

class PortfolioBacktester:
    def __init__(self, initial_capital=500000.0):
        self.master = MasterStrategySelector()
        self.pm = PortfolioManager(initial_capital=initial_capital)
        self.symbols = ["ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
                        "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL"]
        self.data = {}

    def load_all_data(self, start_date, end_date):
        for sym in self.symbols:
            filename = f"{sym}_minute.csv"
            path = os.path.join(DATA_PATH, filename)
            if not os.path.exists(path): continue
            
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            df = df.resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
            self.data[sym] = precompute_indicators(df)

    def run(self, start_date_str, end_date_str):
        start = pd.Timestamp(start_date_str).tz_localize('Asia/Kolkata')
        end = pd.Timestamp(end_date_str).tz_localize('Asia/Kolkata')
        self.load_all_data(start, end)
        
        # Get common index
        all_indices = sorted(list(set([idx for df in self.data.values() for idx in df.index])))
        
        for now in all_indices:
            self.pm.daily_reset() # Reset risk budget for new day
            
            # 1. Scan all symbols
            for sym, df in self.data.items():
                if now not in df.index: continue
                
                sub_df = df.loc[:now]
                signal = self.master.select_best_signal(sub_df, sym, 15.0, current_time=now)
                
                if signal:
                    # Check Global Portfolio Risk
                    risk_amount = signal.get("sl_dist", 500.0) # Assume 500 risk if missing
                    if self.pm.can_enter_trade(risk_amount):
                        # Execute logic
                        print(f"[{now}] TRADE ENTERED: {sym} | Equity: {self.pm.total_equity:.2f}")
                        # Simulate trade exit and update equity
                        self.pm.update_equity(1000.0) # Placeholder PnL
                        self.pm.remove_risk(risk_amount)

if __name__ == "__main__":
    backtester = PortfolioBacktester()
    backtester.run("2025-01-01", "2025-12-31")
