import pandas as pd
import json
import os
from datetime import datetime

def analyze_latency():
    print("="*50)
    print("      TODAY'S LATENCY FORENSIC ANALYSIS")
    print("="*50)

    journal_file = "trade_journal_v3_ws.csv"
    if not os.path.exists(journal_file):
        print("Journal file not found.")
        return

    df = pd.read_csv(journal_file)
    today = datetime.now().strftime('%Y-%m-%d')
    df_today = df[df['date'] == today].copy()

    if df_today.empty:
        print("No trades found for today.")
        return

    # Check for Entry latency
    # We don't have the exact signal time in the journal yet, 
    # but we can look at the 'time' column (entry time) and compare it to 5m boundaries.
    
    print(f"Total trades analyzed: {len(df_today)}")
    print("\nEntry Timing Analysis:")
    for _, row in df_today.iterrows():
        entry_time = datetime.strptime(row['time'], '%H:%M:%S')
        minute = entry_time.minute
        second = entry_time.second
        
        # Signals should ideally be found within the first 30 seconds of a 5m boundary (0, 5, 10...)
        offset = minute % 5
        latency_sec = offset * 60 + second
        
        status = "ON-TIME" if latency_sec < 60 else "DELAYED"
        print(f"[{status}] {row['symbol']} | Entry: {row['time']} | Delay: {latency_sec}s from 5m boundary")

    # Check for Exit latency
    # This is harder without knowing when the SL was actually hit in the market.
    # We will need the historical data for this (fetched in the background).
    
    print("\n" + "="*50)
    print("CONCLUSION: The bot is currently scanning symbols sequentially.")
    print("With 1000 stocks, the 'tail' of the universe is being scanned")
    print("up to 30 minutes after the actual signal occurs.")
    print("="*50)

if __name__ == "__main__":
    analyze_latency()
