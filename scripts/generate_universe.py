import requests
import pandas as pd
import json
import yaml
import os

def generate_universe():
    print("🚀 Fetching Angel One Master File...")
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    try:
        data = requests.get(url, timeout=30).json()
        df = pd.DataFrame(data)
    except Exception as e:
        print(f"❌ Error fetching scrip master: {e}")
        return

    # 1. Filter Only NSE Equity
    print("🔍 Filtering NSE Equity stocks...")
    # NOTE: instrumenttype can be empty string for some EQ stocks
    df = df[
        (df['exch_seg'] == 'NSE') &
        (df['symbol'].str.endswith("-EQ"))
    ].copy()
    
    # Filter out weird ones like INAV
    df = df[~df['symbol'].str.contains("INAV")]

    # 2. Cleanup
    df['symbol_clean'] = df['symbol'].str.replace("-EQ", "")
    df = df[['symbol_clean', 'name', 'token']].drop_duplicates(subset=['symbol_clean'])
    
    # Take first 1000
    top_1000 = df.head(1000).copy()
    
    # 3. Create Tiers
    tiers = {
        "TIER_1": top_1000.iloc[:150]['symbol_clean'].tolist(),
        "TIER_2": top_1000.iloc[150:500]['symbol_clean'].tolist(),
        "TIER_3": top_1000.iloc[500:1000]['symbol_clean'].tolist()
    }

    # 4. Map for Live Trader
    mappings = {}
    token_map = {}
    for _, row in top_1000.iterrows():
        sym = row['symbol_clean']
        mappings[sym] = {
            "name": row['name'],
            "token": row['token'],
            "tier": 1 if sym in tiers['TIER_1'] else (2 if sym in tiers['TIER_2'] else 3)
        }
        token_map[f"{sym}-EQ"] = row['token']

    # 5. Save Files
    print(f"💾 Saving universe with {len(top_1000)} stocks...")
    
    universe_data = {
        "universe": {
            "name": "NSE_TOP_1000_DYNAMIC",
            "tiers": tiers,
            "mappings": mappings
        }
    }

    with open("config/universe_full.yaml", "w") as f:
        yaml.dump(universe_data, f, sort_keys=False)
        
    with open("broker_tokens_full.json", "w") as f:
        json.dump(token_map, f, indent=2)

    print("✅ Generation Complete!")
    print(f"Tier 1: {len(tiers['TIER_1'])}")
    print(f"Tier 2: {len(tiers['TIER_2'])}")
    print(f"Tier 3: {len(tiers['TIER_3'])}")

if __name__ == "__main__":
    generate_universe()
