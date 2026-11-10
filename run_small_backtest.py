import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def run_small_backtest():
    # Only 2 symbols for speed
    top_symbols = ["RELIANCE", "HDFCBANK"]
    data_dir = "data/angel_historical"
    
    all_files = []
    for s in top_symbols:
        p = os.path.join(data_dir, f"{s}_1m.csv")
        if os.path.exists(p):
            all_files.append(p)
            
    if not all_files:
        print("❌ No data found.")
        return

    # Initialize Engine
    engine = BacktestEngine(initial_capital=1000000.0)
    
    # Run backtest with limit on sessions (simulated via file slice if needed, 
    # but massive_backtest processes entire file. We'll just report the small output.)
    print(f"\n🚀 Running Small Smoke Backtest on: {top_symbols}...")
    
    # We'll just run it. With 2 stocks, it should be very fast.
    trades = engine.run_massive_backtest_v2(all_files)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print("📊 SMOKE TEST PERFORMANCE")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
            
    print("\n✅ SMOKE TEST COMPLETE.")

if __name__ == "__main__":
    run_small_backtest()
