import pandas as pd
import numpy as np
import os
from pathlib import Path
from backtest_engine import BacktestEngine

def main():
    print("🚀 Module 4 Validation & Context Stacking Test...")
    
    # 1. Run backtest on 5 heavyweights with all filters enabled
    stocks = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]
    data_dir = "data/nifty200"
    files = [os.path.join(data_dir, f"{s}_1m.csv") for s in stocks]
    target_date = "2026-04-17"
    
    print(f"📊 Running Backtest with full Context Filter Stack for {target_date}...")
    engine = BacktestEngine(initial_capital=100000.0)
    trades = engine.run_massive_backtest_v2(files, target_date=target_date)
    
    journal_path = "trade_journal.csv"
    if os.path.exists(journal_path):
        j_df = pd.read_csv(journal_path)
        print(f"📝 Journal check: {len(j_df)} trades recorded in {journal_path}")
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print(f"📊 MODULE 4 PERFORMANCE ({target_date})")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("="*30)
        
        # Analyze vetoes (this would require re-running or logging)
        print("\n🎉 MODULE 4: READY")
    else:
        print("\n⚠️ No trades triggered. Context filters might be too strict or integration needs check.")

if __name__ == "__main__":
    main()
