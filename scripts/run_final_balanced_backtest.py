import subprocess
import os
import time
import pandas as pd

# Define target stocks
TARGET_STOCKS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL"
]

def run_backtest():
    print(f"🚀 Starting Annual 2025 Backtest in BALANCED mode...")
    
    for sym in TARGET_STOCKS:
        print(f"--- Processing {sym} ---")
        # Run in BALANCED mode specifically
        cmd = f"python -c \"from scripts.validation_backtest import ValidationBacktester; t=ValidationBacktester(); t.master.mode='BALANCED'; t.run(symbol='{sym}', start_date_str='2025-01-01', end_date_str='2025-12-31')\""
        subprocess.run(cmd, shell=True)
        print(f"✅ {sym} Complete.")

if __name__ == "__main__":
    run_backtest()
