import asyncio
from typing import Dict, List
import logging

logger = logging.getLogger("CandleManager")

from utils.candle_aggregator import candle_aggregator

class CandleManager:
    def __init__(self):
        self.subscribers = set()
        self.aggregator = candle_aggregator

    def register(self, websocket):
        self.subscribers.add(websocket)

    def unregister(self, websocket):
        self.subscribers.discard(websocket)

    def process_tick(self, symbol, price, volume, timestamp):
        """Processes a raw tick and updates all timeframes."""
        self.aggregator.update(symbol, price, volume, timestamp)

    async def broadcast(self, candle: Dict):
        if self.subscribers:
            await asyncio.gather(
                *[ws.send_json(candle) for ws in self.subscribers],
                return_exceptions=True
            )


# Global Instance
candle_manager = CandleManager()
