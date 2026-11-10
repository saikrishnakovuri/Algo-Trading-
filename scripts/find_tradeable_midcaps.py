import os
import pandas as pd
import numpy as np

DATA_DIR = "data/nifty200"

def analyze_liquidity(symbol):
    path = os.path.join(DATA_DIR, f"{symbol}_1m.csv")
    try:
        df = pd.read_csv(path)
        df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True).dt.tz_convert('Asia/Kolkata')
        df.set_index('Datetime', inplace=True)
        
        # Focus on April 2026
        df_apr = df.between_time('09:15', '15:30')
        df_apr = df_apr[df_apr.index.month == 4]
        
        if df_apr.empty: return None
        
        daily = df_apr.resample('D').agg({'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
        if daily.empty: return None
        
        daily['range_pct'] = (daily['High'] - daily['Low']) / daily['Close'] * 100
        daily['turnover'] = daily['Volume'] * daily['Close']
        
        avg_range = daily['range_pct'].mean()
        avg_turnover = daily['turnover'].mean()
        
        return {
            'symbol': symbol,
            'avg_range': avg_range,
            'avg_turnover': avg_turnover
        }
    except Exception:
        return None

def main():
    symbols = [f.replace("_1m.csv", "") for f in os.listdir(DATA_DIR) if f.endswith("_1m.csv")]
    results = []
    print(f"Processing {len(symbols)} symbols...")
    for s in symbols:
        res = analyze_liquidity(s)
        if res:
            results.append(res)
    
    if not results:
        print("No results found at all.")
        return

    df = pd.DataFrame(results)
    # Filter: range > 2%, turnover > 5Cr (5,00,00,000)
    tradeable = df[(df['avg_range'] > 2.0) & (df['avg_turnover'] > 50000000)]
    
    if tradeable.empty:
        print("No tradeable symbols found with current filters.")
        # Top by range
        print(df.sort_values('avg_range', ascending=False).head(10)['symbol'].tolist())
        return

    # Sort by range
    top_30 = tradeable.sort_values('avg_range', ascending=False).head(30)
    print(top_30['symbol'].tolist())

if __name__ == "__main__":
    main()
