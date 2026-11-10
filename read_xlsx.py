import pandas as pd
try:
    df = pd.read_excel('backtest_report_20260422_162637.xlsx')
    print(df)
except Exception as e:
    print(f"Error: {e}")
