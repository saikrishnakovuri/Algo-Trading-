import pandas as pd
from scripts.main_backtest import run_v1_repro

t = run_v1_repro()
df = pd.DataFrame(t)
ce = df[df['Direction'] == 'CE']
win_rate = (len(ce[ce["Result"] == "WIN"])/len(ce)*100)
net_pnl = ce["PnL"].sum()

print(f"CE Trades: {len(ce)}")
print(f"CE Win Rate: {win_rate:.1f}%")
print(f"CE Net PnL: ₹{net_pnl:,.0f}")
