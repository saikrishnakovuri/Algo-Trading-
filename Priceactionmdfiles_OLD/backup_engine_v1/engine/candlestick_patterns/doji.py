"""
Strategy: Doji Candlestick Pattern
Category: candlestick
Source: Candlestickpatterns/Doji Candlestick Pattern.md

Description:
  A single candle pattern signaling indecision.
  - Body is extremely small (Open approx. equal to Close).
  - Wicks represent the battle between bulls and bears.

Logic:
  - Body size <= 10% of total candle range.
  - Standard Doji: Balanced wicks.
  - Dragonfly Doji: Long lower wick, little/no upper wick.
  - Gravestone Doji: Long upper wick, little/no lower wick.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from ..base_strategy import BaseStrategy
from ..signal import Signal, SignalType, MarketBias


class Doji(BaseStrategy):
    
    @property
    def name(self) -> str:
        return "Doji"
    
    @property
    def category(self) -> str:
        return "candlestick"
    
    @property
    def required_candles(self) -> int:
        return 20
    
    def detect(self, df: pd.DataFrame, timeframe: str = "15m") -> List[Signal]:
        if not self.validate_dataframe(df):
            return []
            
        c = df.iloc[-1]
        
        body_size = abs(c['close'] - c['open'])
        total_range = c['high'] - c['low']
        
        if total_range == 0: # Avoid division by zero in flat markets
            return []
            
        # Doji Condition: Body is tiny relative to range
        is_doji = body_size <= (total_range * 0.1)
        
        if not is_doji:
            return []
            
        # Identify sub-types
        upper_wick = c['high'] - max(c['open'], c['close'])
        lower_wick = min(c['open'], c['close']) - c['low']
        
        doji_type = "Standard"
        bias = MarketBias.NEUTRAL
        
        if upper_wick <= (total_range * 0.1) and lower_wick > (total_range * 0.5):
            doji_type = "Dragonfly" # Bullish Rejection
            bias = MarketBias.BULLISH
        elif lower_wick <= (total_range * 0.1) and upper_wick > (total_range * 0.5):
            doji_type = "Gravestone" # Bearish Rejection
            bias = MarketBias.BEARISH
        elif total_range > (df['high'] - df['low']).tail(20).mean() * 1.5:
            doji_type = "Long-Legged"
            
        # Doji is neutral, so we mostly return HOLD with reasoning
        # unless it's a specific rejection type at an extreme.
        
        signals = [Signal(
            signal_type=SignalType.HOLD,
            strategy_name=self.name,
            confidence=0.5,
            timeframe=timeframe,
            market_bias=bias,
            reasoning=f"{doji_type} Doji detected. Market is in equilibrium/indecision."
        )]
        
        return signals
