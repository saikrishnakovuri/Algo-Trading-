import json
import pandas as pd
import os
import time
from datetime import datetime, timedelta
from modules.broker_layer import AngelOneBroker

def fetch_all_data():
    print("Initializing Data Retrieval for 1000 Stocks (V2 - Timezone Fix)...")
    broker = AngelOneBroker()
    if not broker.login(): return

    with open("broker_tokens_full.json", "r") as f:
        token_map = json.load(f)

    today_str = datetime.now().strftime('%Y-%m-%d')
    start_date = f"{today_str} 09:15"
    end_date = f"{today_str} 15:30"
    
    all_data = []
    total = len(token_map)
    processed = 0

    for symbol_eq, token in token_map.items():
        processed += 1
        symbol = symbol_eq.replace("-EQ", "")
        try:
            df = broker.get_historical_data(symbol_eq, token, interval="ONE_MINUTE", from_date_str=start_date, to_date_str=end_date)
            if df is not None and not df.empty:
                # REMOVE TIMEZONE
                df.index = df.index.tz_localize(None)
                df['Symbol'] = symbol
                df['Token'] = token
                all_data.append(df)
            if processed % 100 == 0: print(f"Progress: {processed}/{total}...")
        except Exception as e: print(f"Error fetching {symbol}: {e}")

    if all_data:
        print("Consolidating...")
        final_df = pd.concat(all_data).reset_index()
        output_file = f"market_data_1k_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        print(f"Saving to {output_file}...")
        final_df.to_excel(output_file, index=False)
        print(f"Done. Saved {len(final_df)} rows.")
    broker.logout()

if __name__ == "__main__":
    fetch_all_data()
