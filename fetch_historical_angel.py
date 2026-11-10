import os
import json
import time
import pandas as pd
from modules.broker_layer import AngelOneBroker

def fetch_history():
    print("📡 Initializing Angel One Historical Data Fetch...")
    broker = AngelOneBroker()
    if not broker.login():
        print("❌ Login failed. Check your .env credentials.")
        return

    if not os.path.exists("broker_tokens.json"):
        print("❌ broker_tokens.json missing. Run fetch_broker_tokens.py first.")
        return
        
    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    # Top 25 highly liquid Nifty stocks for robust backtesting
    stocks_to_fetch = [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
        "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE", "BHARTIARTL", "BPCL",
        "BRITANNIA", "CIPLA", "BHARATFORGE", "COFORGE", "MPHASIS",
        "PERSISTENT", "POLYCAB", "GODREJPROP", "AUBANK", "CUMMINSIND",
        "MARICO", "INDUSTOWER", "AUROPHARMA", "ASHOKLEY", "HDFCAMC",
        "FEDERALBNK", "LUPIN"
    ]

    data_dir = "data/angel_historical"
    os.makedirs(data_dir, exist_ok=True)
    
    print(f"🚀 Fetching 30 days of 1m data for {len(stocks_to_fetch)} stocks...")
    
    for sym in stocks_to_fetch:
        token = token_map.get(f"{sym}-EQ")
        if not token:
            print(f"⚠️ Token for {sym}-EQ not found.")
            continue
            
        print(f"Fetching historical 1m data for {sym}...")
        # Angel One allows up to 30 days for ONE_MINUTE.
        df = broker.get_historical_data(f"{sym}-EQ", token, interval="ONE_MINUTE", days=30)
        
        if df is not None and not df.empty:
            file_path = os.path.join(data_dir, f"{sym}_1m.csv")
            df.to_csv(file_path)
            print(f"✅ Saved {sym} with {len(df)} candles.")
        else:
            print(f"❌ Failed to fetch data for {sym}")
        
        time.sleep(0.6) # Angel One rate limit is 3 requests/sec

if __name__ == "__main__":
    fetch_history()
