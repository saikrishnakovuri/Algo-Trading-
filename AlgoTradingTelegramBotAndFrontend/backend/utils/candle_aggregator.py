import asyncio
from datetime import datetime, timedelta
import pandas as pd
from typing import Dict

class RealTimeCandleAggregator:
    def __init__(self):
        # symbol -> {timeframe -> {OHLCV data}}
        self.buckets = {} 
        self.timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
    
    def get_bucket_start(self, timestamp: datetime, timeframe: str) -> datetime:
        """Aligns a timestamp to the start of the timeframe bucket."""
        if timeframe == '1m':
            return timestamp.replace(second=0, microsecond=0)
        elif timeframe == '5m':
            return timestamp.replace(minute=(timestamp.minute // 5) * 5, second=0, microsecond=0)
        elif timeframe == '15m':
            return timestamp.replace(minute=(timestamp.minute // 15) * 15, second=0, microsecond=0)
        elif timeframe == '1h':
            return timestamp.replace(minute=0, second=0, microsecond=0)
        elif timeframe == '4h':
            return timestamp.replace(hour=(timestamp.hour // 4) * 4, minute=0, second=0, microsecond=0)
        elif timeframe == '1d':
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        return timestamp

    def update(self, symbol: str, price: float, volume: int, timestamp: datetime):
        if symbol not in self.buckets:
            self.buckets[symbol] = {}
            
        for tf in self.timeframes:
            bucket_start = self.get_bucket_start(timestamp, tf)
            
            if tf not in self.buckets[symbol]:
                self.buckets[symbol][tf] = {}
            
            if bucket_start not in self.buckets[symbol][tf]:
                self.buckets[symbol][tf][bucket_start] = {
                    'open': price, 'high': price, 'low': price, 'close': price, 'volume': volume
                }
            else:
                b = self.buckets[symbol][tf][bucket_start]
                b['high'] = max(b['high'], price)
                b['low'] = min(b['low'], price)
                b['close'] = price
                b['volume'] += volume

    def get_latest(self, symbol: str, tf: str):
        if symbol in self.buckets and tf in self.buckets[symbol]:
            data = self.buckets[symbol][tf]
            if not data: return None
            latest_time = max(data.keys())
            return {'time': latest_time, **data[latest_time]}
        return None

candle_aggregator = RealTimeCandleAggregator()
