import json
import logging
import redis
import pytz
import os
import yaml
from datetime import datetime, time, timedelta
from typing import Dict, Any, Optional

# Configuration
LOG_FILE = "logs/candle_builder.log"
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("candle_builder")

import time as t_time
IST = pytz.timezone('Asia/Kolkata')

class RealTimeCandleBuilder:
    def __init__(self, host='localhost', port=6379, db=0):
        try:
            self.r = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            self.r.ping()
            logger.info("Connected to Redis for Candle Building")
        except Exception as e:
            logger.error(f"Redis Connection Failed: {e}")
            raise

        self.candle_state: Dict[str, Dict[str, Any]] = {}
        self.last_boundary: Dict[str, Dict[str, datetime]] = {}
        self.market_hours = self._load_market_hours()
        self._cache_saved_today = set()

    def _load_market_hours(self):
        try:
            with open("config/market_hours.yaml", "r") as f:
                return yaml.safe_load(f).get('exchanges', {})
        except:
            return {}

    def save_cache(self, exchange: str):
        logger.info(f"Saving {exchange} candle cache to disk...")
        cache_data = {}
        try:
            keys = self.r.keys(f"candles:*:{exchange}:*")
            for key in keys:
                cache_data[key] = self.r.lrange(key, 0, -1)
            
            date_str = datetime.now(IST).strftime('%Y%m%d')
            filename = f"data/candle_cache_{exchange}_{date_str}.json"
            with open(filename, 'w') as f:
                json.dump(cache_data, f)
        except Exception as e:
            logger.error(f"Failed to save {exchange} cache: {e}")

    def load_cache(self):
        logger.info("Checking for candle cache files to load...")
        try:
            files = [f for f in os.listdir("data") if f.startswith("candle_cache_") and f.endswith(".json")]
            for filename in files:
                logger.info(f"Loading cache from {filename}...")
                with open(f"data/{filename}", 'r') as f:
                    cache_data = json.load(f)
                pipe = self.r.pipeline()
                for key, candles in cache_data.items():
                    pipe.delete(key)
                    for candle in reversed(candles):
                        pipe.lpush(key, candle)
                    pipe.ltrim(key, 0, 99)
                pipe.execute()
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")

    def _get_time_boundary(self, dt: datetime, timeframe_mins: int, exchange: str) -> datetime:
        # Get exchange timezone
        exch_config = self.market_hours.get(exchange, {})
        tz_name = exch_config.get('timezone', 'Asia/Kolkata')
        tz = pytz.timezone(tz_name)
        
        if dt.tzinfo is None: dt = IST.localize(dt).astimezone(tz)
        else: dt = dt.astimezone(tz)
        
        # Get market open time
        open_str = exch_config.get('open', '09:15')
        open_h, open_m = map(int, open_str.split(':'))
        
        minutes_since_midnight = dt.hour * 60 + dt.minute
        offset = open_h * 60 + open_m
        
        base_minutes = minutes_since_midnight - offset
        floored_minutes = (base_minutes // timeframe_mins) * timeframe_mins + offset
        
        return dt.replace(hour=floored_minutes // 60, minute=floored_minutes % 60, second=0, microsecond=0)

    def process_tick(self, exchange: str, tick: Dict[str, Any]):
        token = tick['t']
        price = float(tick['lp'])
        total_volume = float(tick['v'])
        state_key = f"{exchange}:{token}"
        
        try:
            dt = datetime.strptime(tick['ts'], '%Y-%m-%d %H:%M:%S')
            dt = IST.localize(dt)
        except:
            dt = datetime.now(IST)

        # Exchange-aware reset and close
        exch_config = self.market_hours.get(exchange, {})
        open_str = exch_config.get('open', '09:15')
        close_str = exch_config.get('close', '15:30')
        
        # Open Reset
        oh, om = map(int, open_str.split(':'))
        if dt.hour == oh and dt.minute == om and dt.second < 2:
            if state_key in self.candle_state:
                self._flush_and_reset(state_key)

        # Close Cache
        ch, cm = map(int, close_str.split(':'))
        if dt.hour == ch and dt.minute == cm and dt.second < 2:
            if exchange not in self._cache_saved_today:
                self.save_cache(exchange)
                self._cache_saved_today.add(exchange)

        if state_key not in self.candle_state:
            self.candle_state[state_key] = {
                '1m': self._init_candle(price, total_volume, dt),
                '5m': self._init_candle(price, total_volume, dt)
            }
            self.last_boundary[state_key] = {
                '1m': self._get_time_boundary(dt, 1, exchange),
                '5m': self._get_time_boundary(dt, 5, exchange)
            }
            return

        for tf_name, tf_mins in [('1m', 1), ('5m', 5)]:
            boundary = self._get_time_boundary(dt, tf_mins, exchange)
            if boundary > self.last_boundary[state_key][tf_name]:
                # Close previous
                closed_candle = self.candle_state[state_key][tf_name]
                closed_candle['timestamp'] = self.last_boundary[state_key][tf_name].strftime('%Y-%m-%d %H:%M:%S')
                self.r.lpush(f"candles:{tf_name}:{exchange}:{token}", json.dumps(closed_candle))
                self.r.ltrim(f"candles:{tf_name}:{exchange}:{token}", 0, 99)
                
                # New candle
                self.candle_state[state_key][tf_name] = self._init_candle(price, total_volume, dt)
                self.last_boundary[state_key][tf_name] = boundary
            else:
                # Update
                state = self.candle_state[state_key][tf_name]
                state['high'] = max(state['high'], price)
                state['low'] = min(state['low'], price)
                state['close'] = price
                state['volume'] = total_volume - state['start_volume']
                
            # Update live
            live_candle = self.candle_state[state_key][tf_name].copy()
            live_candle['timestamp'] = boundary.strftime('%Y-%m-%d %H:%M:%S')
            self.r.set(f"candle_live:{tf_name}:{exchange}:{token}", json.dumps(live_candle))

    def _init_candle(self, price: float, cumulative_volume: float, dt: datetime) -> Dict[str, Any]:
        return {'open': price, 'high': price, 'low': price, 'close': price, 'volume': 0, 'start_volume': cumulative_volume, 'start_ts': dt.strftime('%Y-%m-%d %H:%M:%S')}

    def _flush_and_reset(self, state_key: str):
        if state_key in self.candle_state: del self.candle_state[state_key]
        if state_key in self.last_boundary: del self.last_boundary[state_key]

    def run(self):
        self.load_cache()
        pubsub = self.r.pubsub()
        pubsub.psubscribe("ticks:*")
        logger.info("Multi-Asset Candle Builder started. Listening for ticks:*...")
        for message in pubsub.listen():
            if message['type'] == 'pmessage':
                try:
                    # Channel format: ticks:EXCHANGE:token
                    channel = message['channel']
                    parts = channel.split(':')
                    if len(parts) < 3: continue
                    exchange = parts[1]
                    tick_data = json.loads(message['data'])
                    self.process_tick(exchange, tick_data)
                except Exception as e:
                    logger.error(f"Error processing tick message: {e}")

if __name__ == "__main__":
    builder = RealTimeCandleBuilder()
    builder.run()
