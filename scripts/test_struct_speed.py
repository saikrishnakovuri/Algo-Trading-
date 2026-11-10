import os
import pandas as pd
import time
from datetime import datetime, timedelta
from modules.charting.structure_detector import StructureDetector

def test_speed():
    detector = StructureDetector()
    symbol = "RELIANCE"
    data_path = f"data/angel_historical/{symbol}_1m.csv"
    
    if not os.path.exists(data_path):
        print(f"Data not found for {symbol}")
        return

    df_raw = pd.read_csv(data_path)
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], utc=True).dt.tz_convert('Asia/Kolkata')
    df_raw.set_index('Timestamp', inplace=True)
    
    df = df_raw.resample('5min').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
    df = df.iloc[-500:] # Last 500 bars
    
    print(f"Testing {symbol} with {len(df)} bars...")
    
    start = time.time()
    for _ in range(20):
        # Test detect_all (which uses the new cache and optimized algorithms)
        _ = detector.detect_all(df, symbol)
    end = time.time()
    
    print(f"Total time for 20 calls (with cache): {end - start:.4f}s")
    print(f"Avg time per call: {(end - start)/20:.4f}s")
    
    # Test without cache (different lengths)
    start = time.time()
    for i in range(20):
        _ = detector.detect_all(df.iloc[:-(i+1)], symbol)
    end = time.time()
    print(f"Total time for 20 calls (NO cache, varying length): {end - start:.4f}s")
    print(f"Avg time per call (NO cache): {(end - start)/20:.4f}s")

if __name__ == "__main__":
    test_speed()
