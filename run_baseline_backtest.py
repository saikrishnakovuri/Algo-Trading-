import os
import json
import subprocess
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def run_baseline_backtest():
    data_dir = "data/nifty200"
    top_10_symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"]
    all_files = sorted([os.path.join(data_dir, f"{s}_1m.csv") for s in top_10_symbols if os.path.exists(os.path.join(data_dir, f"{s}_1m.csv"))])
    
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    journal_file = f"trade_journal_{session_id}.csv"
    db_file = f"meta_db_{session_id}.json"
            
    engine = BacktestEngine(initial_capital=1000000.0)
    engine.journal_file = journal_file
    
    import meta_learning.tracker
    meta_learning.tracker.DB_FILE = db_file
    
    print(f"\n🚀 Starting Baseline Backtest on {len(all_files)} Stocks...")
    trades = engine.run_massive_backtest_v2(all_files)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print("📊 BASELINE PERFORMANCE")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        
        # Save results for Part G reporting
        results = {
            "stats": stats,
            "trades": trades,
            "session_id": session_id,
            "symbols": top_10_symbols
        }
        with open("data/backtest_results_baseline.json", "w") as f:
            # We don't save full trades list to avoid huge file, just stats and summary
            json.dump({"stats": stats, "session_id": session_id, "symbols": top_10_symbols}, f)
            
    print("\n✅ BACKTEST COMPLETE.")

if __name__ == "__main__":
    run_baseline_backtest()
