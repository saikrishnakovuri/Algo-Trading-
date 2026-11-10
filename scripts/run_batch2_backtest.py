import subprocess
import os
import time
import pandas as pd

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"
RESULTS_DIR = "data/backtest_results"
LOG_FILE = "logs/parallel_backtest_status.log"

os.makedirs("logs", exist_ok=True)

# Full Nifty 50 Set
NIFTY_50 = ["ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"]

# Already processed
EXCLUDED = {"RELIANCE", "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL"}

# Next 10 targets
TARGET_STOCKS = [s for s in NIFTY_50 if s not in EXCLUDED][:10]

def run_chunk(symbols):
    print(f"🚀 Launching Second Batch: {symbols}")
    processes = []
    for sym in symbols:
        # Run in BALANCED mode
        cmd = f"python -c \"from scripts.validation_backtest import ValidationBacktester; t=ValidationBacktester(); t.master.mode='BALANCED'; t.run(symbol='{sym}', start_date_str='2025-01-01', end_date_str='2025-12-31')\""
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(p)
    
    for p in processes:
        p.wait()
    print("✅ Batch Complete.")

if __name__ == "__main__":
    run_chunk(TARGET_STOCKS)
