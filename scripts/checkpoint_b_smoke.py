
import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, time, timedelta

# Add project root to path
sys.path.insert(0, os.getcwd())

from modules.strategy_selector import MasterStrategySelector

def run_smoke():
    print("🔬 Checkpoint B Smoke Run — 1-week historical data")
    
    # 1. Load NIFTY 5m data
    nifty_df = pd.read_csv("data/nifty50_5m.csv")
    col = 'Timestamp' if 'Timestamp' in nifty_df.columns else 'Datetime'
    nifty_df['Datetime'] = pd.to_datetime(nifty_df[col], utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
    nifty_df.set_index('Datetime', inplace=True); nifty_df.sort_index(inplace=True)
    nifty_df.columns = [c.lower() for c in nifty_df.columns]
    
    # Filter for last 7 days of available data
    last_date = nifty_df.index[-1].date()
    start_date = last_date - timedelta(days=7)
    df_week = nifty_df.loc[start_date:last_date].copy()
    
    selector = MasterStrategySelector()
    
    fire_counts = {
        "VWAP_BOUNCE": 0,
        "STRUCTURE_BOUNCE": 0,
        "MOMENTUM_BREAKOUT": 0,
        "MEAN_REVERSION": 0,
        "SWEEP_RETEST": 0,
        "SMC_CORE": 0,
        "CANDLESTICK": 0
    }
    
    pass_fail = {"PASS": 0, "FAIL": 0}
    
    print(f"Scanning from {start_date} to {last_date}...")
    
    # We need history for detection, find indices in main df
    start_idx = nifty_df.index.get_loc(df_week.index[0])
    if isinstance(start_idx, slice): start_idx = start_idx.start
    
    for i in range(max(50, start_idx), len(nifty_df)):
        ts = nifty_df.index[i]
        if not (time(9, 45) <= ts.time() <= time(15, 15)):
            continue
            
        # Use a mock VIX or fetch from data if available
        vix_val = 12.5 
        
        # We need to capture the print output for threshold pass/fail ratio or just track it manually
        # Step 1: Detect Context
        ctx = selector.context_detector.detect(nifty_df.iloc[:i+1], vix_val, ts)
        candidates = selector.strategy_mapper.get_candidates(ctx)
        
        if not candidates: continue
        
        for candidate in candidates:
            engine = selector.engines.get(candidate.name)
            if not engine: continue
            
            raw_signal = selector._call_engine(candidate.name, engine, nifty_df.iloc[:i+1], "NIFTY", ctx)
            if not raw_signal or not (raw_signal.get('signal') or raw_signal.get('direction') or raw_signal.get('options_direction')):
                continue
                
            score = selector.confidence_scorer.score(candidate.name, raw_signal, ctx, nifty_df.iloc[:i+1])
            
            # Threshold logic from Phase 6
            threshold = candidate.min_confidence if candidate.min_confidence > 20 else 52
            
            if score >= threshold:
                pass_fail["PASS"] += 1
                fire_counts[candidate.name] += 1
            else:
                pass_fail["FAIL"] += 1
                
    print("\n--- Smoke Run Results ---")
    print("Per-strategy fire counts:")
    for s, c in fire_counts.items():
        print(f"  {s}: {c}")
        
    total_evals = pass_fail["PASS"] + pass_fail["FAIL"]
    ratio = pass_fail["PASS"] / total_evals if total_evals > 0 else 0
    print(f"\nThreshold Pass/Fail Ratio: {ratio:.2f} ({pass_fail['PASS']}/{total_evals})")

if __name__ == "__main__":
    run_smoke()
