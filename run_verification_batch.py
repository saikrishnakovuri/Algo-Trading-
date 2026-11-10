import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def run_verification():
    # Remaining 7 stocks
    other_7_symbols = ["INFY", "TCS", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"]
    data_dir = "data/angel_historical"
    
    all_files = sorted([os.path.join(data_dir, f"{s}_1m.csv") for s in other_7_symbols if os.path.exists(os.path.join(data_dir, f"{s}_1m.csv"))])

    journal_file = "trade_journal_verification.csv"
    if os.path.exists(journal_file):
        os.remove(journal_file)
            
    engine = BacktestEngine(initial_capital=1000000.0)
    engine.journal_file = journal_file
    
    print(f"\n🚀 Starting Verification Batch (7 Stocks, 30 Days)...")
    print(f"Active Strategies: TRAP_REVERSAL, OB_MITIGATION, etc. (ZONE_REJECTION disabled for these non-bank stocks)")
    
    trades = engine.run_massive_backtest_v2(all_files)
    
    if trades:
        for t in trades:
            risk = abs(t['entry'] - t['sl'])
            t['r_multiple'] = round(t['pnl'] / (risk * t['qty']), 2) if risk > 0 else 0
            
        df = pd.DataFrame(trades)
        stats = engine.calculate_performance(trades)
        
        print("\n" + "="*50)
        print("📊 VERIFICATION BATCH PERFORMANCE")
        print("="*50)
        
        results = []
        for sym in df['symbol'].unique():
            sdf = df[df['symbol'] == sym]
            wins = sdf[sdf['pnl'] > 0]
            row = {
                "Stock": sym,
                "Trades": len(sdf),
                "Win%": f"{round(len(wins)/len(sdf)*100, 1)}%",
                "Exp(R)": round(sdf['r_multiple'].mean(), 2),
                "P&L": round(sdf['pnl'].sum(), 0)
            }
            results.append(row)
        
        print(pd.DataFrame(results).to_string(index=False))
        print("-" * 50)
        print(f"Total Trades: {stats['Total Trades']}")
        print(f"Overall Win Rate: {stats['Win Rate %']}%")
        print(f"Overall Expectancy: {df['r_multiple'].mean():.2f}R")
        print(f"Total Profit: {stats['Total Profit']:.2f} INR")
        
        with open("data/backtest_results_verification.json", "w") as f:
            json.dump(stats, f)
    else:
        print("ℹ️ No trades taken for this batch (Strict filtering active).")

if __name__ == "__main__":
    run_verification()
