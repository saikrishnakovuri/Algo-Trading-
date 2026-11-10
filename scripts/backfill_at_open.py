import json
import time
import redis
import yaml
import os
from datetime import datetime
from modules.broker_layer import AngelOneBroker

def backfill():
    print("STARTING MARKET-OPEN BACKFILL...")
    
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    broker = AngelOneBroker()
    if not broker.login():
        print("Login failed")
        return

    # Load Full Universe
    u_path = "config/universe_full.yaml" if os.path.exists("config/universe_full.yaml") else "config/universe.yaml"
    with open(u_path, "r") as f:
        universe = yaml.safe_load(f)['universe']
    
    t_path = "broker_tokens_full.json" if os.path.exists("broker_tokens_full.json") else "broker_tokens.json"
    with open(t_path, "r") as f:
        token_map = json.load(f)

    # BACKFILL TIER 1 and TIER 2
    backfill_symbols = universe['tiers'].get('TIER_1', []) + universe['tiers'].get('TIER_2', [])
    print(f"Backfilling {len(backfill_symbols)} Tier 1 & 2 symbols...")

    for symbol in backfill_symbols:
        angel_sym = f"{symbol}-EQ"
        token = token_map.get(angel_sym)
        if not token: continue

        print(f"Backfilling {symbol}...")
        df = broker.get_historical_data(angel_sym, token, interval="FIVE_MINUTE", days=2)
        
        if df is not None and not df.empty:
            redis_key = f"candles:5m:{token}"
            r.delete(redis_key)
            
            pipe = r.pipeline()
            # Push last 100 candles
            for idx, row in df.tail(100).iterrows():
                candle = {
                    'timestamp': idx.strftime('%Y-%m-%d %H:%M:%S'),
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': float(row['Volume'])
                }
                pipe.lpush(redis_key, json.dumps(candle))
            pipe.ltrim(redis_key, 0, 99)
            pipe.execute()
        
        # Respect API rate limit: 1 call per 0.5s
        time.sleep(0.5)

    print("BACKFILL COMPLETE.")

if __name__ == "__main__":
    backfill()
