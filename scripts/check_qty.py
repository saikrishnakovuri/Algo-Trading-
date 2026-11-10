import pandas as pd
from scripts.main_backtest import run_backtest

t = run_backtest()
df = pd.DataFrame(t)
print(f"Avg Qty: {df['qty'].mean():.0f}")
print(f"Max Qty: {df['qty'].max():.0f}")
print(f"Avg PnL: {df['PnL'].mean():,.0f}")
print(df[['PnL', 'qty']].head(10).to_string())
