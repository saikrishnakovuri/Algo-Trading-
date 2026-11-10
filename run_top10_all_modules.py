import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def main():
    # Top 10 Heavyweights
    top10 = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS",
        "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"
    ]

    data_dir = "data/nifty200"
    files = []
    for sym in top10:
        f_path = os.path.join(data_dir, f"{sym}_1m.csv")
        if os.path.exists(f_path):
            files.append(f_path)
    
    target_date = "2026-04-16"
    print(f"🚀 Starting Top 10 Full-Stack Backtest for {target_date}...")
    
    session_id = f"TOP10_FULL_{target_date.replace('-', '')}"
    journal_file = f"trade_journal_{session_id}.csv"
    
    if os.path.exists(journal_file): os.remove(journal_file)
            
    engine = BacktestEngine(initial_capital=100000.0)
    engine.journal_file = journal_file
    
    # Run Backtest
    trades = engine.run_massive_backtest_v2(files, target_date=target_date)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print(f"📊 TOP 10 FULL-STACK PERFORMANCE ({target_date})")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("="*30)
    else:
        print(f"No trades triggered for {target_date} with all modules and filters active.")

if __name__ == "__main__":
    main()
