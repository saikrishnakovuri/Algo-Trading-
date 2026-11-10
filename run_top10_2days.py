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
    
    target_dates = ["2026-04-16", "2026-04-17"]
    print(f"🚀 Starting Top 10 Full-Stack Backtest for {target_dates}...")
    
    session_id = f"TOP10_2DAYS"
    journal_file = f"trade_journal_{session_id}.csv"
    
    if os.path.exists(journal_file): os.remove(journal_file)
            
    engine = BacktestEngine(initial_capital=100000.0)
    engine.journal_file = journal_file
    
    # Custom Loop for multiple days
    all_trades = []
    for target_date in target_dates:
        print(f"\n📅 DATE: {target_date}")
        trades = engine.run_massive_backtest_v2(files, target_date=target_date)
        all_trades.extend(trades)
    
    if all_trades:
        stats = engine.calculate_performance(all_trades)
        print("\n" + "="*30)
        print(f"📊 TOP 10 PERFORMANCE (OVER 2 DAYS)")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("="*30)
    else:
        print(f"No trades triggered for the selected dates.")

if __name__ == "__main__":
    main()
