from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class TickEvent(BaseModel):
    symbol: str
    price: float
    timestamp: datetime

class CandleEvent(BaseModel):
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    timestamp: datetime

class SignalEvent(BaseModel):
    symbol: str
    signal: str
    reason: str
    timestamp: datetime

class HealthStatus(BaseModel):
    status: str
    timestamp: datetime

class SystemStatus(BaseModel):
    active_trades: int
    system_load: float
    last_update: datetime
