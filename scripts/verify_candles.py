
import time
import json
import redis
import pandas as pd
from datetime import datetime, timedelta
from modules.broker_layer import AngelOneBroker

def verify_candle_build(symbol: str):
    print(f"VERIFYING CANDLE BUILD FOR {symbol}...")
    
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    
    with open("broker_tokens.json", "r") as f:
        token_map = json.load(f)
    
    angel_sym = f"{symbol}-EQ"
    token = token_map.get(angel_sym)
    
    if not token:
        print(f"Token not found for {symbol}")
        return

    # 1. Fetch built candles from Redis
    redis_key = f"candles:1m:{token}"
    built_raw = r.lrange(redis_key, 0, 4) # Last 5 candles
    
    if not built_raw:
        print("No built candles found in Redis. Is the WebSocket and Candle Builder running?")
        return
        
    built_candles = [json.loads(c) for c in built_raw]
    df_built = pd.DataFrame(built_candles)
    df_built['timestamp'] = pd.to_datetime(df_built['timestamp'])
    df_built = df_built.sort_values('timestamp', ascending=False).head(5)

    # 2. Fetch REST candles from Angel One
    broker = AngelOneBroker()
    if not broker.login(): return
    
    df_rest = broker.get_historical_data(angel_sym, token, interval="ONE_MINUTE", days=1)
    if df_rest is None or df_rest.empty:
        print("Failed to fetch REST candles")
        return
    
    df_rest = df_rest.sort_index(ascending=False).head(5)

    # 3. Comparison
    print("\n--- COMPARISON (Last 5 Candles) ---")
    print(f"{'Time':<20} | {'Built Close':<10} | {'REST Close':<10} | {'Diff':<10}")
    print("-" * 55)
    
    for idx, row in df_built.iterrows():
        ts = row['timestamp']
        built_close = row['close']
        
        # Match by timestamp
        if ts in df_rest.index:
            rest_close = df_rest.loc[ts, 'Close']
            diff = built_close - rest_close
            print(f"{ts.strftime('%Y-%m-%d %H:%M'):<20} | {built_close:<11.2f} | {rest_close:<10.2f} | {diff:<+10.2f}")
        else:
            print(f"{ts.strftime('%Y-%m-%d %H:%M'):<20} | {built_close:<11.2f} | {'Missing in REST':<10} | {'N/A':<10}")

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else "RELIANCE"
    verify_candle_build(symbol)
