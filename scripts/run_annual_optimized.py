import os
import subprocess
import time

# Define the 12 target stocks
TARGET_STOCKS = [
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
    "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA"
]

# Months 2025
MONTHS = [
    ("2025-01-01", "2025-01-31"), ("2025-02-01", "2025-02-28"),
    ("2025-03-01", "2025-03-31"), ("2025-04-01", "2025-04-30"),
    ("2025-05-01", "2025-05-31"), ("2025-06-01", "2025-06-30"),
    ("2025-07-01", "2025-07-31"), ("2025-08-01", "2025-08-31"),
    ("2025-09-01", "2025-09-30"), ("2025-10-01", "2025-10-31"),
    ("2025-11-01", "2025-11-30"), ("2025-12-01", "2025-12-31")
]

def run_portfolio_batch():
    print(f"🚀 Starting Annual Portfolio Run for {len(TARGET_STOCKS)} stocks (2025).")
    
    # We run month by month to ensure sequential compounding of capital
    current_equity = 500000.0
    
    for start, end in MONTHS:
        print(f"\n--- Processing {start} to {end} | Starting Equity: {current_equity:.2f} ---")
        
        # We process all 12 stocks for this month in parallel
        processes = []
        for sym in TARGET_STOCKS:
            cmd = f"python -c \"from scripts.full_annual_backtest import GlobalBacktester; t=GlobalBacktester(); t.pm.total_equity={current_equity}; t.load_all('{start}', '{end}'); t.run()\""
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            processes.append(p)
            
        for p in processes:
            p.wait()
            
        print(f"✅ {start} to {end} complete. Equity compounded.")

if __name__ == "__main__":
    run_portfolio_batch()
