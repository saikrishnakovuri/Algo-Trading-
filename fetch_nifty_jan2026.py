import os
import json
import pandas as pd
from modules.broker_layer import AngelOneBroker

def fetch_nifty_jan2026():
    print("📡 Fetching Nifty Index data for Jan 2026...")
    broker = AngelOneBroker()
    if not broker.login():
        print("❌ Login failed.")
        return

    # Use the token for "Nifty 50" identified as "99926000"
    symbol_token = "99926000"
    
    # Angel historical data range for Nifty Index
    start_date = "2026-01-01 09:15"
    end_date = "2026-01-31 15:30"
    
    df = broker.get_historical_data(
        "NIFTY", 
        symbol_token, 
        interval="ONE_MINUTE", 
        from_date_str=start_date, 
        to_date_str=end_date,
        exchange="NSE"
    )
    
    # Debugging the response if empty
    if df is not None and not df.empty:
        os.makedirs("data/nifty_index", exist_ok=True)
        file_path = "data/nifty_index/NIFTY_Jan2026.csv"
        df.to_csv(file_path)
        print(f"✅ Saved Nifty data for Jan 2026 with {len(df)} candles to {file_path}")
    elif df is None:
        print("❌ broker.get_historical_data returned None.")
    elif df.empty:
        print("❌ broker.get_historical_data returned empty DataFrame.")

if __name__ == "__main__":
    fetch_nifty_jan2026()
