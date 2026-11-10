import asyncio
import json
import logging
import redis
from binance import AsyncClient, BinanceSocketManager
from datetime import datetime

# Configuration
LOG_FILE = "logs/binance_feed.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | BINANCE_WS | %(message)s',
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()]
)
logger = logging.getLogger("binance_feed")

import os

class BinanceFeed:
    """
    Real-time Binance WebSocket feed for Crypto.
    Pushes closed and forming candles to Redis.
    """
    def __init__(self, symbols=['btcusdt', 'ethusdt', 'solusdt', 'xrpusdt']):
        self.symbols = [s.lower() for s in symbols]
        
        if os.getenv("SKIP_REDIS_CHECK") == "1":
            logger.info("DRY RUN: Using Redis Stub for Binance")
            self.r = type('RedisStub', (object,), {
                'ping': lambda self: True,
                'lpush': lambda self, k, v: 0,
                'ltrim': lambda self, k, s, e: True,
                'set': lambda self, k, v: True,
                'hset': lambda self, k, mapping=None: True,
                'publish': lambda self, c, m: 0
            })()
        else:
            try:
                self.r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                self.r.ping()
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Redis Connection Failed: {e}")
                raise

    async def run(self):
        client = await AsyncClient.create()
        bm = BinanceSocketManager(client)
        
        # Subscribe to 1m and 5m klines
        streams = []
        for sym in self.symbols:
            streams.append(f"{sym}@kline_1m")
            streams.append(f"{sym}@kline_5m")
            
        logger.info(f"Subscribing to streams: {streams}")
        
        # Multi-stream listener
        ms = bm.multiplex_socket(streams)
        
        async with ms as tscm:
            while True:
                res = await tscm.recv()
                if res:
                    await self.handle_message(res)

    async def handle_message(self, msg):
        try:
            # Multiplex format: {'stream': '...', 'data': {...}}
            data = msg['data']
            symbol = data['s'].upper()
            k = data['k']
            interval = k['i'] # '1m' or '5m'
            is_closed = k['x']
            
            # Format to unified model
            # Binance uses ms timestamps
            ts = datetime.fromtimestamp(k['t']/1000).strftime('%Y-%m-%d %H:%M:%S')
            
            candle = {
                'timestamp': ts,
                'open': float(k['o']),
                'high': float(k['h']),
                'low': float(k['l']),
                'close': float(k['c']),
                'volume': float(k['v'])
            }
            
            tick_data = {
                't': symbol,
                'lp': candle['close'],
                'v': candle['volume'],
                'ts': ts
            }

            if is_closed:
                # 1. Closed candle to Redis list
                redis_key = f"candles:{interval}:CRYPTO:{symbol}"
                self.r.lpush(redis_key, json.dumps(candle))
                self.r.ltrim(redis_key, 0, 99)
                logger.debug(f"Closed {interval} candle for {symbol}")
            else:
                # 2. Forming candle to Redis key
                self.r.set(f"candle_live:{interval}:CRYPTO:{symbol}", json.dumps(candle))
            
            # 3. Always update latest tick
            self.r.hset(f"latest_tick:CRYPTO:{symbol}", mapping=tick_data)
            self.r.publish(f"ticks:CRYPTO:{symbol}", json.dumps(tick_data))

        except Exception as e:
            logger.error(f"Error processing Binance message: {e}")

if __name__ == "__main__":
    feed = BinanceFeed()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(feed.run())
    except KeyboardInterrupt:
        logger.info("Binance feed stopped.")
