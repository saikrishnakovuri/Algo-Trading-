import pandas as pd
import sys
import numpy as np

# Load 180d optimized trades
trades = pd.read_csv('data/fast_backtest_results/trades_optimized.csv')
trades['timestamp'] = pd.to_datetime(trades['timestamp'])
trades['month'] = trades['timestamp'].dt.to_period('M')
trades['win'] = (trades['net_pnl'] > 0).astype(int)

print("=== MONTHLY PnL (Post-20b) ===")
monthly = trades.groupby('month').agg(
    trades=('net_pnl','count'),
    wr=('win','mean'),
    pnl=('net_pnl','sum')
).round(2)
monthly['wr'] = (monthly['wr']*100).round(1)
print(monthly)

# OOS Oct-Dec Calculation
oos_mask = (trades['timestamp'] >= '2025-10-01') & (trades['timestamp'] < '2026-01-01')
oos = trades[oos_mask]
if not oos.empty:
    wins = oos[oos['net_pnl'] > 0]['net_pnl'].sum()
    losses = abs(oos[oos['net_pnl'] < 0]['net_pnl'].sum())
    pf = wins / losses if losses > 0 else float('inf')
    print(f"\nOOS Oct-Dec PF: {pf:.2f}")
    print(f"OOS Oct-Dec Trades: {len(oos)}")
else:
    print("\nOOS Oct-Dec: NO TRADES")

# Ex-March PnL
ex_march = trades[trades['month'] != '2026-03']['net_pnl'].sum()
print(f"Ex-March PnL: ₹{ex_march:,.0f}")

print(f"Total 6M Trades: {len(trades)}")
