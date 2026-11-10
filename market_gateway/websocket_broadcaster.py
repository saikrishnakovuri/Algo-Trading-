from market_gateway.connection_manager import manager
from market_gateway.schemas import TickEvent, CandleEvent, SignalEvent

class WebSocketBroadcaster:
    async def broadcast_tick(self, tick: TickEvent):
        await manager.broadcast({"type": "tick", **tick.dict()})

    async def broadcast_candle(self, candle: CandleEvent):
        await manager.broadcast({"type": "candle", **candle.dict()})

    async def broadcast_signal(self, signal: SignalEvent):
        await manager.broadcast({"type": "signal", **signal.dict()})

broadcaster = WebSocketBroadcaster()
