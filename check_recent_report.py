import pandas as pd
import os
import glob

files = glob.glob('backtest_report_*.xlsx')
if not files:
    print("No reports found.")
else:
    latest_file = max(files, key=os.path.getmtime)
    print(f"Reading {latest_file}...")
    df = pd.read_excel(latest_file)
    print(df)
    if not df.empty:
        print("\nSummary:")
        print(df.groupby('symbol')['pnl'].sum())
