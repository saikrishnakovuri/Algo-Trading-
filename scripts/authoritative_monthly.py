import pandas as pd
import sys
import os
sys.path.insert(0, '.')

from scripts.fast_backtest import load_data, resample_5m, simulate_trade
from modules.strategy_selector import MasterStrategySelector

def run_authoritative_monthly():
    master = MasterStrategySelector()
    symbols = ["NIFTY", "BANKNIFTY", "RELIANCE"]
    trade_log = []
    
    print("Running authoritative monthly breakdown (Post-Phase 18)...")
    
    for symbol in symbols:
        df_full = load_data(symbol)
        if df_full is None: continue
        
        df_5m = resample_5m(df_full)
        df_5m["atr"] = (df_5m["High"] - df_5m["Low"]).rolling(14).mean()
        
        i = 50
        while i < len(df_5m):
            sub_df = df_5m.iloc[:i+1]
            now = sub_df.index[-1]
            risk_pct = 0.02 if symbol in ["NIFTY", "BANKNIFTY"] else 0.01
            risk_amt = 1000000.0 * risk_pct
            
            signal = master.select_best_signal(sub_df, symbol, 14.0, current_time=now)
            
            if signal:
                trade = simulate_trade(df_5m.iloc[i], df_5m.iloc[i:], risk_amt, signal, symbol)
                trade['month'] = now.strftime('%Y-%m')
                trade_log.append(trade)
                i += trade['exit_idx'] + 1
            else:
                i += 1
                
    df_trades = pd.DataFrame(trade_log)
    monthly = df_trades.groupby('month')['net_pnl'].sum()
    total = df_trades['net_pnl'].sum()
    no_march = df_trades[df_trades['month'] != '2026-03']['net_pnl'].sum()
    
    print("\n=== PER-MONTH P&L BREAKDOWN (POST-PHASE 18) ===")
    print(monthly.map('INR {:,.0f}'.format))
    print("-" * 40)
    print(f"TOTAL P&L:       INR {total:,.0f}")
    print(f"EXCLUDING MARCH: INR {no_march:,.0f}")
    
    # Calculate % dependency
    march_pnl = monthly.get('2026-03', 0)
    dependency = (march_pnl / total * 100) if total > 0 else 0
    print(f"March Dependency: {dependency:.1f}%")

if __name__ == "__main__":
    run_authoritative_monthly()
