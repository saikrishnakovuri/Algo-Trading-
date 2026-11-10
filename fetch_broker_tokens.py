import requests
import json
import pandas as pd
import os

def fetch_tokens():
    """Downloads Angel One instrument list and filters for Nifty 200."""
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    print("📡 Downloading Angel One Instrument List (OpenAPIScripMaster)...")
    
    try:
        # Standard requests approach for better error visibility
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data)
        
        # Filter for NSE segment
        nse_df = df[df['exch_seg'] == 'NSE']
        
        # 1. Filter for equity (ignore others)
        eq_df = nse_df[nse_df['symbol'].str.endswith("-EQ")]
        
        # 2. Filter for major indices
        # We search in 'name' or 'symbol'
        indices_to_track = ["NIFTY", "BANKNIFTY", "INDIA VIX"]
        idx_df = nse_df[nse_df['name'].isin(indices_to_track) | nse_df['symbol'].isin(indices_to_track)]
        
        print(f"Debug: Found {len(idx_df)} index entries.")
        for _, row in idx_df.iterrows():
            print(f"   - {row['name']} | {row['symbol']} | {row['token']}")

        # Map Symbol -> Token
        token_map = dict(zip(eq_df['symbol'], eq_df['token']))
        
        # Add indices using their symbols AND names to be safe
        for _, row in idx_df.iterrows():
            token_map[row['symbol']] = row['token']
            token_map[row['name']] = row['token']
            
        # Hard-force the primary correct indices tokens for the master engine to avoid collisions
        token_map["NIFTY"] = "99926000"
        token_map["Nifty 50"] = "99926000"
        token_map["BANKNIFTY"] = "99926009"
        token_map["Nifty Bank"] = "99926009"
        token_map["INDIA VIX"] = "99926017"
        token_map["India VIX"] = "99926017"
        
        with open("broker_tokens.json", "w") as f:
            json.dump(token_map, f, indent=2)
            
        print(f"✅ Successfully mapped {len(token_map)} NSE tokens (Equity + Indices) to broker_tokens.json")
        return token_map
    except Exception as e:
        print(f"❌ Error fetching tokens: {e}")
        return None

if __name__ == "__main__":
    fetch_tokens()
