
import os
import pandas as pd
import numpy as np
import sys
from datetime import datetime, time

# Add project root to path
sys.path.insert(0, os.getcwd())

from modules.context_detector import ContextDetector

def run_distribution():
    # 1. Load NIFTY 5m data
    nifty_df = pd.read_csv("data/nifty50_5m.csv")
    col = 'Timestamp' if 'Timestamp' in nifty_df.columns else 'Datetime'
    nifty_df['Datetime'] = pd.to_datetime(nifty_df[col], utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
    nifty_df.set_index('Datetime', inplace=True); nifty_df.sort_index(inplace=True)
    nifty_df.columns = [c.lower() for c in nifty_df.columns]
    
    # Filter for May 5
    df_today = nifty_df.loc["2026-05-05"].copy()
    
    detector = ContextDetector()
    regimes = []
    
    # We need history for detection, so we use the full df but only record for May 5
    start_idx = nifty_df.index.get_loc(df_today.index[0])
    
    for i in range(start_idx, start_idx + len(df_today)):
        ctx = detector.detect(nifty_df.iloc[:i+1], 12.5, nifty_df.index[i])
        regimes.append(ctx.regime)
        
    df_reg = pd.Series(regimes)
    dist = df_reg.value_counts(normalize=True) * 100
    
    print("--- May 5 Regime Distribution ---")
    for r, p in dist.items():
        print(f"{r}: {p:.1f}%")

if __name__ == "__main__":
    run_distribution()
