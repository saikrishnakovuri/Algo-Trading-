import os
import json
import time
import pandas as pd
from datetime import datetime, timedelta
from modules.broker_layer import AngelOneBroker

def fetch_max_data():
    broker = AngelOneBroker()
    if not broker.login():
        print("Login failed.")
        return

    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)

    stocks = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "TCS", "SBIN", 
        "BAJFINANCE", "KOTAKBANK", "AXISBANK", "MARUTI", "INFY"
    ]
    
    # Nifty tokens (if available) - we'll skip if not in token_map
    
    timeframes = {
        "ONE_MINUTE": ("1m", 30, 90),
        "FIVE_MINUTE": ("5m", 90, 180),
        "FIFTEEN_MINUTE": ("15m", 180, 730),
        "ONE_DAY": ("daily", 1000, 2000)
    }

    os.makedirs("data/extended", exist_ok=True)
    inventory = []

    for sym in stocks:
        token = token_map.get(f"{sym}-EQ")
        if not token: 
            print(f"Token not found for {sym}")
            continue
        
        for tf_name, (tf_ext, chunk_days, max_days) in timeframes.items():
            print(f"Fetching max {tf_ext} for {sym}...")
            all_data = []
            current_end = datetime.now()
            
            while (datetime.now() - current_end).days < max_days:
                from_date = current_end - timedelta(days=chunk_days)
                
                try:
                    params = {
                        "exchange": "NSE",
                        "symboltoken": token,
                        "interval": tf_name,
                        "fromdate": from_date.strftime('%Y-%m-%d %H:%M'),
                        "todate": current_end.strftime('%Y-%m-%d %H:%M')
                    }
                    response = broker.smart_api.getCandleData(params)
                    if response and response.get('status') and response.get('data') and len(response['data']) > 0:
                        df_chunk = pd.DataFrame(response['data'], columns=['Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
                        all_data.append(df_chunk)
                    else:
                        # Limit reached or empty data
                        break
                except Exception as e:
                    print(f"Error fetching {tf_name} for {sym}: {e}")
                    break
                    
                current_end = from_date
                time.sleep(0.4)
                
            if all_data:
                df_full = pd.concat(all_data).drop_duplicates(subset=['Timestamp']).sort_values('Timestamp')
                df_full.to_csv(f"data/extended/{sym}_{tf_ext}.csv", index=False)
                inventory.append({
                    "Symbol": sym,
                    "Timeframe": tf_ext,
                    "Count": len(df_full),
                    "Start": df_full['Timestamp'].iloc[0],
                    "End": df_full['Timestamp'].iloc[-1]
                })

    df_inv = pd.DataFrame(inventory)
    df_inv.to_csv("data/extended/inventory.csv", index=False)
    
    # Save a readable summary
    summary = "\nEXTENDED DATA INVENTORY\n═══════════════════════\n"
    summary += df_inv.to_string()
    with open("recovery_results.md", "a", encoding="utf-8") as f:
        f.write("\n\n=== PART 1.2: MAXIMUM DATA INGESTION ===\n")
        f.write(summary)
        
    print("Done fetching.")
    print(summary)

if __name__ == '__main__':
    fetch_max_data()
