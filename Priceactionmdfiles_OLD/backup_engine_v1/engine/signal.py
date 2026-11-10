"""
Standard signal output for all strategies.
Every strategy MUST return Signal objects.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from datetime import datetime


class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class MarketBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    VOLATILE = "VOLATILE"


@dataclass
class Signal:
    signal_type: SignalType
    strategy_name: str
    confidence: float              # 0.0 to 1.0
    timeframe: str                 # "1m", "5m", "15m", "1h", "4h", "1d"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    market_bias: MarketBias = MarketBias.NEUTRAL
    reasoning: str = ""
    metadata: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "signal": self.signal_type.value,
            "strategy": self.strategy_name,
            "confidence": self.confidence,
            "timeframe": self.timeframe,
            "entry": self.entry_price,
            "sl": self.stop_loss,
            "tp": self.take_profit,
            "rr": self.risk_reward_ratio,
            "bias": self.market_bias.value,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
