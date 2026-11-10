import shutil
import os
import pandas as pd
import json

# Define Nifty 50 constituents (as of early 2026 for reference)
NIFTY_50 = {
    "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJAJFINSV", "BAJFINANCE",
    "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT",
    "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK",
    "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", "M&M", "MARUTI", "NESTLEIND",
    "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS",
    "TATASTEEL", "TCS", "TECHM", "TITAN", "ULTRACEMCO", "UPL", "WIPRO"
}

SOURCE_DIR = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\angel_historical\Test_months_1min_data"
TARGET_DIR = r"C:\Users\91810\OneDrive\Desktop\AlgoTrading Options\data\nifty50_2024"

# Metadata for record
metadata = {}

for filename in os.listdir(SOURCE_DIR):
    # Match files like "ADANIENT_minute.csv"
    stock_name = filename.split('_')[0]
    if stock_name in NIFTY_50:
        src = os.path.join(SOURCE_DIR, filename)
        dst = os.path.join(TARGET_DIR, filename)
        
        # Read a chunk to get date range
        df = pd.read_csv(src, nrows=10) # check start
        # Assume standard timestamp column
        if 'date' in df.columns:
             start_date = df['date'].iloc[0]
             # Get end date
             df_tail = pd.read_csv(src)
             end_date = df_tail['date'].iloc[-1]
             metadata[stock_name] = {"start": start_date, "end": end_date}
        
        shutil.copy2(src, dst)
        print(f"✅ Moved {stock_name}")

with open(os.path.join(TARGET_DIR, "data_range_metadata.json"), "w") as f:
    json.dump(metadata, f, indent=4)
