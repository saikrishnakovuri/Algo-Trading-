import yfinance as yf
import pandas as pd
import os

def fetch_indices():
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    # NIFTY 50
    print("📡 Fetching Nifty 50 Data...")
    nifty = yf.Ticker("^NSEI")
    
    nifty_daily = nifty.history(period="60d", interval="1d")
    nifty_daily.to_csv(os.path.join(data_dir, "nifty50_daily.csv"))
    
    nifty_15m = nifty.history(period="60d", interval="15m")
    nifty_15m.to_csv(os.path.join(data_dir, "nifty50_15m.csv"))
    
    nifty_5m = nifty.history(period="60d", interval="5m")
    nifty_5m.to_csv(os.path.join(data_dir, "nifty50_5m.csv"))
    
    # INDIA VIX
    print("📡 Fetching India VIX Data...")
    # Yahoo symbol for India VIX is usually '^INDIAVIX' or 'INDIAVIX.NS'
    vix = yf.Ticker("^INDIAVIX")
    vix_daily = vix.history(period="60d", interval="1d")
    if vix_daily.empty:
        # Fallback symbol
        vix = yf.Ticker("INDIAVIX.NS")
        vix_daily = vix.history(period="60d", interval="1d")
        
    vix_daily.to_csv(os.path.join(data_dir, "india_vix_daily.csv"))
    
    print("✅ Index fetching complete.")

if __name__ == "__main__":
    fetch_indices()
