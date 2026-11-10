import pandas as pd
import os
import glob

files = glob.glob('backtest_report_*.xlsx')
if not files:
    print("No reports found.")
else:
    latest_file = max(files, key=os.path.getmtime)
    print(f"Converting {latest_file} to CSV...")
    try:
        df = pd.read_excel(latest_file, engine='openpyxl')
        csv_name = latest_file.replace('.xlsx', '.csv')
        df.to_csv(csv_name, index=False)
        print(f"Created {csv_name}")
        print(df)
    except Exception as e:
        print(f"Error: {e}")
