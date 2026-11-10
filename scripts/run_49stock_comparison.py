import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import json
import logging
from scripts.validation_backtest import ValidationBacktester

# Silence spam
logging.getLogger("SMC_Engine").setLevel(logging.WARNING)
logging.getLogger("SMC_Structure").setLevel(logging.WARNING)
logging.getLogger("modules.strategy_selector").setLevel(logging.WARNING)

MONTHS = [
    ("2025-01-01", "2025-12-31")
]

DATA_PATH = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"
EXCLUDE = ["RELIANCE"]

def run_batch_comparison():
    modes = ["NORMAL", "BALANCED"]
    final_comparison = {}
    
    for mode in modes:
        print(f"\n🚀 STARTING BATCH: {mode} MODE (1% Risk)")
        results = []
        count = 0
        
        for stock_file in os.listdir(DATA_PATH):
            if stock_file.endswith("_minute.csv"):
                symbol = stock_file.split('_')[0]
                if symbol in EXCLUDE: continue
                
                print(f"[{mode}] Progress: {count+1}/49 | Testing {symbol}...")
                tester = ValidationBacktester(initial_capital=500000.0)
                tester.master.mode = mode
                
                # Run full year
                tester.run_for_symbol(symbol, "2025-01-01", "2025-12-31")
                
                df = pd.DataFrame(tester.trade_log)
                if not df.empty:
                    results.append({
                        "stock": symbol,
                        "trades": len(df),
                        "win_rate": f"{(len(df[df['net_pnl'] > 0]) / len(df)) * 100:.1f}%",
                        "pnl": df['net_pnl'].sum()
                    })
                
                count += 1
                if count >= 49: break # Cap at 49 remaining

        final_comparison[mode] = results

    # Final Output
    for mode, data in final_comparison.items():
        print(f"\n--- {mode} MODE SUMMARY ---")
        if data:
            df_final = pd.DataFrame(data)
            print(df_final.to_markdown(index=False))
            print(f"\nTotal PnL ({mode}): ₹{df_final['pnl'].sum():.2f}")
        else:
            print("No trades generated.")

if __name__ == "__main__":
    run_batch_comparison()
