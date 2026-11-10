import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import logging
from modules.strategy_selector import MasterStrategySelector
from modules.portfolio_manager import PortfolioManager
from modules.indicator_cache import precompute_indicators

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("PortfolioBacktester")

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"
NIFTY_50 = ["ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"]

class PortfolioBacktester:
    def __init__(self):
        self.master = MasterStrategySelector()
        self.master.mode = "BALANCED"
        self.pm = PortfolioManager(initial_capital=500000.0)
        self.data = {}

    def load_all_2025(self):
        print("📊 Loading 2025 Data for all 50 stocks...")
        start, end = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
        for sym in NIFTY_50:
            path = os.path.join(DATA_PATH, f"{sym}_minute.csv")
            if not os.path.exists(path): continue
            
            df = pd.read_csv(path)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            df = df[(df.index >= start) & (df.index <= end)].resample("5min").agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
            self.data[sym] = precompute_indicators(df)
        print(f"✅ Data loaded for {len(self.data)} stocks.")

    def run(self):
        self.load_all_2025()
        all_indices = sorted(list(set([idx for df in self.data.values() for idx in df.index])))
        
        print("🚀 Starting Portfolio Run...")
        trade_history = []
        
        for now in all_indices:
            # Daily reset
            if now.hour == 9 and now.minute == 15:
                self.pm.daily_reset()
            
            # Portfolio loop
            daily_pnl = 0
            for sym, df in self.data.items():
                if now not in df.index: continue
                sub_df = df.loc[:now]
                
                signal = self.master.select_best_signal(sub_df, sym, 15.0, current_time=now)
                if signal:
                    risk = signal.get("sl_dist", 500.0)
                    if self.pm.can_enter_trade(risk):
                        # PnL logic - using a realistic volatility-based return
                        # In a real engine this simulates trade exit
                        trade_pnl = (df.loc[now]['close'] - df.loc[now]['open']) * 50 # Simplification
                        daily_pnl += trade_pnl
                        trade_history.append({"time": now, "sym": sym, "pnl": trade_pnl})
                        self.pm.remove_risk(risk)
            
            # End of day compounding
            if now.hour == 15 and now.minute == 25:
                self.pm.update_equity(daily_pnl)
                print(f"[{now.date()}] Day Complete. Equity: {self.pm.total_equity:.2f}")

        # Final Report
        df_hist = pd.DataFrame(trade_history)
        print("\n--- ANNUAL 2025 PORTFOLIO SUMMARY ---")
        print(f"Final Equity: ₹{self.pm.total_equity:.2f}")
        print(f"Total Trades: {len(df_hist)}")
        print(f"Net PnL: ₹{df_hist['pnl'].sum():.2f}")

if __name__ == "__main__":
    PortfolioBacktester().run()
