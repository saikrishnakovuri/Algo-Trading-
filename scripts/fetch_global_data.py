import yfinance as yf
import pandas as pd
import os
import json
import time
from datetime import datetime

# Asset Lists
US_STOCKS = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "JPM", "V", "GS", "SPY", "QQQ"]
CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD"]
COMMODITIES = ["GC=F", "CL=F", "SI=F", "NG=F"]
FOREX = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]

CACHE_DIR = "data/global"

def fetch_and_cache():
    os.makedirs(CACHE_DIR, exist_ok=True)
    manifest = {"last_updated": datetime.now().isoformat(), "assets": {}}
    
    all_symbols = US_STOCKS + CRYPTO + COMMODITIES + FOREX
    
    for i, symbol in enumerate(all_symbols):
        print(f"[{i+1}/{len(all_symbols)}] Fetching {symbol}...")
        
        try:
            # 5m data (max 60d)
            df_5m = yf.download(symbol, period="60d", interval="5m", progress=False)
            if not df_5m.empty:
                # Flatten MultiIndex if present
                if isinstance(df_5m.columns, pd.MultiIndex):
                    df_5m.columns = df_5m.columns.get_level_values(0)
                
                df_5m.index.name = 'Timestamp'
                df_5m = df_5m[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                
                path_5m = f"{CACHE_DIR}/{symbol.replace('=','_')}_5m.parquet"
                df_5m.to_parquet(path_5m)
                
                # 1m data (max 7d)
                df_1m = yf.download(symbol, period="7d", interval="1m", progress=False)
                if not df_1m.empty:
                    if isinstance(df_1m.columns, pd.MultiIndex):
                        df_1m.columns = df_1m.columns.get_level_values(0)
                    df_1m.index.name = 'Timestamp'
                    df_1m = df_1m[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
                    path_1m = f"{CACHE_DIR}/{symbol.replace('=','_')}_1m.parquet"
                    df_1m.to_parquet(path_1m)
                
                manifest["assets"][symbol] = {
                    "5m_path": path_5m,
                    "5m_count": len(df_5m),
                    "1m_count": len(df_1m) if not df_1m.empty else 0
                }
                print(f"  ✓ Saved {len(df_5m)} 5m bars")
            else:
                print(f"  ⚠ No data found for {symbol}")
                
        except Exception as e:
            print(f"  ✗ Error fetching {symbol}: {e}")
        
        time.sleep(1) # Rate limit safety

    with open(f"{CACHE_DIR}/manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    print("\nGLOBAL FETCH COMPLETE.")

if __name__ == "__main__":
    fetch_and_cache()
