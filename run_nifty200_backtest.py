from backtest_engine import BacktestEngine
import os

def main():
    print("🚀 STARTING MASSIVE NIFTY TOP 10 BACKTEST")
    print("💰 Initial Virtual Capital: ₹1,00,000")
    print("✅ Threshold: 7/10 Checklist Points")
    print("🎯 Target RR: 1:3")
    print("🛡️ Entry: Touch-and-Bounce at Zone Lines")
    
    TOP_10_STOCKS = [
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", 
        "BHARTIARTL", "SBIN", "LICI", "ITC", "HUL"
    ]
    
    engine = BacktestEngine(initial_capital=100000.0)
    data_dir = "data/nifty200"
    
    if not os.path.exists(data_dir):
        print(f"❌ Error: Data directory {data_dir} not found. Run fetch_nifty200.py first.")
        return
    
    # Filter files to only include Top 10
    import glob
    all_files = glob.glob(os.path.join(data_dir, "*_1m.csv"))
    files = [f for f in all_files if any(s in os.path.basename(f) for s in TOP_10_STOCKS)]
    
    print(f"📁 Selected {len(files)} Top 10 stock files for backtesting.")
    
    # We need to pass the files to run_massive_backtest or modify it to accept them.
    # I'll modify BacktestEngine.run_massive_backtest to accept a file list.
    trades = engine.run_massive_backtest_v2(files)
    
    print(f"\n✅ Massive Backtest Complete. Total Trades: {len(trades)}")
    
    if trades:
        perf = engine.calculate_performance(trades)
        print("\n=== AGGREGATE PERFORMANCE (ALL STOCKS) ===")
        for k, v in perf.items():
            print(f"👉 {k}: {v}")
        
        # Calculate final equity based on total profit
        final_equity = 100000.0 + perf['Total Profit']
        print(f"\n💵 Final Virtual Equity: ₹{final_equity:,.2f}")
        print(f"📈 Total PnL: ₹{perf['Total Profit']:,.2f}")

if __name__ == '__main__':
    main()
