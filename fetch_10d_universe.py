import json
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from modules.broker_layer import AngelOneBroker

def fetch_10d_data():
    DATA_DIR = "data/universe_10d"
    os.makedirs(DATA_DIR, exist_ok=True)
    
    print("="*60)
    print("   MASSIVE DATA RETRIEVAL: 1000 STOCKS x 10 SESSIONS")
    print("="*60)
    
    broker = AngelOneBroker()
    if not broker.login(): return

    with open("broker_tokens_full.json", "r") as f:
        token_map = json.load(f)

    # Dates: Last 14 calendar days should cover 10 trading sessions
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    
    start_str = start_date.strftime('%Y-%m-%d 09:15')
    end_str = end_date.strftime('%Y-%m-%d 15:30')
    
    print(f"Time Range: {start_str} to {end_str}")
    
    total = len(token_map)
    processed = 0
    success_count = 0

    # To avoid memory issues with 3.7M rows, we save symbols INDIVIDUALLY to CSV.
    # This is much faster and more reliable than a single giant Excel file.
    
    for symbol_eq, token in token_map.items():
        processed += 1
        symbol = symbol_eq.replace("-EQ", "")
        csv_path = os.path.join(DATA_DIR, f"{symbol}.csv")
        
        # Skip if already exists (resume capability)
        if os.path.exists(csv_path):
            success_count += 1
            continue

        try:
            df = broker.get_historical_data(symbol_eq, token, interval="ONE_MINUTE", from_date_str=start_str, to_date_str=end_str)
            if df is not None and not df.empty:
                df.index = df.index.tz_localize(None)
                df.to_csv(csv_path)
                success_count += 1
            
            if processed % 50 == 0:
                print(f"Progress: {processed}/{total} symbols. Successfully saved: {success_count}")
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")

    print("\n" + "="*60)
    print(f"FETCH COMPLETE: {success_count} symbols saved to {DATA_DIR}")
    print("="*60)

if __name__ == "__main__":
    fetch_10d_data()
