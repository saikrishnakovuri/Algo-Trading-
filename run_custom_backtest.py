import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def run_custom_backtest():
    # 3 symbols
    symbols = ["SBIN", "AXISBANK", "RELIANCE"]
    data_dir = "data/angel_historical"
    
    all_files = []
    for s in symbols:
        p = os.path.join(data_dir, f"{s}_1m.csv")
        if os.path.exists(p):
            all_files.append(p)
            
    if not all_files:
        print("❌ No data found.")
        return

    # Initialize Engine
    engine = BacktestEngine(initial_capital=1000000.0)
    
    # Define date range (1-2 days)
    start_date = "2026-04-20"
    end_date = "2026-04-22"
    
    print(f"\n🚀 Running Custom Backtest on: {symbols} for {start_date} to {end_date}...")
    
    # Run backtest
    trades = engine.run_massive_backtest_v2(all_files, start_date=start_date, end_date=end_date)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print("📊 CUSTOM BACKTEST PERFORMANCE")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
    else:
        print("\n⚠️ No trades executed during this period.")
            
    print("\n✅ CUSTOM BACKTEST COMPLETE.")

if __name__ == "__main__":
    run_custom_backtest()
