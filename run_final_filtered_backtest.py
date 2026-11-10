import os
import json
import pandas as pd
from datetime import datetime
from backtest_engine import BacktestEngine

def run_filtered_backtest():
    # 3 High-Liquidity Stocks for Depth + Speed
    top_3_symbols = ["RELIANCE", "HDFCBANK", "ICICIBANK"]
    data_dir = "data/angel_historical"
    
    all_files = sorted([os.path.join(data_dir, f"{s}_1m.csv") for s in top_3_symbols if os.path.exists(os.path.join(data_dir, f"{s}_1m.csv"))])

    session_id = f"filtered_final_{datetime.now().strftime('%H%M%S')}"
    journal_file = "trade_journal_filtered.csv"
    
    if os.path.exists(journal_file):
        os.remove(journal_file)
            
    engine = BacktestEngine(initial_capital=1000000.0)
    engine.journal_file = journal_file
    
    print(f"\n🚀 Starting Final Filtered Backtest (3 Stocks, 30 Days)...")
    print(f"Active Strategies: TRAP_REVERSAL (All), ZONE_REJECTION (Banks Only, Score > 7.0)")
    
    trades = engine.run_massive_backtest_v2(all_files)
    
    if trades:
        # Calculate R-multiples for the results
        for t in trades:
            risk = abs(t['entry'] - t['sl'])
            t['r_multiple'] = round(t['pnl'] / (risk * t['qty']), 2) if risk > 0 else 0
            
        df = pd.DataFrame(trades)
        stats = engine.calculate_performance(trades)
        
        print("\n" + "="*50)
        print("📊 FILTERED PERFORMANCE SUMMARY")
        print("="*50)
        
        # Summary Table Logic
        results = []
        for strat in df['setup'].unique():
            sdf = df[df['setup'] == strat]
            wins = sdf[sdf['pnl'] > 0]
            row = {
                "Strategy": strat,
                "Trades": len(sdf),
                "Win%": f"{round(len(wins)/len(sdf)*100, 1)}%",
                "AvgR": round(sdf['r_multiple'].mean(), 2),
                "P&L": round(sdf['pnl'].sum(), 0)
            }
            results.append(row)
        
        print(pd.DataFrame(results).to_string(index=False))
        print("-" * 50)
        print(f"Total Trades: {stats['Total Trades']}")
        print(f"Overall Win Rate: {stats['Win Rate %']}%")
        print(f"Total Profit: {stats['Total Profit']:.2f} INR")
        print(f"Max Drawdown: {stats['Max Drawdown']:.2f} INR")
        
        # Save results
        with open("data/backtest_results_filtered.json", "w") as f:
            json.dump(stats, f)
            
    print("\n✅ FINAL BACKTEST COMPLETE.")

if __name__ == "__main__":
    run_filtered_backtest()
