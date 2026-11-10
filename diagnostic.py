import pandas as pd
import numpy as np

try:
    wins = pd.read_excel('v2/winning_v2.xlsx', engine='openpyxl')
    losses = pd.read_excel('v2/loosing_v2.xlsx', engine='openpyxl')
    df = pd.concat([wins, losses])
except Exception as e:
    print(f"Error loading files: {e}")
    exit()

df['Entry_Time'] = pd.to_datetime(df['Entry_Time'])

print("\n=== 1. SL/TP DISTANCE SANITY (must be: |Target-Entry| > |SL-Entry|) ===")
df['tp_dist'] = (df['Target_T1'] - df['Entry_Price']).abs()
df['sl_dist'] = (df['StopLoss']  - df['Entry_Price']).abs()
df['rr_ratio'] = df['tp_dist'] / df['sl_dist']
print(df[['Direction','Entry_Price','Target_T1','StopLoss','tp_dist','sl_dist','rr_ratio']].head(10).to_string())
print(f"\nMedian R:R ratio: {df['rr_ratio'].median():.2f}  (must be ~2.0 if tp_atr=1.2 and sl_atr=0.6)")

print("\n=== 2. DIRECTION vs PRICE OUTCOME (proves entry logic correctness) ===")
# For CE: target should be above entry (long), SL below
ce = df[df['Direction']=='CE']
ce_target_above = (ce['Target_T1'] > ce['Entry_Price']).sum()
ce_sl_below     = (ce['StopLoss']  < ce['Entry_Price']).sum()
print(f"CE trades total: {len(ce)}")
print(f"CE target ABOVE entry: {ce_target_above} (must equal {len(ce)})")
print(f"CE SL BELOW entry    : {ce_sl_below}     (must equal {len(ce)})")

if ce_target_above != len(ce) or ce_sl_below != len(ce):
    print("🔴 BUG FOUND: CE direction is inverted somewhere!")
else:
    print("✅ CE Direction logic is technically sound.")

print("\n=== 3. WIN/LOSS by entry quality (price action after entry) ===")
# Note: direction is always CE in verified V2
df['exit_pnl_sign'] = (df['Exit_Price'] - df['Entry_Price'])
print(df.groupby('Result')['exit_pnl_sign'].describe())

print("\n=== 4. LOSS REASON DISTRIBUTION ===")
v_losses = df[df['Result']=='LOSS']
print(v_losses['Reason'].value_counts())
print(f"\nFAKEOUT %: {(v_losses['Reason']=='FAKEOUT').sum() / len(v_losses) * 100:.1f}%")
print("If FAKEOUT > 60% → volume filter is likely INVERTED (passing only low-vol retests)")
