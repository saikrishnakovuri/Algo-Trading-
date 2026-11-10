import os
import time
import pandas as pd
from modules.broker_layer import AngelOneBroker
from datetime import datetime, timedelta

def fetch_range():
    print("📡 Initializing Angel One Historical Data Fetch (Jan 2025 - Apr 2026)...")
    broker = AngelOneBroker()
    if not broker.login():
        print("❌ Login failed. Check your .env credentials.")
        return

    target = {"symbol": "nifty50", "token": "99926000"}
    data_dir = "data/angel_historical"
    os.makedirs(data_dir, exist_ok=True)
    
    # Angel One allows max 30 days per request for 1m data. 
    # We need ~16 months. Let's fetch in 30-day chunks.
    start_date = datetime(2025, 1, 1, 9, 15)
    end_final = datetime(2026, 4, 30, 15, 30)
    
    all_dfs = []
    current_start = start_date
    
    while current_start < end_final:
        current_end = min(current_start + timedelta(days=29), end_final)
        
        from_str = current_start.strftime('%Y-%m-%d %H:%M')
        to_str = current_end.strftime('%Y-%m-%d %H:%M')
        
        print(f"Fetching {target['symbol']} from {from_str} to {to_str}...")
        
        df = broker.get_historical_data(
            target['symbol'], 
            target['token'], 
            interval="ONE_MINUTE", 
            from_date_str=from_str, 
            to_date_str=to_str
        )
        
        if df is not None and not df.empty:
            all_dfs.append(df)
            print(f"✅ Received {len(df)} candles.")
        else:
            print(f"⚠️ No data for range {from_str} - {to_str}")
        
        current_start = current_end + timedelta(minutes=1)
        time.sleep(1.0) # Rate limit safety

    if all_dfs:
        full_df = pd.concat(all_dfs)
        full_df = full_df[~full_df.index.duplicated(keep='first')]
        full_df.sort_index(inplace=True)
        file_path = os.path.join(data_dir, "nifty50_18m_1m.csv")
        full_df.to_csv(file_path)
        print(f"🏁 Saved COMPLETE NIFTY DATA: {len(full_df)} candles to {file_path}")
    else:
        print("❌ No data fetched at all.")

if __name__ == "__main__":
    fetch_range()
