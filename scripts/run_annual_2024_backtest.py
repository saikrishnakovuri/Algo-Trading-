import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import json
from scripts.validation_backtest import ValidationBacktester

# 2025 Months
MONTHS = [
    ("2025-01-01", "2025-01-31"),
    ("2025-02-01", "2025-02-28"),
    ("2025-03-01", "2025-03-31"),
    ("2025-04-01", "2025-04-30"),
    ("2025-05-01", "2025-05-31"),
    ("2025-06-01", "2025-06-30"),
    ("2025-07-01", "2025-07-31"),
    ("2025-08-01", "2025-08-31"),
    ("2025-09-01", "2025-09-30"),
    ("2025-10-01", "2025-10-31"),
    ("2025-11-01", "2025-11-30"),
    ("2025-12-01", "2025-12-31")
]

# Define Source Data
DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"

def run_annual():
    annual_results = []
    
    # Process each Nifty 50 stock file
    for stock_file in os.listdir(DATA_PATH):
        if stock_file.endswith("_minute.csv"):
            symbol = stock_file.split('_')[0]
            print(f"\n--- Backtesting {symbol} for 2025 ---")
            
            stock_trades = []
            for start, end in MONTHS:
                tester = ValidationBacktester(initial_capital=500000.0)
                tester.master.mode = "BALANCED"
                tester.run(symbol=symbol, start_date_str=start, end_date_str=end)
                stock_trades.extend(tester.trade_log)
            
            # Aggregate stats for this stock
            df = pd.DataFrame(stock_trades)
            if not df.empty:
                annual_results.append({
                    "stock": symbol,
                    "trades": len(df),
                    "win_rate": f"{(len(df[df['net_pnl'] > 0]) / len(df)) * 100:.2f}%",
                    "total_pnl": df['net_pnl'].sum(),
                    "avg_pnl": df['net_pnl'].mean()
                })
        
    print("\n--- ANNUAL 2025 NIFTY 50 PERFORMANCE SUMMARY ---")
    print(pd.DataFrame(annual_results).to_markdown())

if __name__ == "__main__":
    run_annual()
