
import os
import pandas as pd
import numpy as np
import sys

# Add project root to path
sys.path.insert(0, os.getcwd())

from datetime import datetime, time
from modules.options.signal_adapter import IndexLiquidityTrapAdapter

def run_verify():
    print("🔬 Phase 1 Verification — VWAP_BOUNCE definition audit")
    
    # 1. Load NIFTY 5m data
    nifty_df = pd.read_csv("data/nifty50_5m.csv")
    # Handle both possible column names
    col = 'Timestamp' if 'Timestamp' in nifty_df.columns else 'Datetime'
    nifty_df['Datetime'] = pd.to_datetime(nifty_df[col], utc=True).dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
    nifty_df.set_index('Datetime', inplace=True); nifty_df.sort_index(inplace=True)
    nifty_df.columns = [c.lower() for c in nifty_df.columns]
    
    # 2. Setup adapter
    adapter = IndexLiquidityTrapAdapter()
    
    signals = []
    
    # Mock data for adapter
    mock_oi = {}
    vix_val = 12.5
    pcr_proxy = 1.0
    
    # 3. Scan for signals
    print("Scanning for VWAP_BOUNCE signals (Oct 2025 - May 2026)...")
    for i in range(50, len(nifty_df)):
        ts = nifty_df.index[i]
        
        # Check only between 09:45 and 15:15
        if not (time(9, 45) <= ts.time() <= time(15, 15)):
            continue
            
        sig = adapter.evaluate_signal(nifty_df.iloc[:i+1], "NIFTY", vix_val, pcr_proxy, mock_oi, False)
        
        if sig and sig['strategy'] == 'VWAP_BOUNCE':
            signals.append({
                'timestamp': ts,
                'direction': sig['options_direction'],
                'price': sig['spot_price']
            })
            
    df_sig = pd.DataFrame(signals)
    
    # 4. Results
    print(f"\n1. Total VWAP_BOUNCE signals generated (before any filter): {len(df_sig)}")
    
    # May 5 check
    may5_signals = df_sig[df_sig['timestamp'].dt.date == datetime(2026, 5, 5).date()]
    print(f"2. Count on May 5 specifically: {len(may5_signals)}")
    
    if not may5_signals.empty:
        print("\nMay 5 Signals Detail:")
        for _, s in may5_signals.iterrows():
            print(f" - {s['timestamp'].time()} | {s['direction']} @ {s['price']:.2f}")
    
    if len(may5_signals) >= 3:
        print("\nRESULT: PASS ✅ (Count >= 3)")
    else:
        print(f"\nRESULT: FAIL ❌ (Count {len(may5_signals)} < 3)")

if __name__ == "__main__":
    run_verify()
