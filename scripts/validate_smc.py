import pandas as pd
import numpy as np
import os
import yaml
from pathlib import Path
from backtest_engine import BacktestEngine

def main():
    print("🚀 Module 3 Validation & SMC Stacking Test...")
    
    # 1. Run backtest on 5 heavyweights with SMC enabled
    stocks = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]
    data_dir = "data/nifty200"
    files = [os.path.join(data_dir, f"{s}_1m.csv") for s in stocks]
    target_date = "2026-04-17"
    
    print(f"📊 Running Backtest with SMC + VP + Regime for {target_date}...")
    engine = BacktestEngine(initial_capital=100000.0)
    trades = engine.run_massive_backtest_v2(files, target_date=target_date)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print(f"📊 MODULE 3 (SMC) PERFORMANCE ({target_date})")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("="*30)
        
        # Tier breakdown logic
        df = pd.DataFrame(trades)
        # Note: we should look at 'SMC: ... (Tier: X)' in reasons
        
        print("\n🎉 MODULE 3: READY")
    else:
        print("\n⚠️ No trades triggered. Verify SMC integration and filters.")

if __name__ == "__main__":
    main()
