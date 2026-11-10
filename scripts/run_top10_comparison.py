import subprocess
import os
import time

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"
LOG_FILE = "logs/parallel_backtest_status.log"

os.makedirs("logs", exist_ok=True)

# Select Top 10 Stocks available in folder (excluding Reliance which was done)
# Let's pick 10 liquid ones from the list I see
TARGET_STOCKS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL"
]

def run_chunk(symbols):
    modes = ["NORMAL", "BALANCED"]
    
    with open(LOG_FILE, "w", encoding="utf-8") as log:
        log.write(f"Starting Top 10 Parallel Backtest at {time.ctime()}\n")

    for mode in modes:
        processes = []
        chunk_size = 5 # 5 parallel processes
        
        msg = f"STARTING MODE: {mode}\n"
        print(msg.strip())
        with open(LOG_FILE, "a", encoding="utf-8") as log: log.write(msg)

        for i in range(0, len(symbols), chunk_size):
            chunk = symbols[i:i+chunk_size]
            msg = f"Launching Chunk {i//chunk_size + 1}: {chunk}\n"
            print(msg.strip())
            with open(LOG_FILE, "a", encoding="utf-8") as log: log.write(msg)
            
            for sym in chunk:
                # 1% risk is already set in risk_manager.py
                cmd = f"python -c \"from scripts.validation_backtest import ValidationBacktester; t=ValidationBacktester(); t.master.mode='{mode}'; t.run(symbol='{sym}', start_date_str='2025-01-01', end_date_str='2025-12-31')\""
                p = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                processes.append(p)
            
            # Wait for chunk to finish
            for p in processes:
                p.wait()
            
            processes = []
            msg = f"Chunk {i//chunk_size + 1} Complete.\n"
            print(msg.strip())
            with open(LOG_FILE, "a", encoding="utf-8") as log: log.write(msg)

    print("\nALL MODES COMPLETE FOR TOP 10 STOCKS.")
    with open(LOG_FILE, "a", encoding="utf-8") as log: log.write("ALL MODES COMPLETE.\n")

if __name__ == "__main__":
    run_chunk(TARGET_STOCKS)
