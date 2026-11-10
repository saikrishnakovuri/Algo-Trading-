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
    
    print(f"🚀 Starting V3 Test on {len(files)} Nifty 50 Stocks...")
    print("Settings: 5m/15m MTF, ATR Stops, Gap Filter, 09:45-10:30 Structured Move")

    # Clean old session files for a fresh test
    session_id = "NIFTY50_TEST"
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
    trades = engine.run_massive_backtest_v2(files)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*40)
        print("📊 NIFTY 50 V3 TEST RESULTS")
        print("="*40)
        for k, v in stats.items():
            print(f"{k}: {v}")
        
        # Meta Analysis
        with open(db_file, "r") as f:
            db_trades = json.load(f)
        
        m_stats = analyze(db_trades)
        print("\n🎯 TOP NIFTY 50 PERFORMERS:")
        for stock, pnls in m_stats["by_stock"].items():
            if sum(pnls) > 0:
                print(f"- {stock}: ₹{sum(pnls):.2f}")
        print("="*40)
    else:
        print("No trades triggered for Nifty 50 with V3 filters.")

if __name__ == "__main__":
    main()
