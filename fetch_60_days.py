import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from modules.broker_layer import AngelOneBroker

def fetch_60_days():
    print("📡 Initializing 60-day Data Fetch...")
    broker = AngelOneBroker()
    if not broker.login():
        print("❌ Login failed.")
        return

    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    stocks = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "SBIN", "BHARTIARTL", "BAJFINANCE", "LT"]
    indices = {"Nifty 50": "nifty50_1m.csv", "Nifty Bank": "banknifty_1m.csv"}
    
    data_dir = "data/angel_historical"
    os.makedirs(data_dir, exist_ok=True)

    # Date ranges
    now = datetime.now()
    batch1_to = now.strftime('%Y-%m-%d %H:%M')
    batch1_from = (now - timedelta(days=30)).strftime('%Y-%m-%d %H:%M')
    
    batch2_to = (now - timedelta(days=30, minutes=1)).strftime('%Y-%m-%d %H:%M')
    batch2_from = (now - timedelta(days=60)).strftime('%Y-%m-%d %H:%M')

    all_targets = []
    for s in stocks:
        all_targets.append((s + "-EQ", f"{s}_1m.csv"))
    for name, filename in indices.items():
        all_targets.append((name, filename))

    for symbol, filename in all_targets:
        token = token_map.get(symbol)
        if not token:
            print(f"⚠️ Token for {symbol} not found.")
            continue

        print(f"Fetching 60 days for {symbol}...")
        
        # Batch 1 (Recent 30 days)
        df1 = broker.get_historical_data(symbol, token, interval="ONE_MINUTE", from_date_str=batch1_from, to_date_str=batch1_to)
        time.sleep(0.5)
        
        # Batch 2 (Previous 30 days)
        df2 = broker.get_historical_data(symbol, token, interval="ONE_MINUTE", from_date_str=batch2_from, to_date_str=batch2_to)
        
        if df1 is not None and df2 is not None:
            full_df = pd.concat([df2, df1]).sort_index()
            # Drop duplicates if any at the boundary
            full_df = full_df[~full_df.index.duplicated(keep='first')]
            
            file_path = os.path.join(data_dir, filename)
            full_df.to_csv(file_path)
            print(f"✅ Saved {symbol} to {file_path} ({len(full_df)} candles).")
        elif df1 is not None:
            file_path = os.path.join(data_dir, filename)
            df1.to_csv(file_path)
            print(f"⚠️ Only Batch 1 available for {symbol}. Saved {len(df1)} candles.")
        else:
            print(f"❌ Failed to fetch any data for {symbol}")
            
        time.sleep(1.0)

if __name__ == "__main__":
    fetch_60_days()
