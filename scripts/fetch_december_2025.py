import os
import time
import pandas as pd
from modules.broker_layer import AngelOneBroker
from datetime import datetime

def fetch_dec_2025():
    print("📡 Initializing Angel One Historical Data Fetch for Dec 2025...")
    broker = AngelOneBroker()
    if not broker.login():
        print("❌ Login failed. Check your .env credentials.")
        return

    # Tokens for Indices
    targets = [
        {"symbol": "nifty50", "token": "99926000"},
        {"symbol": "banknifty", "token": "99926009"},
        {"symbol": "indiavix", "token": "99926017"}
    ]

    data_dir = "data/angel_historical"
    os.makedirs(data_dir, exist_ok=True)
    
    # Dec 2025 range
    from_date = "2025-12-01 09:15"
    to_date = "2025-12-31 15:30"
    
    for item in targets:
        print(f"Fetching historical 1m data for {item['symbol']} (Dec 2025)...")
        # Trying to fetch 1m data for Dec 2025
        df = broker.get_historical_data(
            item['symbol'], 
            item['token'], 
            interval="ONE_MINUTE", 
            from_date_str=from_date, 
            to_date_str=to_date
        )
        
        if df is not None and not df.empty:
            file_path = os.path.join(data_dir, f"{item['symbol']}_dec2025_1m.csv")
            df.to_csv(file_path)
            print(f"✅ Saved {item['symbol']} with {len(df)} candles.")
        else:
            print(f"❌ Failed to fetch data for {item['symbol']}. It might be outside the broker's retention window.")
        
        time.sleep(1.0)

if __name__ == "__main__":
    fetch_dec_2025()
