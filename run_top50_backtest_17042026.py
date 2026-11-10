import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine
from meta_learning.analyzer import analyze, compute_metrics

def main():
    # NIFTY 50 LIST
    nifty50 = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
        "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL",
        "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY",
        "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE",
        "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK",
        "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT",
        "LTIM", "M&M", "MARUTI", "NESTLEIND", "NTPC",
        "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN",
        "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS",
        "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"
    ]

    data_dir = "data/nifty200"
    files = []
    for sym in nifty50:
        f_path = os.path.join(data_dir, f"{sym}_1m.csv")
        if os.path.exists(f_path):
            files.append(f_path)
    
    target_date = "2026-04-17"
    print(f"🚀 Starting Top 50 Backtest for {target_date}...")
    
    session_id = f"TOP50_{target_date.replace('-', '')}"
    journal_file = f"trade_journal_{session_id}.csv"
    db_file = f"meta_db_{session_id}.json"
    
    if os.path.exists(journal_file): os.remove(journal_file)
    if os.path.exists(db_file): os.remove(db_file)
            
    engine = BacktestEngine(initial_capital=100000.0)
    engine.journal_file = journal_file
    
    # Patch the meta-tracker
    import meta_learning.tracker
    meta_learning.tracker.DB_FILE = db_file
    
    # Run Backtest
    trades = engine.run_massive_backtest_v2(files, target_date=target_date)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print(f"📊 TOP 50 PERFORMANCE ({target_date})")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("="*30)
    else:
        print(f"No trades triggered for {target_date} with the current strict filters.")

if __name__ == "__main__":
    main()
