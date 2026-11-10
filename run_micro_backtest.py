import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def run_micro_backtest():
    # Only 5 symbols for maximum speed
    top_symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]
    data_dir = "data/angel_historical"
    
    all_files = []
    for s in top_symbols:
        p = os.path.join(data_dir, f"{s}_1m.csv")
        if os.path.exists(p):
            all_files.append(p)
            
    if not all_files:
        print("❌ No data found.")
        return

    # Initialize Engine with 10L Capital
    engine = BacktestEngine(initial_capital=1000000.0)
    engine.journal_file = "trade_journal_micro.csv"
    
    # Target ONLY 1 Day for statistical verification of the loop fix
    target_day = "2026-04-15"
    
    print(f"\n🚀 Running MICRO Backtest (5 Stocks, 1 Day: {target_day})...")
    
    trades = engine.run_massive_backtest_v2(all_files, target_date=target_day)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print(f"📊 MICRO TEST PERFORMANCE ({target_day})")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
            
    print("\n✅ MICRO TEST COMPLETE.")

if __name__ == "__main__":
    run_micro_backtest()
