import os
import shutil
import glob
import time
from datetime import datetime, timedelta
import pandas as pd
from modules.broker_layer import AngelOneBroker
import json

def setup_cache():
    print("=== STEP 1: SETUP DATA CACHE ===")
    os.makedirs("data/cache", exist_ok=True)
    
    # 1. Copy existing data
    copied = 0
    for src_dir in ["data/extended", "data/angel_historical"]:
        if os.path.exists(src_dir):
            for file_path in glob.glob(f"{src_dir}/*.csv"):
                dest_path = os.path.join("data/cache", os.path.basename(file_path))
                if not os.path.exists(dest_path):
                    shutil.copy2(file_path, dest_path)
                    copied += 1
    
    print(f"Copied {copied} files from existing data folders")
    
    # 2. Check missing symbols
    target_symbols = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "SBIN", 
        "BHARTIARTL", "BAJFINANCE", "LT", "KOTAKBANK", "AXISBANK", "MARUTI", 
        "WIPRO", "HCLTECH", "SUNPHARMA", "POWERGRID", "NTPC", "ULTRACEMCO", 
        "TITAN", "ASIANPAINT", "ADANIPORTS", "HINDALCO", "JSWSTEEL", "TATAMOTORS",
        "BANKBARODA", "PNB", "IDFCFIRSTB", "FEDERALBNK", "INDUSINDBK",
        "TATAPOWER", "ADANIENT", "ZOMATO", "IRCTC", "TRENT", "DELHIVERY", 
        "PAYTM", "POLICYBZR", "NYKAA", "VEDL", "ONGC", "COALINDIA", "BPCL", 
        "IOC", "GAIL", "DIVISLAB", "DRREDDY", "CIPLA", "APOLLOHOSP", "MANKIND"
    ]
    
    timeframes = {
        "1m": ("ONE_MINUTE", 30),
        "5m": ("FIVE_MINUTE", 40),
        "15m": ("FIFTEEN_MINUTE", 60),
        "daily": ("ONE_DAY", 365)
    }

    # Indices skip 1m
    indices = ["NIFTY50", "BANKNIFTY"]
    
    broker = None

    for sym in target_symbols + indices:
        for tf_ext, (tf_api, days) in timeframes.items():
            if sym in indices and tf_ext == "1m":
                continue
                
            file_path = f"data/cache/{sym}_{tf_ext}.csv"
            if os.path.exists(file_path):
                continue
                
            # If we reach here, we need to download. Initialize broker once.
            if broker is None:
                broker = AngelOneBroker()
                if not broker.login():
                    print("Broker login failed. Cannot download missing data.")
                    return
                try:
                    with open("broker_tokens.json", "r") as f:
                        token_map = json.load(f)
                except Exception as e:
                    print("Failed to load broker_tokens.json:", e)
                    return

            token_key = f"{sym}-EQ"
            if sym == "NIFTY50": token_key = "NIFTY 50"
            elif sym == "BANKNIFTY": token_key = "NIFTY BANK"
            
            token = token_map.get(token_key)
            if not token:
                # Try simple symbol name
                token = token_map.get(sym)
            
            if not token:
                print(f"Token not found for {sym}")
                break

            print(f"Downloading {sym} {tf_ext}...")
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            retries = 3
            success = False
            while retries > 0 and not success:
                try:
                    params = {
                        "exchange": "NSE",
                        "symboltoken": token,
                        "interval": tf_api,
                        "fromdate": from_date.strftime('%Y-%m-%d %H:%M'),
                        "todate": to_date.strftime('%Y-%m-%d %H:%M')
                    }
                    response = broker.smart_api.getCandleData(params)
                    if response and response.get('status') and response.get('data'):
                        df = pd.DataFrame(response['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                        df.to_csv(file_path, index=False)
                        success = True
                    else:
                        print(f"  API returned no data for {sym} {tf_ext}")
                        retries -= 1
                        time.sleep(1)
                except Exception as e:
                    print(f"  Error fetching {sym} {tf_ext}: {e}")
                    retries -= 1
                    time.sleep(1)
            
            time.sleep(0.5)

    # Generate inventory
    inventory_file = "data/cache/inventory.txt"
    files = glob.glob("data/cache/*.csv")
    symbols_found = set()
    with open(inventory_file, "w") as f:
        for file in files:
            fname = os.path.basename(file)
            f.write(f"{fname}\n")
            sym = fname.split("_")[0]
            if sym != "inventory":
                symbols_found.add(sym)
                
    print(f"Data cache ready: {len(symbols_found)} symbols, {len(files)} total files")

if __name__ == "__main__":
    setup_cache()