import os
import json
import time
import pandas as pd
from modules.broker_layer import AngelOneBroker

def fetch_indices():
    print("📡 Initializing Angel One Index Data Fetch...")
    broker = AngelOneBroker()
    if not broker.login():
        print("❌ Login failed.")
        return

    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    # Use names as mapped in fetch_broker_tokens.py
    targets = {
        "Nifty 50": "nifty50_5m.csv",
        "Nifty Bank": "banknifty_5m.csv",
        "INDIA VIX": "india_vix_5m.csv"
    }

    os.makedirs("data", exist_ok=True)
    
    for name, filename in targets.items():
        token = token_map.get(name)
        if not token:
            print(f"⚠️ Token for {name} not found.")
            continue
            
        print(f"Fetching 30 days of 5m data for {name}...")
        df = broker.get_historical_data(name, token, interval="FIVE_MINUTE", days=30)
        
        if df is not None and not df.empty:
            file_path = os.path.join("data", filename)
            df.to_csv(file_path)
            print(f"✅ Saved {name} to {file_path} ({len(df)} bars).")
        else:
            print(f"❌ Failed to fetch data for {name}")
        
        time.sleep(1.0)

if __name__ == "__main__":
    fetch_indices()
