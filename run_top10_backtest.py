import os
import pandas as pd
from backtest_engine import BacktestEngine

def main():
    # Top 10 Stocks Selection (Approximate by importance/liquidity)
    top_10_stocks = [
        "RELIANCE_1m.csv", "HDFCBANK_1m.csv", "ICICIBANK_1m.csv", 
        "INFY_1m.csv", "TCS_1m.csv", "AXISBANK_1m.csv", 
        "BHARTIARTL_1m.csv", "SBIN_1m.csv", "LT_1m.csv", "ITC_1m.csv"
    ]
    
    data_dir = "data/nifty200"
    files = [os.path.join(data_dir, f) for f in top_10_stocks]
    
    # Initialize Engine
    engine = BacktestEngine(initial_capital=100000.0)
    
    print("🚀 Starting Elite Backtest on Top 10 Stocks...")
    print("Strategy: Weighted Confluence + Market Regime Adaptation + Time-of-Day Filter + Partial Exits")
    
    trades = engine.run_massive_backtest_v2(files)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*30)
        print("📊 FINAL PERFORMANCE SUMMARY")
        print("="*30)
        for k, v in stats.items():
            print(f"{k}: {v}")
        print("="*30)
    else:
        print("No trades triggered in this period with the strict elite filters.")

if __name__ == "__main__":
    main()
