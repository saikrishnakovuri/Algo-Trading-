import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from modules.broker_layer import AngelOneBroker

def fetch_batched_data(broker, symbol, token, interval, total_days):
    full_df = pd.DataFrame()
    end_date = datetime.now()
    
    # Angel One limit for 1m is 30 days
    batch_size = 30 if interval == "ONE_MINUTE" else 60
    
    current_end = end_date
    days_fetched = 0
    
    while days_fetched < total_days:
        current_start = current_end - timedelta(days=batch_size)
        from_str = current_start.strftime('%Y-%m-%d %H:%M')
        to_str = current_end.strftime('%Y-%m-%d %H:%M')
        
        print(f"  Fetching {symbol} batch: {from_str} to {to_str}")
        df = broker.get_historical_data(symbol, token, interval=interval, from_date_str=from_str, to_date_str=to_str)
        
        if df is not None and not df.empty:
            full_df = pd.concat([df, full_df])
            # Remove duplicates at overlaps
            full_df = full_df[~full_df.index.duplicated(keep='first')]
        else:
            print(f"  No more data or error for {symbol} at {from_str}")
            break
            
        current_end = current_start - timedelta(minutes=1)
        days_fetched += batch_size
        time.sleep(0.5) # Rate limit safety
        
    return full_df.sort_index()

def main():
    print("=== EXECUTING PART 1 of 11 ===")
    start_time = datetime.now()
    print(f"Start Timestamp: {start_time}")
    
    broker = AngelOneBroker()
    if not broker.login():
        print("FATAL: Login failed")
        return

    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    stocks = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "ITC", "SBIN", "BHARTIARTL",
        "BAJFINANCE", "LT", "KOTAKBANK", "AXISBANK", "MARUTI", "TATAMOTORS", "WIPRO",
        "HCLTECH", "SUNPHARMA", "POWERGRID", "NTPC", "ULTRACEMCO", "TITAN", "ASIANPAINT",
        "ADANIPORTS", "HINDALCO", "JSWSTEEL"
    ]
    
    indices = {
        "Nifty 50": "99926000",
        "Nifty Bank": "99926009",
        "India VIX": "99926017"
    }

    data_dir = "data/angel_historical"
    os.makedirs(data_dir, exist_ok=True)
    
    inventory = []
    skipped = []
    
    # 1. Fetch Stocks (1m)
    for s in stocks:
        symbol_eq = s + "-EQ"
        token = token_map.get(symbol_eq)
        if not token:
            print(f"⚠️ Token for {symbol_eq} not found. Skipping.")
            skipped.append(s)
            continue
            
        print(f"Processing {s}...")
        df = fetch_batched_data(broker, s, token, "ONE_MINUTE", 180)
        
        if not df.empty:
            path = os.path.join(data_dir, f"{s}_1m.csv")
            df.to_csv(path)
            stats = {
                "symbol": s,
                "start": df.index.min().strftime('%Y-%m-%d'),
                "end": df.index.max().strftime('%Y-%m-%d'),
                "rows": len(df),
                "sessions": len(df.index.normalize().unique())
            }
            inventory.append(stats)
            print(f"✅ Saved {s}: {stats['rows']} rows, {stats['sessions']} sessions")
        else:
            print(f"❌ Failed to fetch data for {s}")
            skipped.append(s)

    # 2. Fetch Indices
    for name, token in indices.items():
        print(f"Processing Index {name}...")
        # Index intraday might have different limits, try 180 days 5m
        fname = name.replace(" ", "").lower()
        df_5m = fetch_batched_data(broker, name, token, "FIVE_MINUTE", 180)
        if not df_5m.empty:
            df_5m.to_csv(os.path.join("data", f"{fname}_5m.csv"))
            print(f"✅ Saved {name} 5m")
            
        # Daily
        df_daily = broker.get_historical_data(name, token, interval="ONE_DAY", days=365)
        if df_daily is not None and not df_daily.empty:
            df_daily.to_csv(os.path.join("data", f"{fname}_daily.csv"))
            print(f"✅ Saved {name} daily")

    # Final Report
    end_time = datetime.now()
    report = f"\n=== PART 1 COMPLETE — RESULTS LOGGED ===\n"
    report += f"End Timestamp: {end_time}\n"
    report += f"Duration: {end_time - start_time}\n\n"
    report += "### Data Inventory\n"
    for item in inventory:
        report += f"- {item['symbol']}: {item['start']} to {item['end']}, {item['sessions']} sessions, {item['rows']} rows\n"
    
    report += f"\nTotal symbols fetched: {len(inventory)}\n"
    report += f"Skipped: {', '.join(skipped)}\n"
    
    # Verification
    valid_count = sum(1 for item in inventory if item['sessions'] >= 40)
    if valid_count < 15:
        report += f"\n⚠️ WARNING: Only {valid_count} symbols have 40+ sessions. Requirements not fully met.\n"
    else:
        report += f"\n✅ VERIFICATION PASSED: {valid_count} symbols have 40+ sessions.\n"

    with open("optimization_results.md", "a") as f:
        f.write(report)
    
    print(report)

if __name__ == "__main__":
    main()
