import os
import pandas as pd
from backtest_engine import BacktestEngine

def fast_backtest():
    initial_capital = 500000.0
    file_path = "data/nifty_index/NIFTY_Jan2026.csv"
    
    print(f"🚀 Running Fast Baseline Backtest for NIFTY Jan 2026...")
    
    engine = BacktestEngine(initial_capital=initial_capital)
    
    # Run for the full month of January
    trades = engine.run_massive_backtest_v2(
        files=[file_path],
        start_date="2026-01-01",
        end_date="2026-01-31"
    )
    
    if not trades:
        print("❌ No trades were triggered in the baseline run.")
        return
        
    print(f"✅ Fast Backtest Complete. Total Trades: {len(trades)}")
    
    df_trades = pd.DataFrame(trades)
    total_pnl = df_trades['pnl'].sum()
    win_rate = (df_trades['PnL'] > 0).mean() * 100
    
    print(f"--- RESULTS ---")
    print(f"Total P&L: ₹{total_pnl:,.2f}")
    print(f"Win Rate:  {win_rate:.1f}%")
    print(f"Max P&L:   ₹{df_trades['pnl'].max():,.2f}")
    print(f"Min P&L:   ₹{df_trades['pnl'].min():,.2f}")

if __name__ == "__main__":
    fast_backtest()
