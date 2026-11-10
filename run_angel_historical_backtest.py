import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine
from meta_learning.analyzer import analyze, compute_metrics

def main():
    data_dir = "data/angel_historical"
    if not os.path.exists(data_dir):
        print(f"❌ Data directory {data_dir} not found.")
        return
        
    all_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith("_1m.csv")]
    
    # Filter for all available 25 stocks
    all_files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith("_1m.csv")]
    
    if not all_files:
        print("❌ No data files found in angel_historical.")
        return

    print(f"🚀 Starting Historical Backtest on {len(all_files)} Top Stocks (30 Days of 1m Data)...")
    print("Settings: Bias-Free Swings, Momentum Filter, 2% Daily Stop, Compounding Equity")

    # Clean old session files for a fresh test
    session_id = "ANGEL_HIST_30D"
    journal_file = f"trade_journal_{session_id}.csv"
    db_file = f"meta_db_{session_id}.json"

    # Persistent Meta-Learning: Stop deleting the meta-database between historical runs.
    if os.path.exists(journal_file): os.remove(journal_file)
    # if os.path.exists(db_file): os.remove(db_file)
            
    engine = BacktestEngine(initial_capital=100000.0)
    engine.journal_file = journal_file
    
    # Patch the meta-tracker
    import meta_learning.tracker
    meta_learning.tracker.DB_FILE = db_file
    
    # Run Backtest
    trades = engine.run_massive_backtest_v2(all_files)
    
    if trades:
        stats = engine.calculate_performance(trades)
        print("\n" + "="*50)
        print("📊 30-DAY HISTORICAL BACKTEST RESULTS")
        print("="*50)
        for k, v in stats.items():
            print(f"{k:20}: {v}")
        
        # Meta Analysis
        with open(db_file, "r") as f:
            db_trades = json.load(f)
        
        m_stats = analyze(db_trades)
        print("\n🎯 TOP PERFORMING STOCKS (Last 30 Days):")
        # Collect stock profits
        stock_pnls = []
        for stock, pnls in m_stats["by_stock"].items():
            stock_pnls.append({"Symbol": stock, "PnL": round(sum(pnls), 2), "Trades": len(pnls)})
        
        df_stocks = pd.DataFrame(stock_pnls).sort_values(by="PnL", ascending=False)
        print(df_stocks.head(10).to_string(index=False))
        
        print("\n⏰ TIME-WINDOW PERFORMANCE:")
        for window, pnls in m_stats["by_time_window"].items():
            m = compute_metrics(pnls)
            print(f"- {window:35} | PnL: ₹{sum(pnls):8.2f} | Win%: {m['win_rate']}%")
            
        print("="*50)
    else:
        print("No trades triggered in the last 30 days with current strict filters.")

if __name__ == "__main__":
    main()
