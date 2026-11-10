import subprocess
import os
import time
import pandas as pd
from modules.portfolio_manager import PortfolioManager
from modules.strategy_selector import MasterStrategySelector
from modules.indicator_cache import precompute_indicators

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"

# Full Nifty 50 List
NIFTY_50 = ["ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"]

class GlobalBacktester:
    def __init__(self):
        self.master = MasterStrategySelector()
        self.pm = PortfolioManager(initial_capital=500000.0)
        self.data = {}

    def load_all(self, start, end):
        for sym in NIFTY_50:
            path = os.path.join(DATA_PATH, f"{sym}_minute.csv")
            if not os.path.exists(path): continue
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df = df[(df.index >= start) & (df.index <= end)].resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
            self.data[sym] = precompute_indicators(df)

    def run(self):
        start = pd.Timestamp("2025-01-01").tz_localize('Asia/Kolkata')
        end = pd.Timestamp("2025-12-31").tz_localize('Asia/Kolkata')
        self.load_all(start, end)
        
        all_indices = sorted(list(set([idx for df in self.data.values() for idx in df.index])))
        
        print("🚀 Starting Portfolio Run...")
        for now in all_indices:
            # New Day Logic
            if now.hour == 9 and now.minute == 15:
                self.pm.daily_reset()
            
            for sym, df in self.data.items():
                if now not in df.index: continue
                sub_df = df.loc[:now]
                
                signal = self.master.select_best_signal(sub_df, sym, 15.0, current_time=now)
                if signal:
                    # Risk Check
                    risk = signal.get("sl_dist", 500.0)
                    if self.pm.can_enter_trade(risk):
                        # PnL Placeholder logic
                        self.pm.update_equity(100.0) 
                        self.pm.remove_risk(risk)
                        
if __name__ == "__main__":
    GlobalBacktester().run()
