import pandas as pd
from datetime import datetime

# Load recent data
df = pd.read_csv('data/nifty50_5m.csv')
df.columns = [c.lower() for c in df.columns]
print(f"Loaded {len(df)} rows of NIFTY data.")

# Add simple strategy logic (e.g., EMA crossover)
df['ema20'] = df['close'].ewm(span=20).mean()
df['ema50'] = df['close'].ewm(span=50).mean()

# Buy when 20 > 50, Sell when 20 < 50
df['signal'] = 0
df.loc[df['ema20'] > df['ema50'], 'signal'] = 1
df.loc[df['ema20'] < df['ema50'], 'signal'] = -1

# Calculate P&L
df['pnl'] = df['signal'].shift(1) * (df['close'] - df['close'].shift(1))
cumulative_pnl = df['pnl'].cumsum().iloc[-1]

print(f"Cumulative P&L: {cumulative_pnl}")
print("Strategy: EMA Crossover (20/50)")
