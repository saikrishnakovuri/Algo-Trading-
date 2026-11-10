import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from scripts.run_annual_compounded import AnnualCompoundedBacktester

# Quarter chunks to prevent timeout
QUARTERS = [
    ("2025-01-01", "2025-03-31", "Q1"),
    ("2025-04-01", "2025-06-30", "Q2"),
    ("2025-07-01", "2025-09-30", "Q3"),
    ("2025-10-01", "2025-12-31", "Q4")
]

def run_chunked_backtest():
    current_equity = 500000.0
    total_trades = 0
    total_pnl = 0.0
    quarterly_stats = []

    # Define the 12 target stocks
    TARGET_STOCKS = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
        "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA"
    ]
    
    # Initialize tester once to load data only once
    tester = AnnualCompoundedBacktester()
    tester.load_all_2025(TARGET_STOCKS)

    for start, end, label in QUARTERS:
        print(f"🚀 Running {label} ({start} to {end}) | Starting Equity: {current_equity:.2f}")
        
        # Set starting equity for this chunk
        tester.pm.total_equity = current_equity
        # Clear trade log for this chunk to measure chunk pnl
        tester.trade_log = []
        
        final_eq, trades, pnl = tester.run_custom(start, end)
        
        quarterly_stats.append({
            "Quarter": label,
            "Trades": trades,
            "PnL": round(pnl, 2),
            "Ending Equity": round(final_eq, 2)
        })
        
        current_equity = final_eq
        total_trades += trades
        total_pnl += pnl
        print(f"✅ {label} Complete. PnL: {pnl:.2f}\n")

    print("\n--- ANNUAL 2025 COMPUNDED SUMMARY (QUARTERLY) ---")
    print(pd.DataFrame(quarterly_stats).to_markdown(index=False))
    print(f"\nFinal Annual Equity: ₹{current_equity:.2f}")
    print(f"Total Annual Net PnL: ₹{total_pnl:.2f}")
    print(f"Total Annual Trades: {total_trades}")

if __name__ == "__main__":
    run_chunked_backtest()
