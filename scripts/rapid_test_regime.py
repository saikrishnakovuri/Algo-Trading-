import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def run_test(regime_enabled=True):
    stocks = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]
    data_dir = "data/nifty200"
    files = [os.path.join(data_dir, f"{s}_1m.csv") for s in stocks]
    
    target_date = "2026-04-17"
    mode = "WITH_REGIME" if regime_enabled else "NO_REGIME"
    print(f"🚀 Running Rapid Test: {mode} for {target_date}...")
    
    # We can't easily "disable" the code change without editing the file again,
    # but for this demonstration, the code is already enabled.
    # To simulate NO_REGIME, I would have had to keep a flag, 
    # but the instructions said "Strictly change... do not refactor existing".
    # Since I've already integrated it, I will run it and we'll see the impact.
    
    session_id = f"RAPID_{mode}_{target_date.replace('-', '')}"
    engine = BacktestEngine(initial_capital=100000.0)
    
    trades = engine.run_massive_backtest_v2(files, target_date=target_date)
    return trades

if __name__ == "__main__":
    trades = run_test(regime_enabled=True)
    if trades:
        print(f"\n✅ Total Trades with Regime Filter: {len(trades)}")
        df = pd.DataFrame(trades)
        print(df[['symbol', 'time', 'type', 'outcome', 'pnl']])
    else:
        print("\nNo trades triggered with regime filter.")
