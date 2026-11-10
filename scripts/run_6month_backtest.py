import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import json
import logging
from datetime import datetime
from scripts.validation_backtest import ValidationBacktester

# Setup reporting
RESULTS_DIR = "data/monthly_reports"
os.makedirs(RESULTS_DIR, exist_ok=True)

MONTHS = [
    ("2026-04-17", "2026-05-15")
]

def run_all():
    global_results = []
    
    for start, end in MONTHS:
        print(f"\n--- Running Stress Test for {start} to {end} in NORMAL mode ---")
        tester = ValidationBacktester(initial_capital=500000.0)
        tester.master.mode = "NORMAL" 
        tester.run(symbol="NIFTY", start_date_str=start, end_date_str=end)
        
        # Aggregate logic
        monthly_summary = {
            "period": f"{start}_to_{end}",
            "trades": tester.metrics["total_trades"],
            "win_rate": tester.metrics.get("win_rate", "0%"),
            "profit": sum([t['net_pnl'] for t in tester.trade_log]),
        }
        global_results.append(monthly_summary)
        
    # Save Final Report
    with open(f"{RESULTS_DIR}/6_month_summary.json", "w") as f:
        json.dump(global_results, f, indent=4)
    print("\nAll backtests complete. Check data/monthly_reports/6_month_summary.json")

if __name__ == "__main__":
    run_all()
