import requests
import json
import yaml
import os

def generate_universe():
    print("Fetching OpenAPIScripMaster.json...")
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    try:
        res = requests.get(url, timeout=30)
        if res.status_code != 200:
            print(f"Failed to fetch master list. Status code: {res.status_code}")
            return
        master_list = res.json()
    except Exception as e:
        print(f"Error fetching master list: {e}")
        return
    
    # 1. NSE EQ Symbols
    nse_eq = [s for s in master_list if s.get('exch_seg') == 'NSE' and s.get('symbol', '').endswith('-EQ')]
    
    # 2. MCX FUTCOM Symbols
    mcx_fut = [s for s in master_list if s.get('exch_seg') == 'MCX' and s.get('instrumenttype') == 'FUTCOM']
    
    # NIFTY 50 Constituents (Standard list)
    nifty50_list = {
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", 
        "BPCL", "BHARTIARTL", "BRITANNIA", "CIPLA", "COALINDIA", "DIVISLAB", "DRREDDY", "EICHERMOT", 
        "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR", "ICICIBANK", 
        "ITC", "INDUSINDBK", "INFY", "JSWSTEEL", "KOTAKBANK", "LT", "LTIM", "M&M", "MARUTI", "NTPC", 
        "NESTLEIND", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SUNPHARMA", "TCS", "TATACONSUM", 
        "TATAMOTORS", "TATASTEEL", "TECHM", "TITAN", "UPL", "ULTRACEMCO", "WIPRO"
    }

    # Samples for NIFTY Next 150
    nifty_next_list = {
        "ACC", "ABBOTINDIA", "ADANIENSOL", "ADANIGREEN", "ADANIPOWER", "ATGL", "AMBUJACEM", "BEL", "BERGEPAINT", 
        "BIOCON", "BOSCHLTD", "CANBK", "CHOLAFIN", "DLF", "DMART", "GAIL", "HAL", "HAVELLS", "ICICIGI", 
        "ICICIPRULI", "IOC", "IRCTC", "IRFC", "INDIGO", "JINDALSTEL", "LICHSGFIN", "LICI", "MRF", "MUTHOOTFIN", 
        "NMDC", "NAUKRI", "PAGEIND", "PIDILITIND", "PFC", "PNB", "RECLTD", "SHREECEM", "SIEMENS", "TVSMOTOR", 
        "TRENT", "UNITDSPR", "VBL", "VEDL", "YESBANK", "ZOMATO", "ZYDUSLIFE"
    }
    
    tiers = {'TIER_1': [], 'TIER_2': [], 'TIER_3': []}
    mappings = {}
    tokens = {}
    
    # Process NSE
    for s in nse_eq:
        symbol_full = s['symbol']
        symbol_clean = symbol_full.replace('-EQ', '')
        token = s['token']
        if symbol_clean in nifty50_list:
            tier = 1
            tiers['TIER_1'].append(symbol_clean)
        elif symbol_clean in nifty_next_list or (len(tiers['TIER_2']) < 150 and symbol_clean not in nifty50_list):
            tier = 2
            tiers['TIER_2'].append(symbol_clean)
        else:
            tier = 3
            tiers['TIER_3'].append(symbol_clean)
            
        mappings[symbol_clean] = {'exchange': 'NSE', 'sector': "UNKNOWN", 'tier': tier, 'beta_base': 1.0}
        tokens[symbol_full] = token

    # Process MCX (Select nearest expiry for key commodities)
    mcx_keys = {
        "CRUDEOIL": {"lot_size": 100, "tick_size": 1},
        "GOLD": {"lot_size": 100, "tick_size": 10},
        "SILVER": {"lot_size": 30, "tick_size": 1},
        "NATURALGAS": {"lot_size": 1250, "tick_size": 0.10},
        "COPPER": {"lot_size": 2500, "tick_size": 0.05}
    }
    
    mcx_final = {}
    for key, props in mcx_keys.items():
        # Filter symbols starting with key (e.g. CRUDEOIL25JANFUT)
        matches = [s for s in mcx_fut if s['symbol'].startswith(key)]
        if not matches: continue
        
        # Sort by expiry (Nearest first)
        matches.sort(key=lambda x: x['expiry'])
        nearest = matches[0]
        
        mcx_final[key] = {
            'exchange': 'MCX',
            'symbol': nearest['symbol'],
            'token': nearest['token'],
            'lot_size': props['lot_size'],
            'tick_size': props['tick_size'],
            'expiry': nearest['expiry']
        }
        tokens[nearest['symbol']] = nearest['token']

    # Standard Indices
    indices = [
        {"symbol": "Nifty 50", "token": "99926000", "exchange": "NSE"},
        {"symbol": "Nifty Bank", "token": "99926009", "exchange": "NSE"},
        {"symbol": "INDIA VIX", "token": "99926036", "exchange": "NSE"}
    ]
    for idx in indices:
        tokens[idx['symbol']] = idx['token']

    universe_config = {
        'universe': {
            'name': "NSE_MCX_FULL",
            'default_beta': 1.0,
            'tiers': tiers,
            'mappings': mappings,
            'mcx': mcx_final
        }
    }
    
    os.makedirs('config', exist_ok=True)
    with open('config/universe_full.yaml', 'w') as f:
        yaml.dump(universe_config, f, sort_keys=False)
    with open('broker_tokens_full.json', 'w') as f:
        json.dump(tokens, f, indent=4)
        
    print(f"Generated universe: NSE Tier1={len(tiers['TIER_1'])}, Tier2={len(tiers['TIER_2'])}, Tier3={len(tiers['TIER_3'])}, MCX={len(mcx_final)}")

if __name__ == "__main__":
    generate_universe()
