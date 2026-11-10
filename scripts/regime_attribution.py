import pandas as pd
import sys
import numpy as np

# Load 6M trade log
trades = pd.read_csv('data/backtest_results/6month_trades_20260508.csv')
trades['timestamp'] = pd.to_datetime(trades['timestamp'])
trades['date'] = trades['timestamp'].dt.date
trades['month'] = trades['timestamp'].dt.to_period('M')
trades['win'] = (trades['net_pnl'] > 0).astype(int)

# Required columns exist: date, symbol, strategy, regime, direction, net_pnl, win

print("=== REGIME × MONTH PnL HEATMAP ===")
piv = trades.pivot_table(index='regime', columns='month', values='net_pnl', aggfunc='sum').fillna(0).round(0)
print(piv)

print("\n=== REGIME 6M SUMMARY ===")
agg = trades.groupby('regime').agg(
    trades=('net_pnl','count'),
    wins=('win','sum'),
    pnl_total=('net_pnl','sum'),
    pnl_avg=('net_pnl','mean'),
).round(2)
agg['wr_pct'] = (agg['wins']/agg['trades']*100).round(1)
# Profit Factor calculation
def calc_pf(g):
    wins = g[g['net_pnl']>0]['net_pnl'].sum()
    losses = abs(g[g['net_pnl']<0]['net_pnl'].sum())
    return wins/losses if losses > 0 else float('inf')

agg['pf'] = trades.groupby('regime').apply(calc_pf).round(2)
print(agg[['trades', 'pnl_total', 'wr_pct', 'pf']])

print("\n=== STRATEGY × REGIME PnL ===")
sr = trades.pivot_table(index='strategy', columns='regime', values='net_pnl', aggfunc='sum').fillna(0).round(0)
print(sr)

print("\n=== STRATEGY × REGIME TRADE COUNT ===")
sr_n = trades.pivot_table(index='strategy', columns='regime', values='net_pnl', aggfunc='count').fillna(0).astype(int)
print(sr_n)

print("\n=== EX-MARCH REGIME SUMMARY ===")
ex = trades[trades['month'] != pd.Period('2026-03', 'M')]
agg_ex = ex.groupby('regime').agg(
    trades=('net_pnl','count'),
    pnl_total=('net_pnl','sum'),
).round(0)
agg_ex['wr_pct'] = (ex.groupby('regime')['win'].mean()*100).round(1)
print(agg_ex)
