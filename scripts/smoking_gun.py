import pandas as pd
import numpy as np
from scripts.main_backtest import run_v2_honest

# 1. Load V1 Winners (Proven baseline)
v1w = pd.read_excel("winning09052026.xlsx", engine='openpyxl')
v1w['Entry_Time'] = pd.to_datetime(v1w['Entry_Time'])

# 2. Run current V2 logic
t = run_v2_honest()
v2 = pd.DataFrame(t)
v2['Entry_Time'] = pd.to_datetime(v2['Entry_Time'])

# 3. Compare
merged = v2.merge(v1w[['Entry_Time', 'Result']], on="Entry_Time", suffixes=('_V2', '_V1'))
print(f"V1 Winners present in V2: {len(merged)}")
print("V2 Result distribution for these V1 winners:")
print(merged['Result_V2'].value_counts())

# Inspect one divergence
if len(merged[merged['Result_V2'] == 'LOSS']) > 0:
    div = merged[merged['Result_V2'] == 'LOSS'].iloc[0]
    print(f"\nDivergence at {div['Entry_Time']}:")
    print(f"V1 Result: WIN | V2 Result: LOSS")
