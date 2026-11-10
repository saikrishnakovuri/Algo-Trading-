import pandas as pd
import numpy as np

# Load Iteration 3.3 results (current state of main_backtest.py output)
from scripts.main_backtest import run_backtest
t = run_backtest()
df = pd.DataFrame(t)

print("\n=== STEP 3: DIRECTION vs PRICE OUTCOME ===")
ce = df[df["Direction"] == "CE"]
err1 = (ce["Target_T1"] <= ce["Entry_Price"]).sum()
err2 = (ce["StopLoss"]  >= ce["Entry_Price"]).sum()
print(f"CE trades total: {len(ce)}")
print(f"CE trades with Target <= Entry (BUG): {err1} / {len(ce)}")
print(f"CE trades with SL    >= Entry (BUG): {err2} / {len(ce)}")

ce_long_winners = ce[(ce["Result"] == "WIN") & (ce["Exit_Price"] > ce["Entry_Price"])]
ce_long_paradox = ce[(ce["Result"] == "WIN") & (ce["Exit_Price"] <= ce["Entry_Price"])]
print(f"CE wins with price up   (correct): {len(ce_long_winners)}")
print(f"CE wins with price flat/down (BUG): {len(ce_long_paradox)}")

print("\n=== STEP 5: RISK CAP VIOLATIONS ===")
print(f"Min single trade PnL : ₹{df['PnL'].min():,.2f}")
violations = df[df["PnL"] < -5100] # tolerance for brokerage
print(f"Trades that lost MORE than ₹5,000: {len(violations)}")
