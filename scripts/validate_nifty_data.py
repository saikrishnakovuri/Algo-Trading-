import pandas as pd
import os

def validate_nifty_data():
    file_path = "data/nifty_index/NIFTY_Jan2026.csv"
    print(f"Validating {file_path}...")
    
    if not os.path.exists(file_path):
        print("❌ Error: File not found.")
        return
        
    df = pd.read_csv(file_path)
    
    # 1. Column Check
    expected = ['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    missing = [c for c in expected if c not in df.columns]
    if missing:
        print(f"❌ Missing Columns: {missing}")
    else:
        print("✅ Columns OK.")
        
    # 2. NaN Check
    nans = df.isna().sum().sum()
    if nans > 0:
        print(f"⚠️ Warning: {nans} NaN values found. Filling...")
        df = df.fillna(method='ffill')
    else:
        print("✅ No NaN values.")
        
    # 3. Duplicate Check
    dupes = df.duplicated().sum()
    if dupes > 0:
        print(f"⚠️ Warning: {dupes} duplicate rows found. Removing...")
        df = df.drop_duplicates()
    else:
        print("✅ No duplicate rows.")
        
    # 4. Continuity Check (1m interval)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df = df.sort_values('Timestamp')
    diffs = df['Timestamp'].diff().dropna()
    gaps = diffs[diffs > pd.Timedelta(minutes=1)]
    # Filter out overnight gaps (usually > 1 hour)
    real_gaps = [g for g in gaps if g < pd.Timedelta(hours=1)]
    if real_gaps:
        print(f"⚠️ Warning: {len(real_gaps)} intraday gaps found (missing 1m candles).")
    else:
        print("✅ Data continuity OK (No intraday gaps).")
        
    print(f"✅ Validation Complete. Rows: {len(df)}")

if __name__ == "__main__":
    validate_nifty_data()
