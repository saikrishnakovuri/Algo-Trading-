import os
import pandas as pd
import numpy as np
from datetime import datetime
# Import from the backup file by copying it or using importlib
# For simplicity, I'll copy the logic or import it if I can rename it.

# Let's try to import it directly if I rename it to backtest_engine_v1.py
if not os.path.exists("backtest_engine_v1.py"):
    with open("backtest_engine.py.bak", "r") as f:
        content = f.read()
    with open("backtest_engine_v1.py", "w") as f:
        f.write(content)

from backtest_engine_v1 import BacktestEngine

def run_v1_backtest():
    initial_capital = 500000.0
    file_path = "data/nifty_index/NIFTY_Jan2026.csv"
    
    if not os.path.exists(file_path):
        print(f"❌ Error: {file_path} not found.")
        return

    print(f"🚀 Running V1 Baseline Backtest for NIFTY Jan 2026...")
    
    engine = BacktestEngine(initial_capital=initial_capital)
    
    # Run for the first 10 days of January as requested earlier
    # (Though the user just said "jan 2026" in the latest message, 
    # they previously said "10 days in jan2026")
    
    trades = engine.run_massive_backtest_v2(
        files=[file_path]
    )
    
    if not trades:
        print("❌ No trades were triggered in the V1 run.")
        return
        
    print(f"✅ V1 Backtest Complete. Total Trades: {len(trades)}")
    
    df_trades = pd.DataFrame(trades)
    total_pnl = df_trades['pnl'].sum()
    
    print(f"--- V1 RESULTS ---")
    print(f"Total P&L: ₹{total_pnl:,.2f}")
    for t in trades[:10]:
        print(f"Date: {t['date']} | Type: {t['type']} | Setup: {t['setup']} | PnL: {t['pnl']}")

if __name__ == "__main__":
    run_v1_backtest()
