import asyncio
from datetime import datetime
from market_gateway.websocket_broadcaster import broadcaster
from market_gateway.schemas import TickEvent, CandleEvent, SignalEvent

class EventStream:
    def __init__(self):
        self.queue = asyncio.Queue()
        self._loop = asyncio.get_event_loop()

    def publish_signal(self, symbol: str, signal: str, reason: str):
        sig = SignalEvent(symbol=symbol, signal=signal, reason=reason, timestamp=datetime.now())
        # Non-blocking, thread-safe publication to persistent loop
        asyncio.run_coroutine_threadsafe(broadcaster.broadcast_signal(sig), self._loop)

    def publish_tick(self, symbol: str, price: float):
        tick = TickEvent(symbol=symbol, price=price, timestamp=datetime.now())
        asyncio.run_coroutine_threadsafe(broadcaster.broadcast_tick(tick), self._loop)

    def publish_candle(self, symbol: str, tf: str, o, h, l, c, v):
        candle = CandleEvent(symbol=symbol, timeframe=tf, open=o, high=h, low=l, close=c, volume=v, timestamp=datetime.now())
        asyncio.run_coroutine_threadsafe(broadcaster.broadcast_candle(candle), self._loop)

event_stream = EventStream()
