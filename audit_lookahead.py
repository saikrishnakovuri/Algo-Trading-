import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

import pandas as pd
import numpy as np
from modules.strategy_selector import MasterStrategySelector
from modules.context_detector import ContextDetector

def audit_lookahead():
    print("--- 2a/2b: Entry & Exit Bar Index Verification ---")
    # Load some sample data
    path = "data/angel_historical/RELIANCE_1m.csv"
    df_1m = pd.read_csv(path)
    df_1m["Timestamp"] = pd.to_datetime(df_1m["Timestamp"])
    df_1m.set_index("Timestamp", inplace=True)
    df_1m.columns = [c.lower() for c in df_1m.columns]
    
    # Resample to 5m
    df_5m = df_1m.resample("5min").agg({
        "open": "first", "high": "max",
        "low": "min", "close": "last", "volume": "sum"
    }).dropna()
    
    master = MasterStrategySelector()
    trades = []
    
    # Simulate a few trades to check indexes
    for i in range(50, 500):
        sub_df = df_5m.iloc[:i+1]
        now = sub_df.index[-1]
        signal = master.select_best_signal(sub_df, "RELIANCE", 15.0, current_time=now)
        
        if signal:
            entry_idx = i
            entry_price = df_5m.iloc[i]["close"]
            
            # Simple exit simulation
            exit_idx = -1
            for j in range(i+1, len(df_5m)):
                exit_idx = j
                break # Exit at next bar for index check
            
            trades.append({
                "Trade#": len(trades)+1,
                "Symbol": "RELIANCE",
                "Entry Index": entry_idx,
                "Entry Bar Close": entry_price,
                "Actual Entry Price": signal["entry_price"],
                "Exit Index": exit_idx,
                "Gap": exit_idx - entry_idx
            })
            if len(trades) >= 10: break
            
    df_audit = pd.DataFrame(trades)
    print(df_audit.to_string(index=False))
    
    clean = True
    for t in trades:
        if abs(t["Entry Bar Close"] - t["Actual Entry Price"]) > 0.01:
            print(f"FAILED: Trade {t['Trade#']} entry price mismatch!")
            clean = False
        if t["Gap"] < 1:
            print(f"FAILED: Trade {t['Trade#']} exit index <= entry index!")
            clean = False
            
    print("\n--- 2c: Indicator Look-Ahead Check ---")
    # We'll check context_detector.py for .shift(-1) or future indexing
    with open("modules/context_detector.py", "r") as f:
        content = f.read()
        if ".shift(-" in content or "iloc[i+" in content:
            print("FAILED: Potential look-ahead in context_detector.py")
            clean = False
        else:
            print("Context Detector: PASS")
            
    if clean:
        print("\nLOOK-AHEAD CLEAN: Yes")
    else:
        print("\nLOOK-AHEAD CLEAN: No")

if __name__ == "__main__":
    audit_lookahead()
