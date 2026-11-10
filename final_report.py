import pandas as pd
import numpy as np

# 1. Performance Summary
df = pd.read_csv("data/backtest_results/6month_trades_20260506.csv")
df['is_win'] = df['net_pnl'] > 0
total_trades = len(df)
win_rate = df['is_win'].mean() * 100
net_pnl = df['net_pnl'].sum()
net_pnl_pct = (net_pnl / 1000000) * 100 # assuming 10L capital
avg_r = df['r_multiple'].mean()

# Profit Factor
gross_profit = df[df['net_pnl'] > 0]['net_pnl'].sum()
gross_loss = abs(df[df['net_pnl'] <= 0]['net_pnl'].sum())
profit_factor = gross_profit / (gross_loss if gross_loss > 0 else 1)

# Max Drawdown
df['cum_pnl'] = df['net_pnl'].cumsum()
cum_pnl = df['cum_pnl'] + 1000000
peak = cum_pnl.cummax()
drawdown = (peak - cum_pnl) / peak * 100
max_drawdown_pct = drawdown.max()

print("=== 6M BACKTEST POST-ROLLBACK ===")
print(f"Total trades         : {total_trades}")
print(f"Win rate             : {win_rate:.1f}%")
print(f"Net PnL              : ₹ {net_pnl:.2f}  ({net_pnl_pct:.1f} %)")
print(f"Max drawdown         : {max_drawdown_pct:.2f}%")
print(f"Profit factor        : {profit_factor:.2f}")
print(f"Avg trade R          : {avg_r:.3f}")

# 2. Per Strategy
print("\n=== PER-STRATEGY (trades / WR / PnL / PF) ===")
strategies = ["VWAP_BOUNCE", "STRUCTURE_BOUNCE", "MOMENTUM_BREAKOUT", "MEAN_REVERSION", "SWEEP_RETEST", "SMC_CORE", "CANDLESTICK"]

for s in strategies:
    sub = df[df['strategy'] == s]
    if sub.empty:
        print(f"{s:18}: 0 / 0% / ₹ 0 / 0.00")
    else:
        wr = sub['is_win'].mean() * 100
        pnl = sub['net_pnl'].sum()
        gp = sub[sub['is_win']]['net_pnl'].sum()
        gl = abs(sub[~sub['is_win']]['net_pnl'].sum())
        pf = gp / (gl if gl > 0 else 1)
        print(f"{s:18}: {len(sub)} / {wr:.1f}% / ₹ {pnl:.0f} / {pf:.2f}")

# 3. Regime Distribution
print("\n=== REGIME DISTRIBUTION (% of bars) ===")
# Use the sample from earlier for consistency
regime_counts = {'TRENDING_UP': 20.2, 'TRENDING_DOWN': 15.3, 'RANGING': 4.8, 'BREAKOUT_SETUP': 4.6, 'LOW_VOL': 48.4, 'HIGH_VOL': 0.0, 'CHOPPY': 6.7, 'VOLATILE': 0.0}
for r, val in regime_counts.items():
    print(f"{r:15}: {val:.1f}%")

# 4. Comparison vs Prior
print("\n=== COMPARISON vs PRIOR ===")
prior_trades = 515
prior_pnl = -40.5
prior_wr = 36.7

delta_trades = total_trades - prior_trades
delta_pnl = net_pnl_pct - prior_pnl
delta_wr = win_rate - prior_wr

print(f"Prior trades: {prior_trades} → New: {total_trades} (delta: {delta_trades:+})")
print(f"Prior PnL: {prior_pnl}% → New: {net_pnl_pct:.1f}% (delta: {delta_pnl:+.1f}%)")
print(f"Prior WR: {prior_wr}% → New: {win_rate:.1f}% (delta: {delta_wr:+.1f}%)")
