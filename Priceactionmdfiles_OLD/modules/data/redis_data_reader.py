import redis
import json
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger('live_trader')

class RedisDataReader:
    """
    Helper module to abstract Redis data reads for the trading engine.
    Supports multiple exchanges (NSE, MCX, CRYPTO).
    """
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0):
        try:
            self.r = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db, 
                decode_responses=True,
                socket_timeout=5
            )
            self.r.ping()
            self.is_connected = True
        except Exception as e:
            logger.error(f"Redis Connection Error: {e}")
            self.is_connected = False

    def get_5m_candles(self, token: str, exchange: str = 'NSE', count: int = 100) -> Optional[pd.DataFrame]:
        return self._get_candles(f"candles:5m:{exchange}:{token}", count)

    def get_1m_candles(self, token: str, exchange: str = 'NSE', count: int = 100) -> Optional[pd.DataFrame]:
        return self._get_candles(f"candles:1m:{exchange}:{token}", count)

    def _get_candles(self, key: str, count: int) -> Optional[pd.DataFrame]:
        try:
            raw_candles = self.r.lrange(key, 0, count - 1)
            if not raw_candles or len(raw_candles) < 20:
                return None
            
            data = [json.loads(c) for c in raw_candles]
            df = pd.DataFrame(data)
            
            df.rename(columns={
                'timestamp': 'Timestamp',
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }, inplace=True)
            
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df.set_index('Timestamp', inplace=True)
            df.sort_index(ascending=True, inplace=True)
            
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]
        except Exception as e:
            logger.error(f"Error reading candles from Redis ({key}): {e}")
            return None

    def get_live_price(self, token: str, exchange: str = 'NSE') -> Optional[dict]:
        try:
            data = self.r.hgetall(f"latest_tick:{exchange}:{token}")
            if not data:
                return None
            return {
                'ltp': float(data['lp']),
                'volume': int(data['v']),
                'timestamp': data['ts']
            }
        except Exception as e:
            logger.error(f"Error reading live price for {exchange}:{token}: {e}")
            return None

    def get_live_candle(self, token: str, timeframe: str = '5m', exchange: str = 'NSE') -> Optional[dict]:
        try:
            data = self.r.get(f"candle_live:{timeframe}:{exchange}:{token}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Error reading live candle for {exchange}:{token}: {e}")
            return None

    def is_data_fresh(self, token: str, exchange: str = 'NSE', max_age_seconds: int = 120) -> bool:
        try:
            tick = self.get_live_price(token, exchange)
            if not tick:
                return False
            
            tick_ts = datetime.strptime(tick['timestamp'], '%Y-%m-%d %H:%M:%S')
            diff = (datetime.now() - tick_ts).total_seconds()
            return diff <= max_age_seconds
        except:
            return False

    def get_candle_count(self, token: str, timeframe: str = '5m', exchange: str = 'NSE') -> int:
        try:
            return self.r.llen(f"candles:{timeframe}:{exchange}:{token}")
        except:
            return 0

    def batch_read_5m(self, tokens: List[str], exchange: str = 'NSE') -> Dict[str, pd.DataFrame]:
        pipe = self.r.pipeline()
        for token in tokens:
            pipe.lrange(f"candles:5m:{exchange}:{token}", 0, 99)
        
        results = pipe.execute()
        
        batch_data = {}
        for i, raw_list in enumerate(results):
            token = tokens[i]
            if len(raw_list) >= 20:
                data = [json.loads(c) for c in raw_list]
                df = pd.DataFrame(data)
                df.rename(columns={'timestamp': 'Timestamp', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                df.set_index('Timestamp', inplace=True)
                df.sort_index(ascending=True, inplace=True)
                batch_data[token] = df
        
        return batch_data
