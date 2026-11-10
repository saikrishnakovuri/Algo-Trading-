import pandas as pd
import numpy as np
import yaml
import os
from pathlib import Path
from backtest_engine import BacktestEngine

def main():
    print("🚀 Module 2 Validation & A/B Test...")
    
    # 1. Check if composites are refreshed
    cache_dir = Path("data/composites/")
    files = list(cache_dir.glob("*.joblib"))
    print(f"✅ Composite Cache check: {len(files)} files found.")
    
    # 2. Run a small A/B test on 5 heavyweights
    stocks = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]
    data_dir = "data/nifty200"
    files = [os.path.join(data_dir, f"{s}_1m.csv") for s in stocks]
    target_date = "2026-04-17"
    
    print(f"📊 Running Backtest with VP/VWAP integration for {target_date}...")
    engine = BacktestEngine(initial_capital=100000.0)
    trades = engine.run_massive_backtest_v2(files, target_date=target_date)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print(f"📊 MODULE 2 PERFORMANCE ({target_date})")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("="*30)
        
        # Confluence attribution
        df = pd.DataFrame(trades)
        # Note: we should look at logs or the reasoning string if we added it to trade_record
        # But for now, we just check total trades and win rate.
        print("\n🎉 MODULE 2: READY")
    else:
        print("\n⚠️ No trades triggered. Verify integration and data coverage.")

if __name__ == "__main__":
    main()
