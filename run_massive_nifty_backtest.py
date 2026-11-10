import os
import pandas as pd
from backtest_engine import BacktestEngine

def main():
    data_dir = "data/nifty200"
    all_files = sorted([os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith("_1m.csv")])
    
    # BATCH 4: Remaining Stocks (150-END)
    batch_files = all_files[150:]
    
    # Initialize Engine
    engine = BacktestEngine(initial_capital=100000.0)
    
    print(f"🚀 Starting BATCH 4 Backtest on {len(batch_files)} Stocks...")
    print("Strategy: 1% Risk/Trade (₹1,000) + Weighted Confluence + Entry Refinement + 240m Window")
    
    trades = engine.run_massive_backtest_v2(batch_files)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print("📊 MASSIVE BACKTEST PERFORMANCE")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("="*30)
    else:
        print("No trades triggered across all stocks with the current strict filters.")

if __name__ == "__main__":
    main()
