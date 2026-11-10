import os
import json
import subprocess
from datetime import datetime
from backtest_engine import BacktestEngine

def run_all_batches():
    data_dir = "data/nifty200"
    # Target Top 10 Liquid Stocks by volume/turnover as per universe
    top_10_symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"]
    all_files = sorted([os.path.join(data_dir, f"{s}_1m.csv") for s in top_10_symbols if os.path.exists(os.path.join(data_dir, f"{s}_1m.csv"))])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    journal_file = f"trade_journal_batch_{timestamp}.csv"
    db_file = f"meta_db_batch_{timestamp}.json"
    
    print(f"📁 Session Journal: {journal_file}")
    print(f"📁 Session Database: {db_file}")

    engine = BacktestEngine(initial_capital=1000000.0)
    engine.journal_file = journal_file # Set engine to use new file
    
    # Patch the meta-tracker to use the session DB
    import meta_learning.tracker
    meta_learning.tracker.DB_FILE = db_file
    
    # Run all Top 10 stocks in one go
    print(f"\n🚀 Starting Backtest on {len(all_files)} Stocks...")
    engine.run_massive_backtest_v2(all_files)
    
    print("\n✅ BACKTEST COMPLETE.")
    print("📊 Running Meta-Analysis...")
    # Pass the custom DB file to the meta-analysis script if it supports it, 
    # or just rely on it being the latest.
    subprocess.run(["python", "run_meta_analysis.py"])

if __name__ == "__main__":
    run_all_batches()
