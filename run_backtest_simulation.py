from modules.data_layer import DataLayer
from backtest_engine import BacktestEngine
import pandas as pd

def main():
    print("🚀 Starting NIFTY 1-Month Virtual Simulation (Backtest Mode)")
    print("💰 Initial Virtual Capital: ₹1,00,000")
    
    dl = DataLayer()
    # Fetch as much data as possible for a robust backtest
    # yfinance 1m is limited to 7 days usually.
    print("fetching multi-timeframe data...")
    mtf_data = dl.get_multi_timeframe_data()
    
    # Check if all required dataframes are present and not empty
    data_valid = True
    for tf, df in mtf_data.items():
        if df is None or df.empty:
            print(f"❌ Missing or empty data for timeframe: {tf}")
            data_valid = False
            
    if not data_valid:
        return

    engine = BacktestEngine(initial_capital=100000.0)
    
    print("🏃 Running simulation over available historical bars...")
    trades = engine.run_simulation(mtf_data)
    
    print(f"✅ Simulation Complete. Total trades found: {len(trades)}")
    
    if trades:
        print("\n📊 CALCULATING PERFORMANCE METRICS...")
        performance = engine.calculate_performance(trades)
        
        print("\n=== PERFORMANCE REPORT ===")
        for k, v in performance.items():
            print(f"👉 {k}: {v}")
            
        print(f"\n📝 All trades have been logged to 'trade_journal.csv'")
    else:
        print("\n⚠️ No trades were triggered during this period with the current 70% confidence threshold.")
        print("Try running during market hours or with more historical data.")

if __name__ == '__main__':
    main()
