import os
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, time
import joblib

def main():
    print("🚀 Precomputing Gap Statistics...")
    
    data_dir = Path("data/nifty200")
    files = list(data_dir.glob("*_1m.csv"))
    print(f"📁 Found {len(files)} files in {data_dir}")
    
    if not files:
        print("⚠️ No data files found. Skipping precompute.")
        return
        
    all_gap_data = []
    
    for f in files[:50]: # Sample 50 stocks for speed in this demo
        symbol = f.name.replace("_1m.csv", "")
        try:
            df = pd.read_csv(f, index_col=0, parse_dates=True)
            if df.empty: continue
            
            # Resample to Daily
            daily = df.resample('D').apply({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'}).dropna()
            if len(daily) < 5: 
                continue
            
            # Calculate ATR Daily
            high_low = daily['High'] - daily['Low']
            high_close = np.abs(daily['High'] - daily['Close'].shift())
            low_close = np.abs(daily['Low'] - daily['Close'].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            daily['ATR'] = tr.rolling(14, min_periods=1).mean()
            
            daily['Prior_Close'] = daily['Close'].shift(1)
            daily = daily.dropna()
            
            for date, row in daily.iterrows():
                gap_val = row['Open'] - row['Prior_Close']
                gap_pct = gap_val / row['Prior_Close'] * 100
                gap_atr = gap_val / row['ATR'] if row['ATR'] > 0 else 0
                
                # Did it fill?
                day_data = df[df.index.normalize() == date]
                if day_data.empty: continue
                
                filled = False
                if gap_val > 0: # Bullish gap
                    if day_data['Low'].min() <= row['Prior_Close']:
                        filled = True
                elif gap_val < 0: # Bearish gap
                    if day_data['High'].max() >= row['Prior_Close']:
                        filled = True
                else:
                    filled = True
                    
                # Categorize
                abs_gap_pct = abs(gap_pct)
                if abs_gap_pct < 0.15: cat = "micro"
                elif abs_gap_pct < 0.40: cat = "small"
                elif abs_gap_pct < 0.80: cat = "medium"
                elif abs_gap_pct < 1.50: cat = "large"
                else: cat = "extreme"
                
                all_gap_data.append({
                    'category': cat,
                    'direction': 'BULL' if gap_val >= 0 else 'BEAR',
                    'filled': filled,
                    'gap_pct': gap_pct
                })
        except Exception as e:
            print(f"   ⚠️ Error processing {symbol}: {e}")
            
    # Aggregate stats
    print(f"📊 Collected {len(all_gap_data)} gap data points.")
    if not all_gap_data:
        print("⚠️ No gap data collected. Saving empty joblib.")
        gap_df = pd.DataFrame(columns=['category', 'direction', 'filled', 'gap_pct'])
    else:
        gap_df = pd.DataFrame(all_gap_data)
    
    # Save to joblib
    output_path = Path("data/gap_stats.joblib")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(gap_df, output_path)
    print(f"✅ Gap statistics saved to {output_path}")

if __name__ == "__main__":
    main()
