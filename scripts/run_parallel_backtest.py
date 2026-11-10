import subprocess
import os
import time
import pandas as pd

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"
RESULTS_DIR = "data/backtest_results"
LOG_FILE = "logs/parallel_backtest_status.log"

os.makedirs("logs", exist_ok=True)

# List of all symbols
all_symbols = [f.split('_')[0] for f in os.listdir(DATA_PATH) if f.endswith("_minute.csv")]
NIFTY_50 = {"ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"}

target_symbols = [s for s in all_symbols if s in NIFTY_50 and s != "RELIANCE"]

def run_chunk(symbols):
    processes = []
    chunk_size = 8 # Increased parallelization
    
    with open(LOG_FILE, "w") as log:
        log.write(f"Starting Parallel Backtest for {len(symbols)} stocks at {time.ctime()}\n")

    for i in range(0, len(symbols), chunk_size):
        chunk = symbols[i:i+chunk_size]
        msg = f"🚀 Launching Chunk {i//chunk_size + 1}: {chunk}\n"
        print(msg.strip())
        with open(LOG_FILE, "a") as log: log.write(msg)
        
        for sym in chunk:
            # Run in BALANCED mode as primary test
            cmd = f"python -c \"from scripts.validation_backtest import ValidationBacktester; t=ValidationBacktester(); t.master.mode='BALANCED'; t.run(symbol='{sym}', start_date_str='2025-01-01', end_date_str='2025-12-31')\""
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(p)
        
        # Wait for chunk to finish
        for p in processes:
            p.wait()
        
        processes = []
        msg = f"✅ Chunk {i//chunk_size + 1} Complete.\n"
        print(msg.strip())
        with open(LOG_FILE, "a") as log: log.write(msg)

if __name__ == "__main__":
    run_chunk(target_symbols)
