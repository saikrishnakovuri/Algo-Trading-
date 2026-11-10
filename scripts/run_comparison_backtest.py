import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import json
from scripts.validation_backtest import ValidationBacktester

MONTHS = [
    ("2025-10-01", "2025-10-31"),
    ("2025-11-01", "2025-11-30"),
    ("2025-12-01", "2025-12-31"),
    ("2026-01-01", "2026-01-31"),
    ("2026-02-01", "2026-02-28"),
    ("2026-04-01", "2026-04-30")
]

def run_comparison():
    modes = ["NORMAL", "BALANCED"]
    results = {}
    
    for mode in modes:
        print(f"\n=== STARTING MODE: {mode} ===")
        mode_results = []
        for start, end in MONTHS:
            print(f"Testing {start} to {end}...")
            tester = ValidationBacktester(initial_capital=500000.0)
            tester.master.mode = mode
            tester.run(symbol="NIFTY", start_date_str=start, end_date_str=end)
            
            # Extract detailed metrics
            log_df = pd.DataFrame(tester.trade_log)
            pnl = log_df['net_pnl'].sum() if not log_df.empty else 0
            win_rate = len(log_df[log_df['net_pnl'] > 0]) / len(log_df) if not log_df.empty else 0
            
            mode_results.append({
                "period": f"{start}_{end}",
                "pnl": pnl,
                "win_rate": win_rate,
                "trades": len(log_df),
                "drawdown": tester._calculate_drawdown(log_df['net_pnl']) if not log_df.empty else "0.00%"
            })
        results[mode] = mode_results

    with open("data/comparison_results.json", "w") as f:
        json.dump(results, f, indent=4)
    print("\nComparison complete. Results in data/comparison_results.json")

if __name__ == "__main__":
    run_comparison()
