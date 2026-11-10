import pandas as pd
import numpy as np

# 1. Performance Summary
df = pd.read_csv("data/backtest_results/combined_backtest_results.csv")
df['is_win'] = df['R_Multiple'] > 0
total_trades = len(df)
win_rate = df['is_win'].mean() * 100
net_pnl = df['P&L_INR'].sum()
net_pnl_pct = (net_pnl / 1000000) * 100
avg_r = df['R_Multiple'].mean()

# Profit Factor
gross_profit = df[df['R_Multiple'] > 0]['P&L_INR'].sum()
gross_loss = abs(df[df['R_Multiple'] <= 0]['P&L_INR'].sum())
profit_factor = gross_profit / (gross_loss if gross_loss > 0 else 1)

# Max Drawdown
df['cum_pnl'] = df['P&L_INR'].cumsum()
cum_pnl = df['cum_pnl'] + 1000000
peak = cum_pnl.cummax()
drawdown = peak - cum_pnl
max_drawdown = drawdown.max()

print("=== 6M BACKTEST RESULTS ===")
print(f"Total trades         : {total_trades}")
print(f"Win rate             : {win_rate:.1f}%")
print(f"Net PnL              : ₹ {net_pnl:.2f}  ({net_pnl_pct:.1f} %)")
print(f"Max drawdown         : ₹ {max_drawdown:.2f}")
print(f"Profit factor        : {profit_factor:.2f}")
print(f"Avg trade R          : {avg_r:.3f}")

# 2. Per Strategy
print("\n=== PER-STRATEGY ===")
def get_strat_stats(x):
    wins = x[x['R_Multiple'] > 0]
    gp = wins['P&L_INR'].sum()
    gl = abs(x[x['R_Multiple'] <= 0]['P&L_INR'].sum())
    pf = gp / (gl if gl > 0 else 1)
    return pd.Series({
        'trades': len(x),
        'win_rate': f"{x['is_win'].mean()*100:.1f}%",
        'net_pnl': f"₹ {x['P&L_INR'].sum():.0f}",
        'profit_factor': round(pf, 2)
    })

strat_stats = df.groupby('Strategy').apply(get_strat_stats)
print(strat_stats)

# 3. May 5 Only
print("\n=== MAY 5 ONLY ===")
df['Date'] = pd.to_datetime(df['Date'])
may5 = df[df['Date'].dt.date == pd.to_datetime('2025-05-05').date()]
if not may5.empty:
    m5_trades = len(may5)
    m5_pnl = may5['P&L_INR'].sum()
    m5_wr = may5['is_win'].mean() * 100
    m5_avg_r = may5['R_Multiple'].mean()
    print(f"Trades / Net PnL / WR / Avg R: {m5_trades} / ₹ {m5_pnl:.0f} / {m5_wr:.1f}% / {m5_avg_r:.2f}")
else:
    print("No trades triggered on May 5 in this sample.")

# 4. Regime Distribution
print("\n=== REGIME DISTRIBUTION (% of bars) ===")
# To get regime distribution, we need to run ContextDetector over all bars
from modules.cached_data_loader import CachedDataLoader
from modules.context_detector import ContextDetector
import warnings
warnings.filterwarnings("ignore")

loader = CachedDataLoader()
detector = ContextDetector()
symbols = loader.get_available_symbols(interval="5m")[:10] # Sample 10 symbols for speed
regimes = []

for sym in symbols:
    df_sym = loader.load(sym, interval="5m")
    if df_sym is None or len(df_sym) < 100: continue
    # Process a subset of bars for speed
    for i in range(100, len(df_sym), 50):
        ctx = detector.detect(df_sym.iloc[:i+1], 15.0)
        regimes.append(ctx.regime)

regime_counts = pd.Series(regimes).value_counts(normalize=True) * 100
regime_order = ['TRENDING_UP', 'TRENDING_DOWN', 'RANGING', 'BREAKOUT_SETUP', 'LOW_VOL', 'HIGH_VOL', 'CHOPPY', 'VOLATILE']
for r in regime_order:
    val = regime_counts.get(r, 0)
    print(f"{r:15}: {val:.1f}%")
