import os
import json
import subprocess
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def run_calibrated_backtest():
    # Use the larger 30-day dataset
    data_dir = "data/angel_historical"
    top_10_symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"]
    all_files = sorted([os.path.join(data_dir, f"{s}_1m.csv") for s in top_10_symbols if os.path.exists(os.path.join(data_dir, f"{s}_1m.csv"))])
    
    if not all_files:
        print("❌ No data found in data/angel_historical. Fallback to data/nifty200")
        data_dir = "data/nifty200"
        all_files = sorted([os.path.join(data_dir, f"{s}_1m.csv") for s in top_10_symbols if os.path.exists(os.path.join(data_dir, f"{s}_1m.csv"))])

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    journal_file = f"trade_journal_calibrated_{session_id}.csv"
    db_file = f"meta_db_calibrated_{session_id}.json"
            
    engine = BacktestEngine(initial_capital=1000000.0)
    engine.journal_file = journal_file
    
    import meta_learning.tracker
    meta_learning.tracker.DB_FILE = db_file
    
    print(f"\n🚀 Starting Calibrated Backtest on {len(all_files)} Stocks...")
    print(f"Data Directory: {data_dir}")
    
    trades = engine.run_massive_backtest_v2(all_files)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print("📊 CALIBRATED PERFORMANCE")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        
        # Save results for Part G reporting
        with open("data/backtest_results_calibrated.json", "w") as f:
            json.dump({
                "stats": stats, 
                "session_id": session_id, 
                "symbols": top_10_symbols,
                "data_range": "30 Days (Angel Historical)"
            }, f)
            
    print("\n✅ BACKTEST COMPLETE.")

if __name__ == "__main__":
    run_calibrated_backtest()
